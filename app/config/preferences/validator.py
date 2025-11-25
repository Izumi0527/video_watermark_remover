"""
偏好设置验证与工具函数。
"""

import logging
import os
from typing import Any, Dict, List


class PreferencesValidator:
    """偏好设置验证和实用工具类。"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def validate_preference_value(self, category: str, key: str, value: Any) -> bool:
        """验证偏好设置值的有效性。"""
        try:
            if category == "ui":
                if key == "theme" and value not in ["dark", "light"]:
                    return False
                if key == "window_geometry" and (not isinstance(value, list) or len(value) != 4):
                    return False
                if key == "window_maximized" and not isinstance(value, bool):
                    return False

            elif category == "processing":
                if key == "detection_sensitivity" and not (0.0 <= value <= 1.0):
                    return False
                if key == "output_quality" and value not in ["low", "medium", "high"]:
                    return False
                if key in ["auto_detect", "preserve_audio"] and not isinstance(value, bool):
                    return False

            elif category == "advanced":
                if key == "max_threads" and not isinstance(value, int):
                    return False
                if key == "cache_size_mb" and (not isinstance(value, int) or value < 0):
                    return False
                if key == "auto_save_interval" and (not isinstance(value, int) or value < 0):
                    return False

            return True

        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error validating preference {category}.{key}: {e}")
            return False

    def filter_recent_files(self, recent_files: List[str]) -> List[str]:
        """过滤并清理最近使用的文件列表。"""
        try:
            valid_files = [f for f in recent_files if os.path.exists(f)]
            return valid_files[:10]
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error filtering recent files: {e}")
            return []

    def add_recent_file(self, recent_files: List[str], file_path: str) -> List[str]:
        """添加文件到最近使用列表。"""
        try:
            recent_files = recent_files.copy()
            if file_path in recent_files:
                recent_files.remove(file_path)
            recent_files.insert(0, file_path)
            return recent_files[:10]
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error adding recent file: {e}")
            return recent_files

    def validate_window_geometry(self, geometry: List[int]) -> bool:
        """验证窗口几何信息。"""
        try:
            if not isinstance(geometry, list) or len(geometry) != 4:
                return False
            x, y, width, height = geometry
            if not all(isinstance(val, int) for val in geometry):
                return False
            if width <= 0 or height <= 0:
                return False
            if abs(x) > 5000 or abs(y) > 5000:
                return False
            return True
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error validating window geometry: {e}")
            return False

    def normalize_splitter_sizes(self, sizes: List[int]) -> List[int]:
        """标准化分割器大小。"""
        try:
            if not isinstance(sizes, list) or not sizes:
                return [400, 400]
            normalized = [max(100, size) for size in sizes if isinstance(size, int)]
            while len(normalized) < 2:
                normalized.append(400)
            return normalized
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error normalizing splitter sizes: {e}")
            return [400, 400]

    def get_safe_preference_value(
        self, preferences: Dict[str, Any], category: str, key: str, default: Any = None
    ) -> Any:
        """安全获取偏好设置值。"""
        try:
            category_prefs = preferences.get(category, {})
            if not isinstance(category_prefs, dict):
                return default

            value = category_prefs.get(key, default)
            if self.validate_preference_value(category, key, value):
                return value

            self.logger.warning(
                f"Invalid preference value {category}.{key}: {value}, using default"
            )
            return default

        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error getting preference {category}.{key}: {e}")
            return default


__all__ = ["PreferencesValidator"]
