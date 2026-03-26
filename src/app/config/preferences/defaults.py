"""偏好设置默认值定义."""

from typing import Any, Dict, cast

from ..advanced_params import AdvancedParamsSnapshot
from ..styles.colors import DEFAULT_THEME


class PreferencesDefaults:
    """偏好设置默认值定义类."""

    DEFAULT_PREFERENCES = {
        "ui": {
            "theme": DEFAULT_THEME,
            "window_geometry": [100, 100, 1920, 1080],  # 同步更新为更大的默认窗口
            "window_maximized": False,
            "splitter_sizes": [550, 450],  # 55:45 比例（普通窗口默认）
            "active_tab": 0,
        },
        "processing": {
            "auto_detect": True,
            "detection_sensitivity": 0.5,
            "default_inpainting_method": "auto",
            "preserve_audio": True,
            "output_quality": "high",
        },
        "paths": {
            "last_input_dir": "",
            "last_output_dir": "",
            "recent_files": [],
            "ffmpeg_path": "",
        },
        "advanced": {
            "max_threads": 0,
            "cache_size_mb": 512,
            "enable_gpu": True,
            "log_level": "INFO",
            "auto_save_interval": 300,
        },
        "advanced_params": AdvancedParamsSnapshot.defaults().to_dict(),
        "batch": {
            "max_concurrent_files": 1,
            "auto_retry_failed": True,
            "max_retry_count": 3,
            "delete_temp_files": True,
            "show_progress_details": True,
        },
    }

    @classmethod
    def get_default_preferences(cls) -> Dict[str, Any]:
        """获取默认偏好设置的深拷贝."""
        import copy

        return copy.deepcopy(cls.DEFAULT_PREFERENCES)

    @classmethod
    def get_ui_defaults(cls) -> Dict[str, Any]:
        """获取 UI 默认设置."""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["ui"]).copy()

    @classmethod
    def get_processing_defaults(cls) -> Dict[str, Any]:
        """获取处理相关默认设置."""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["processing"]).copy()

    @classmethod
    def get_paths_defaults(cls) -> Dict[str, Any]:
        """获取路径相关默认设置."""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["paths"]).copy()

    @classmethod
    def get_advanced_defaults(cls) -> Dict[str, Any]:
        """获取高级功能默认设置."""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["advanced"]).copy()

    @classmethod
    def get_batch_defaults(cls) -> Dict[str, Any]:
        """获取批量处理默认设置."""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["batch"]).copy()

    @classmethod
    def get_advanced_params_defaults(cls) -> Dict[str, Any]:
        """获取统一高级性能参数默认设置。"""
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["advanced_params"]).copy()


__all__ = ["PreferencesDefaults"]
