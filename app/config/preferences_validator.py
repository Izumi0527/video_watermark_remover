#!/usr/bin/env python3
"""
用户偏好设置验证和实用工具

提供偏好设置的验证和实用功能：
1. 参数类型验证
2. 参数范围检查
3. 最近文件管理
4. 窗口几何信息管理
5. 偏好设置访问器

从 user_preferences_manager.py 重构拆分
作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import os
import logging
from typing import Dict, Any, List, Optional


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