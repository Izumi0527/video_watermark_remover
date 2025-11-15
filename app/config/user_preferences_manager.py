#!/usr/bin/env python3
"""
用户偏好设置管理器

提供以下功能：
1. 主题偏好保存/加载
2. 处理参数偏好保存/加载
3. 界面布局偏好保存/加载
4. 最近使用文件记录
5. 用户自定义设置

重构版本：将功能拆分为多个专门模块，提高代码可维护性
- preferences_defaults.py: 默认配置定义
- preferences_storage.py: 存储管理
- preferences_validator.py: 验证和实用工具

作者: Claude Code Assistant
创建时间: 2025-01-31
版本: v2.0 (重构版)
"""

import logging
from typing import Dict, Any, Optional, List

from .preferences_defaults import PreferencesDefaults
from .preferences_storage import PreferencesStorage
from .preferences_validator import PreferencesValidator


class UserPreferencesManager:
    """用户偏好设置管理器 - 重构版本"""

    # 保持向后兼容性
    DEFAULT_PREFERENCES = PreferencesDefaults.DEFAULT_PREFERENCES

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化用户偏好设置管理器

        Args:
            config_dir: 配置目录路径，默认为用户主目录下的.video_watermark_remover
        """
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.storage = PreferencesStorage(config_dir)
        self.validator = PreferencesValidator()
        
        # 加载偏好设置
        self.preferences = self.load_preferences()

        self.logger.info(f"UserPreferencesManager initialized with config dir: {self.storage.config_dir}")

    @property
    def config_dir(self):
        """配置目录路径（向后兼容性）"""
        return self.storage.config_dir

    @property
    def preferences_file(self):
        """偏好设置文件路径（向后兼容性）"""
        return self.storage.preferences_file

    def load_preferences(self) -> Dict[str, Any]:
        """
        加载用户偏好设置

        Returns:
            偏好设置字典
        """
        return self.storage.load_preferences()

    def save_preferences(self) -> bool:
        """
        保存用户偏好设置

        Returns:
            是否保存成功
        """
        return self.storage.save_preferences(self.preferences)

    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """
        获取偏好设置值

        Args:
            category: 设置类别
            key: 设置键
            default: 默认值

        Returns:
            设置值
        """
        return self.validator.get_safe_preference_value(
            self.preferences, category, key, default
        )

    def set_preference(self, category: str, key: str, value: Any) -> bool:
        """
        设置偏好设置值

        Args:
            category: 设置类别
            key: 设置键
            value: 设置值

        Returns:
            是否设置成功
        """
        try:
            # 验证值的有效性
            if not self.validator.validate_preference_value(category, key, value):
                self.logger.warning(f"Invalid preference value {category}.{key}: {value}")
                return False

            if category not in self.preferences:
                self.preferences[category] = {}

            self.preferences[category][key] = value
            return True

        except Exception as e:
            self.logger.error(f"Error setting preference {category}.{key}: {e}")
            return False

    def add_recent_file(self, file_path: str) -> None:
        """
        添加最近使用的文件

        Args:
            file_path: 文件路径
        """
        try:
            recent_files = self.get_preference("paths", "recent_files", [])
            updated_files = self.validator.add_recent_file(recent_files, file_path)
            self.set_preference("paths", "recent_files", updated_files)

        except Exception as e:
            self.logger.error(f"Error adding recent file: {e}")

    def get_recent_files(self) -> List[str]:
        """
        获取最近使用的文件列表

        Returns:
            文件路径列表
        """
        recent_files = self.get_preference("paths", "recent_files", [])
        valid_files = self.validator.filter_recent_files(recent_files)

        # 如果列表发生了变化，更新偏好设置
        if len(valid_files) != len(recent_files):
            self.set_preference("paths", "recent_files", valid_files)

        return valid_files

    def clear_recent_files(self) -> None:
        """清空最近使用的文件列表"""
        self.set_preference("paths", "recent_files", [])

    def get_ui_preferences(self) -> Dict[str, Any]:
        """获取UI偏好设置"""
        result = self.preferences.get("ui", {})
        return result if isinstance(result, dict) else {}

    def get_processing_preferences(self) -> Dict[str, Any]:
        """获取处理偏好设置"""
        result = self.preferences.get("processing", {})
        return result if isinstance(result, dict) else {}

    def get_advanced_preferences(self) -> Dict[str, Any]:
        """获取高级偏好设置"""
        result = self.preferences.get("advanced", {})
        return result if isinstance(result, dict) else {}

    def get_batch_preferences(self) -> Dict[str, Any]:
        """获取批量处理偏好设置"""
        result = self.preferences.get("batch", {})
        return result if isinstance(result, dict) else {}

    def update_window_geometry(
        self, x: int, y: int, width: int, height: int, maximized: bool = False
    ) -> None:
        """
        更新窗口几何信息

        Args:
            x, y: 窗口位置
            width, height: 窗口大小
            maximized: 是否最大化
        """
        geometry = [x, y, width, height]
        if self.validator.validate_window_geometry(geometry):
            self.set_preference("ui", "window_geometry", geometry)
            self.set_preference("ui", "window_maximized", maximized)
        else:
            self.logger.warning(f"Invalid window geometry: {geometry}")

    def update_splitter_sizes(self, sizes: List[int]) -> None:
        """
        更新分割器大小

        Args:
            sizes: 分割器大小列表
        """
        normalized_sizes = self.validator.normalize_splitter_sizes(sizes)
        self.set_preference("ui", "splitter_sizes", normalized_sizes)

    def reset_to_defaults(self) -> bool:
        """
        重置为默认设置

        Returns:
            是否重置成功
        """
        try:
            self.preferences = PreferencesDefaults.get_default_preferences()
            return self.save_preferences()

        except Exception as e:
            self.logger.error(f"Error resetting preferences: {e}")
            return False


    def export_preferences(self, export_path: str) -> bool:
        """
        导出偏好设置到文件

        Args:
            export_path: 导出文件路径

        Returns:
            是否导出成功
        """
        return self.storage.export_preferences(self.preferences, export_path)

    def import_preferences(self, import_path: str) -> bool:
        """
        从文件导入偏好设置

        Args:
            import_path: 导入文件路径

        Returns:
            是否导入成功
        """
        imported_preferences = self.storage.import_preferences(import_path)
        if imported_preferences:
            self.preferences = imported_preferences
            return self.save_preferences()
        return False


    def auto_save(self) -> None:
        """自动保存偏好设置"""
        if self.get_preference("advanced", "auto_save_interval", 300) > 0:
            self.save_preferences()

    def clear_recent_files(self) -> None:
        """清空最近使用的文件列表"""
        self.set_preference("paths", "recent_files", [])

    def get_ui_preferences(self) -> Dict[str, Any]:
        """获取UI偏好设置"""
        result = self.preferences.get("ui", {})
        return result if isinstance(result, dict) else {}

    def get_processing_preferences(self) -> Dict[str, Any]:
        """获取处理偏好设置"""
        result = self.preferences.get("processing", {})
        return result if isinstance(result, dict) else {}

    def get_advanced_preferences(self) -> Dict[str, Any]:
        """获取高级偏好设置"""
        result = self.preferences.get("advanced", {})
        return result if isinstance(result, dict) else {}

    def get_batch_preferences(self) -> Dict[str, Any]:
        """获取批量处理偏好设置"""
        result = self.preferences.get("batch", {})
        return result if isinstance(result, dict) else {}



# 全局实例（向后兼容性）
_preferences_manager = None


def get_preferences_manager(config_dir: Optional[str] = None) -> UserPreferencesManager:
    """
    获取全局偏好设置管理器实例

    Args:
        config_dir: 配置目录路径

    Returns:
        偏好设置管理器实例
    """
    global _preferences_manager
    if _preferences_manager is None:
        _preferences_manager = UserPreferencesManager(config_dir)
    return _preferences_manager


if __name__ == "__main__":
    """测试代码"""
    # 创建测试实例
    prefs = UserPreferencesManager()

    print("[INFO] 用户偏好设置管理器创建成功")
    print(f"配置目录: {prefs.config_dir}")
    print(f"当前主题: {prefs.get_preference('ui', 'theme')}")

    # 测试设置和获取
    prefs.set_preference("ui", "theme", "light")
    print(f"设置主题为亮色后: {prefs.get_preference('ui', 'theme')}")

    # 测试最近文件
    prefs.add_recent_file("/test/file1.mp4")
    prefs.add_recent_file("/test/file2.jpg")
    print(f"最近文件: {prefs.get_recent_files()}")

    # 测试保存
    if prefs.save_preferences():
        print("[OK] 偏好设置保存成功")
    else:
        print("[ERROR] 偏好设置保存失败")
