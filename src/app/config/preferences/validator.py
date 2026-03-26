"""偏好设置验证与工具函数."""

import logging
import os
from typing import Any, Dict, List


class PreferencesValidator:
    """偏好设置验证和实用工具类."""

    def __init__(self) -> None:
        """初始化验证器."""
        self.logger = logging.getLogger(__name__)

    def validate_preference_value(self, category: str, key: str, value: Any) -> bool:  # noqa: C901
        """验证偏好设置值的有效性."""
        try:
            if category == "ui":
                return self._validate_ui(key, value)
            if category == "processing":
                return self._validate_processing(key, value)
            if category == "advanced":
                return self._validate_advanced(key, value)
            if category == "advanced_params":
                return self._validate_advanced_params(key, value)
            return True
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error validating preference {category}.{key}: {e}")
            return False

    def _validate_ui(self, key: str, value: Any) -> bool:
        """验证 UI 分类的偏好值."""
        if key == "theme":
            return value in ["dark", "light"]
        if key == "window_geometry":
            return isinstance(value, list) and len(value) == 4
        if key == "window_maximized":
            return isinstance(value, bool)
        return True

    def _validate_processing(self, key: str, value: Any) -> bool:
        """验证处理分类的偏好值."""
        if key == "detection_sensitivity":
            return isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0
        if key == "output_quality":
            return value in ["low", "medium", "high"]
        if key in ["auto_detect", "preserve_audio"]:
            return isinstance(value, bool)
        return True

    def _validate_advanced(self, key: str, value: Any) -> bool:
        """验证高级分类的偏好值."""
        if key == "max_threads":
            return isinstance(value, int)
        if key == "cache_size_mb":
            return isinstance(value, int) and value >= 0
        if key == "auto_save_interval":
            return isinstance(value, int) and value >= 0
        return True

    def _validate_advanced_params(self, key: str, value: Any) -> bool:
        """验证统一性能参数分类的偏好值。"""
        if key == "processing_mode":
            return value in {"auto", "single_process", "multiprocess", "pipeline"}
        if key == "worker_count":
            return isinstance(value, int) and 0 <= value <= 16
        if key == "enable_gpu":
            return isinstance(value, bool)
        if key == "gpu_memory_limit_mb":
            return isinstance(value, int) and value >= 256
        if key == "enable_cache":
            return isinstance(value, bool)
        if key == "cache_size_mb":
            return isinstance(value, int) and value >= 64
        if key == "batch_max_concurrent_files":
            return isinstance(value, int) and value >= 1
        if key == "batch_auto_retry_failed":
            return isinstance(value, bool)
        if key == "batch_max_retry_count":
            return isinstance(value, int) and value >= 0
        return True

    def filter_recent_files(self, recent_files: List[str]) -> List[str]:
        """过滤并清理最近使用的文件列表."""
        try:
            valid_files = [f for f in recent_files if os.path.exists(f)]
            return valid_files[:10]
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error filtering recent files: {e}")
            return []

    def add_recent_file(self, recent_files: List[str], file_path: str) -> List[str]:
        """添加文件到最近使用列表."""
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
        """验证窗口几何信息."""
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
        """标准化分割器大小."""
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
        """安全获取偏好设置值."""
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
