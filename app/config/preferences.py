#!/usr/bin/env python3
"""
用户偏好设置管理模块（合并版）

提供完整的偏好设置管理功能：
1. 默认配置定义（PreferencesDefaults）
2. 文件存储管理（PreferencesStorage）
3. 验证和实用工具（PreferencesValidator）
4. 统一管理接口（UserPreferencesManager）

重构说明：
将原来的 4 个文件合并为 1 个，简化 config/ 目录结构
- preferences_defaults.py → PreferencesDefaults 类
- preferences_storage.py → PreferencesStorage 类
- preferences_validator.py → PreferencesValidator 类
- user_preferences_manager.py → UserPreferencesManager 类

作者: Claude Code Assistant
创建时间: 2025-01-31
版本: v3.0 (合并版)
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, cast
from pathlib import Path


# ============================================================
# 默认配置定义
# ============================================================

class PreferencesDefaults:
    """偏好设置默认值定义类"""

    # 默认偏好设置配置
    DEFAULT_PREFERENCES = {
        "ui": {
            "theme": "dark",  # 界面主题: 'dark' | 'light'
            "window_geometry": [100, 100, 1200, 800],  # 窗口位置和大小 [x, y, width, height]
            "window_maximized": False,  # 是否最大化
            "splitter_sizes": [400, 400],  # 分割器大小
            "active_tab": 0,  # 活动标签页索引
        },
        "processing": {
            "auto_detect": True,  # 自动检测水印
            "detection_sensitivity": 0.5,  # 检测敏感度 (0.1-1.0)
            "default_inpainting_method": "auto",  # 默认修复方法:
            # 'auto' | 'telea' | 'navier_stokes' | 'custom'
            "preserve_audio": True,  # 保留音频
            "output_quality": "high",  # 输出质量: 'low' | 'medium' | 'high'
        },
        "paths": {
            "last_input_dir": "",  # 最后输入目录
            "last_output_dir": "",  # 最后输出目录
            "recent_files": [],  # 最近文件列表 (最多10个)
            "ffmpeg_path": "",  # FFmpeg路径
        },
        "advanced": {
            "max_threads": -1,  # 最大线程数 (-1为自动)
            "cache_size_mb": 512,  # 缓存大小(MB)
            "enable_gpu": False,  # 启用GPU加速
            "log_level": "INFO",  # 日志级别
            "auto_save_interval": 300,  # 自动保存间隔(秒)
        },
        "batch": {
            "max_concurrent_files": 1,  # 最大并发文件数
            "auto_retry_failed": True,  # 自动重试失败的文件
            "delete_temp_files": True,  # 删除临时文件
            "show_progress_details": True,  # 显示详细进度
        },
    }

    @classmethod
    def get_default_preferences(cls) -> Dict[str, Any]:
        """
        获取默认偏好设置的深拷贝

        Returns:
            默认偏好设置字典的副本
        """
        import copy
        return copy.deepcopy(cls.DEFAULT_PREFERENCES)

    @classmethod
    def get_ui_defaults(cls) -> Dict[str, Any]:
        """获取UI相关默认设置"""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["ui"]).copy()

    @classmethod
    def get_processing_defaults(cls) -> Dict[str, Any]:
        """获取处理相关默认设置"""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["processing"]).copy()

    @classmethod
    def get_paths_defaults(cls) -> Dict[str, Any]:
        """获取路径相关默认设置"""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["paths"]).copy()

    @classmethod
    def get_advanced_defaults(cls) -> Dict[str, Any]:
        """获取高级功能默认设置"""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["advanced"]).copy()

    @classmethod
    def get_batch_defaults(cls) -> Dict[str, Any]:
        """获取批量处理默认设置"""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["batch"]).copy()


# ============================================================
# 验证和实用工具
# ============================================================

class PreferencesValidator:
    """偏好设置验证和实用工具类"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_preference_value(self, category: str, key: str, value: Any) -> bool:
        """
        验证偏好设置值的有效性

        Args:
            category: 设置类别
            key: 设置键
            value: 设置值

        Returns:
            是否有效
        """
        try:
            # UI类别验证
            if category == "ui":
                if key == "theme" and value not in ["dark", "light"]:
                    return False
                elif key == "window_geometry" and (not isinstance(value, list) or len(value) != 4):
                    return False
                elif key == "window_maximized" and not isinstance(value, bool):
                    return False

            # 处理类别验证
            elif category == "processing":
                if key == "detection_sensitivity" and not (0.0 <= value <= 1.0):
                    return False
                elif key == "output_quality" and value not in ["low", "medium", "high"]:
                    return False
                elif key in ["auto_detect", "preserve_audio"] and not isinstance(value, bool):
                    return False

            # 高级设置验证
            elif category == "advanced":
                if key == "max_threads" and not isinstance(value, int):
                    return False
                elif key == "cache_size_mb" and (not isinstance(value, int) or value < 0):
                    return False
                elif key == "auto_save_interval" and (not isinstance(value, int) or value < 0):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating preference {category}.{key}: {e}")
            return False

    def filter_recent_files(self, recent_files: List[str]) -> List[str]:
        """
        过滤并清理最近使用的文件列表

        Args:
            recent_files: 原始文件列表

        Returns:
            过滤后的有效文件列表
        """
        try:
            # 过滤掉不存在的文件
            valid_files = [f for f in recent_files if os.path.exists(f)]

            # 限制最多10个文件
            return valid_files[:10]

        except Exception as e:
            self.logger.error(f"Error filtering recent files: {e}")
            return []

    def add_recent_file(self, recent_files: List[str], file_path: str) -> List[str]:
        """
        添加文件到最近使用列表

        Args:
            recent_files: 当前最近文件列表
            file_path: 要添加的文件路径

        Returns:
            更新后的文件列表
        """
        try:
            recent_files = recent_files.copy()

            # 移除已存在的相同文件
            if file_path in recent_files:
                recent_files.remove(file_path)

            # 添加到列表开头
            recent_files.insert(0, file_path)

            # 保持最多10个文件
            return recent_files[:10]

        except Exception as e:
            self.logger.error(f"Error adding recent file: {e}")
            return recent_files

    def validate_window_geometry(self, geometry: List[int]) -> bool:
        """
        验证窗口几何信息的有效性

        Args:
            geometry: 窗口几何信息 [x, y, width, height]

        Returns:
            是否有效
        """
        try:
            if not isinstance(geometry, list) or len(geometry) != 4:
                return False

            x, y, width, height = geometry

            # 检查数值类型
            if not all(isinstance(val, int) for val in geometry):
                return False

            # 检查尺寸有效性
            if width <= 0 or height <= 0:
                return False

            # 检查位置合理性（允许负值，但不能太极端）
            if abs(x) > 5000 or abs(y) > 5000:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating window geometry: {e}")
            return False

    def normalize_splitter_sizes(self, sizes: List[int]) -> List[int]:
        """
        标准化分割器大小

        Args:
            sizes: 分割器大小列表

        Returns:
            标准化后的大小列表
        """
        try:
            if not isinstance(sizes, list) or not sizes:
                return [400, 400]  # 默认大小

            # 确保都是正数
            normalized = [max(100, size) for size in sizes if isinstance(size, int)]

            # 确保至少有两个值
            while len(normalized) < 2:
                normalized.append(400)

            return normalized

        except Exception as e:
            self.logger.error(f"Error normalizing splitter sizes: {e}")
            return [400, 400]

    def get_safe_preference_value(self, preferences: Dict[str, Any],
                                  category: str, key: str, default: Any = None) -> Any:
        """
        安全获取偏好设置值

        Args:
            preferences: 偏好设置字典
            category: 设置类别
            key: 设置键
            default: 默认值

        Returns:
            设置值或默认值
        """
        try:
            category_prefs = preferences.get(category, {})
            if not isinstance(category_prefs, dict):
                return default

            value = category_prefs.get(key, default)

            # 验证值的有效性
            if self.validate_preference_value(category, key, value):
                return value
            else:
                self.logger.warning(f"Invalid preference value {category}.{key}: {value}, using default")
                return default

        except Exception as e:
            self.logger.error(f"Error getting preference {category}.{key}: {e}")
            return default


