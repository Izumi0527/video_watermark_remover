"""
用户偏好设置统一管理接口。
"""

import logging
from typing import Any, Dict, List, Optional

from .defaults import PreferencesDefaults
from .storage import PreferencesStorage
from .validator import PreferencesValidator


class UserPreferencesManager:
    """用户偏好设置管理器。"""

    DEFAULT_PREFERENCES = PreferencesDefaults.DEFAULT_PREFERENCES

    def __init__(self, config_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.storage = PreferencesStorage(config_dir)
        self.validator = PreferencesValidator()
        self.preferences = self.load_preferences()
        self.logger.info(
            f"UserPreferencesManager initialized with config dir: {self.storage.config_dir}"
        )

    @property
    def config_dir(self):
        return self.storage.config_dir

    @property
    def preferences_file(self):
        return self.storage.preferences_file

    def load_preferences(self) -> Dict[str, Any]:
        return self.storage.load_preferences()

    def save_preferences(self) -> bool:
        return self.storage.save_preferences(self.preferences)

    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        return self.validator.get_safe_preference_value(self.preferences, category, key, default)

    def set_preference(self, category: str, key: str, value: Any) -> bool:
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
        try:
            recent_files = self.get_preference("paths", "recent_files", [])
            updated_files = self.validator.add_recent_file(recent_files, file_path)
            self.set_preference("paths", "recent_files", updated_files)
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error adding recent file: {e}")

    def get_recent_files(self) -> List[str]:
        recent_files = self.get_preference("paths", "recent_files", [])
        valid_files = self.validator.filter_recent_files(recent_files)
        if len(valid_files) != len(recent_files):
            self.set_preference("paths", "recent_files", valid_files)
        return valid_files

    def clear_recent_files(self) -> None:
        self.set_preference("paths", "recent_files", [])

    def get_ui_preferences(self) -> Dict[str, Any]:
        result = self.preferences.get("ui", {})
        return result if isinstance(result, dict) else {}

    def get_processing_preferences(self) -> Dict[str, Any]:
        result = self.preferences.get("processing", {})
        return result if isinstance(result, dict) else {}

    def get_advanced_preferences(self) -> Dict[str, Any]:
        result = self.preferences.get("advanced", {})
        return result if isinstance(result, dict) else {}

    def get_batch_preferences(self) -> Dict[str, Any]:
        result = self.preferences.get("batch", {})
        return result if isinstance(result, dict) else {}

    def update_window_geometry(
        self, x: int, y: int, width: int, height: int, maximized: bool = False
    ) -> None:
        geometry = [x, y, width, height]
        if self.validator.validate_window_geometry(geometry):
            self.set_preference("ui", "window_geometry", geometry)
            self.set_preference("ui", "window_maximized", maximized)
        else:
            self.logger.warning(f"Invalid window geometry: {geometry}")

    def update_splitter_sizes(self, sizes: List[int]) -> None:
        normalized_sizes = self.validator.normalize_splitter_sizes(sizes)
        self.set_preference("ui", "splitter_sizes", normalized_sizes)

    def reset_to_defaults(self) -> bool:
        try:
            self.preferences = PreferencesDefaults.get_default_preferences()
            return self.save_preferences()
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error resetting preferences: {e}")
            return False

    def export_preferences(self, export_path: str) -> bool:
        return self.storage.export_preferences(self.preferences, export_path)

    def import_preferences(self, import_path: str) -> bool:
        imported_preferences = self.storage.import_preferences(import_path)
        if imported_preferences:
            self.preferences = imported_preferences
            return self.save_preferences()
        return False

    def auto_save(self) -> None:
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
