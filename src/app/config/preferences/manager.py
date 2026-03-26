"""用户偏好设置统一管理接口."""

import logging
from typing import Any, Dict, List, Optional

from ..advanced_params import AdvancedParamsSnapshot, migrate_legacy_performance_preferences
from .defaults import PreferencesDefaults
from .storage import PreferencesStorage
from .validator import PreferencesValidator


class UserPreferencesManager:
    """用户偏好设置管理器."""

    DEFAULT_PREFERENCES = PreferencesDefaults.DEFAULT_PREFERENCES

    def __init__(self, config_dir: Optional[str] = None):
        """初始化管理器并加载偏好设置."""
        self.logger = logging.getLogger(__name__)
        self.storage = PreferencesStorage(config_dir)
        self.validator = PreferencesValidator()
        self.preferences = self.load_preferences()
        self._processing_speeds: List[float] = []
        self.logger.info(
            f"UserPreferencesManager initialized with config dir: {self.storage.config_dir}"
        )

    @property
    def config_dir(self):
        """获取配置目录路径."""
        return self.storage.config_dir

    @property
    def preferences_file(self):
        """获取偏好文件路径."""
        return self.storage.preferences_file

    def load_preferences(self) -> Dict[str, Any]:
        """加载偏好设置."""
        return self.storage.load_preferences()

    def save_preferences(self) -> bool:
        """保存当前偏好设置."""
        return self.storage.save_preferences(self.preferences)

    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """安全获取偏好值."""
        return self.validator.get_safe_preference_value(self.preferences, category, key, default)

    def set_preference(self, category: str, key: str, value: Any) -> bool:
        """设置偏好值并校验."""
        try:
            if not self.validator.validate_preference_value(category, key, value):
                self.logger.warning(f"Invalid preference value {category}.{key}: {value}")
                return False

            if category not in self.preferences:
                self.preferences[category] = {}

            self.preferences[category][key] = value
            return True
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error setting preference {category}.{key}: {e}")
            return False

    def add_recent_file(self, file_path: str) -> None:
        """添加文件到最近列表."""
        try:
            recent_files = self.get_preference("paths", "recent_files", [])
            updated_files = self.validator.add_recent_file(recent_files, file_path)
            self.set_preference("paths", "recent_files", updated_files)
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error adding recent file: {e}")

    def get_recent_files(self) -> List[str]:
        """获取最近文件列表并自动过滤无效路径."""
        recent_files = self.get_preference("paths", "recent_files", [])
        valid_files = self.validator.filter_recent_files(recent_files)
        if len(valid_files) != len(recent_files):
            self.set_preference("paths", "recent_files", valid_files)
        return valid_files

    def clear_recent_files(self) -> None:
        """清空最近文件列表."""
        self.set_preference("paths", "recent_files", [])

    def get_ui_preferences(self) -> Dict[str, Any]:
        """获取 UI 偏好设置."""
        result = self.preferences.get("ui", {})
        return result if isinstance(result, dict) else {}

    def get_processing_preferences(self) -> Dict[str, Any]:
        """获取处理相关偏好设置."""
        result = self.preferences.get("processing", {})
        return result if isinstance(result, dict) else {}

    def get_advanced_preferences(self) -> Dict[str, Any]:
        """获取高级偏好设置."""
        result = self.preferences.get("advanced", {})
        return result if isinstance(result, dict) else {}

    def get_batch_preferences(self) -> Dict[str, Any]:
        """获取批处理偏好设置."""
        result = self.preferences.get("batch", {})
        return result if isinstance(result, dict) else {}

    def get_advanced_params_preferences(self) -> Dict[str, Any]:
        """获取统一高级性能参数偏好设置。"""
        result = self.preferences.get("advanced_params", {})
        return result if isinstance(result, dict) else {}

    def get_advanced_params_snapshot(self) -> AdvancedParamsSnapshot:
        """获取统一高级性能参数快照，并兼容旧结构迁移。"""
        current_preferences = self.get_advanced_params_preferences()
        if current_preferences == PreferencesDefaults.get_advanced_params_defaults():
            current_preferences = {}

        migrated = migrate_legacy_performance_preferences(
            current=current_preferences,
            advanced=self.get_advanced_preferences(),
            batch=self.get_batch_preferences(),
        )
        snapshot = AdvancedParamsSnapshot.from_dict(migrated)

        if "advanced_params" not in self.preferences or not isinstance(
            self.preferences.get("advanced_params"), dict
        ):
            self.preferences["advanced_params"] = snapshot.to_dict()

        return snapshot

    def update_window_geometry(
        self, x: int, y: int, width: int, height: int, maximized: bool = False
    ) -> None:
        """更新窗口几何信息."""
        geometry = [x, y, width, height]
        if self.validator.validate_window_geometry(geometry):
            self.set_preference("ui", "window_geometry", geometry)
            self.set_preference("ui", "window_maximized", maximized)
        else:
            self.logger.warning(f"Invalid window geometry: {geometry}")

    def update_splitter_sizes(self, sizes: List[int]) -> None:
        """更新分割器尺寸."""
        normalized_sizes = self.validator.normalize_splitter_sizes(sizes)
        self.set_preference("ui", "splitter_sizes", normalized_sizes)

    def reset_to_defaults(self) -> bool:
        """重置为默认偏好并保存."""
        try:
            self.preferences = PreferencesDefaults.get_default_preferences()
            return self.save_preferences()
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error resetting preferences: {e}")
            return False

    def export_preferences(self, export_path: str) -> bool:
        """导出偏好设置到指定路径."""
        return self.storage.export_preferences(self.preferences, export_path)

    def import_preferences(self, import_path: str) -> bool:
        """从文件导入偏好设置."""
        imported_preferences = self.storage.import_preferences(import_path)
        if imported_preferences:
            self.preferences = imported_preferences
            return self.save_preferences()
        return False

    def auto_save(self) -> None:
        """按配置自动保存."""
        if self.get_preference("advanced", "auto_save_interval", 300) > 0:
            self.save_preferences()


_preferences_manager: Optional[UserPreferencesManager] = None


def get_preferences_manager(config_dir: Optional[str] = None) -> UserPreferencesManager:
    """获取全局偏好设置管理器实例。"""
    global _preferences_manager
    if _preferences_manager is None:
        _preferences_manager = UserPreferencesManager(config_dir)
    return _preferences_manager


__all__ = ["UserPreferencesManager", "get_preferences_manager"]