# ============================================================
# 文件存储管理
# ============================================================

class PreferencesStorage:
    """偏好设置存储管理类"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化存储管理器

        Args:
            config_dir: 配置目录路径，默认为用户主目录下的.video_watermark_remover
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".video_watermark_remover"

        self.preferences_file = self.config_dir / "user_preferences.json"
        self.logger = logging.getLogger(__name__)

        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_preferences(self) -> Dict[str, Any]:
        """
        从文件加载用户偏好设置

        Returns:
            偏好设置字典
        """
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, "r", encoding="utf-8") as f:
                    loaded_prefs = json.load(f)

                # 合并默认设置和加载的设置
                preferences = self._merge_preferences(
                    PreferencesDefaults.get_default_preferences(),
                    loaded_prefs
                )
                self.logger.info("User preferences loaded successfully")
                return preferences
            else:
                self.logger.info("No existing preferences file, using defaults")
                return PreferencesDefaults.get_default_preferences()

        except Exception as e:
            self.logger.error(f"Error loading preferences: {e}")
            return PreferencesDefaults.get_default_preferences()

    def save_preferences(self, preferences: Dict[str, Any]) -> bool:
        """
        保存用户偏好设置到文件

        Args:
            preferences: 偏好设置字典

        Returns:
            是否保存成功
        """
        try:
            with open(self.preferences_file, "w", encoding="utf-8") as f:
                json.dump(preferences, f, indent=2, ensure_ascii=False)

            self.logger.info("User preferences saved successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error saving preferences: {e}")
            return False

    def export_preferences(self, preferences: Dict[str, Any], export_path: str) -> bool:
        """
        导出偏好设置到指定文件

        Args:
            preferences: 偏好设置字典
            export_path: 导出文件路径

        Returns:
            是否导出成功
        """
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(preferences, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Preferences exported to: {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting preferences: {e}")
            return False

    def import_preferences(self, import_path: str) -> Optional[Dict[str, Any]]:
        """
        从指定文件导入偏好设置

        Args:
            import_path: 导入文件路径

        Returns:
            导入的偏好设置字典，失败时返回None
        """
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                imported_prefs = json.load(f)

            # 合并导入的设置和默认设置
            merged_preferences = self._merge_preferences(
                PreferencesDefaults.get_default_preferences(),
                imported_prefs
            )

            self.logger.info(f"Preferences imported from: {import_path}")
            return merged_preferences

        except Exception as e:
            self.logger.error(f"Error importing preferences: {e}")
            return None

    def _merge_preferences(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并默认设置和加载的设置

        Args:
            default: 默认设置
            loaded: 加载的设置

        Returns:
            合并后的设置
        """
        merged = default.copy()

        for category, settings in loaded.items():
            if category in merged and isinstance(settings, dict):
                merged[category].update(settings)
            else:
                merged[category] = settings

        return merged

    def get_config_dir(self) -> Path:
        """获取配置目录路径"""
        return self.config_dir

    def get_preferences_file_path(self) -> Path:
        """获取偏好设置文件路径"""
        return self.preferences_file

    def preferences_file_exists(self) -> bool:
        """检查偏好设置文件是否存在"""
        return self.preferences_file.exists()


# ============================================================
# 统一管理接口
# ============================================================

class UserPreferencesManager:
    """用户偏好设置管理器 - 统一管理接口"""

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


# ============================================================
# 全局实例（向后兼容性）
# ============================================================

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


# ============================================================
# 测试代码
# ============================================================

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
