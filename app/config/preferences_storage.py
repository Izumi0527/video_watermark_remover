#!/usr/bin/env python3
"""
用户偏好设置存储管理

提供偏好设置的持久化存储功能：
1. 文件读取和写入
2. JSON序列化和反序列化
3. 配置文件路径管理
4. 存储错误处理
5. 偏好设置合并逻辑

从 user_preferences_manager.py 重构拆分
作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .preferences_defaults import PreferencesDefaults


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