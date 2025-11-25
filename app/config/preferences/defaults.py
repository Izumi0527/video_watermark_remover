"""
偏好设置默认值定义。
"""

from typing import Any, Dict, cast


class PreferencesDefaults:
    """偏好设置默认值定义类。"""

    DEFAULT_PREFERENCES = {
        "ui": {
            "theme": "dark",
            "window_geometry": [100, 100, 1200, 800],
            "window_maximized": False,
            "splitter_sizes": [400, 400],
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
            "max_threads": -1,
            "cache_size_mb": 512,
            "enable_gpu": False,
            "log_level": "INFO",
            "auto_save_interval": 300,
        },
        "batch": {
            "max_concurrent_files": 1,
            "auto_retry_failed": True,
            "delete_temp_files": True,
            "show_progress_details": True,
        },
    }

    @classmethod
    def get_default_preferences(cls) -> Dict[str, Any]:
        """获取默认偏好设置的深拷贝。"""
        import copy

        return copy.deepcopy(cls.DEFAULT_PREFERENCES)

    @classmethod
    def get_ui_defaults(cls) -> Dict[str, Any]:
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["ui"]).copy()

    @classmethod
    def get_processing_defaults(cls) -> Dict[str, Any]:
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["processing"]).copy()

    @classmethod
    def get_paths_defaults(cls) -> Dict[str, Any]:
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["paths"]).copy()

    @classmethod
    def get_advanced_defaults(cls) -> Dict[str, Any]:
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["advanced"]).copy()

    @classmethod
    def get_batch_defaults(cls) -> Dict[str, Any]:
        return cast(Dict[str, Any], cls.DEFAULT_PREFERENCES["batch"]).copy()


__all__ = ["PreferencesDefaults"]
