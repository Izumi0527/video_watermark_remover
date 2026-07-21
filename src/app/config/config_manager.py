import configparser
import logging
import os
from configparser import ConfigParser
from typing import Any, Dict, MutableMapping, Optional, cast

# 配置日志
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILENAME = "config.ini"
# Could be in user's app data directory or alongside the executable
# For simplicity during development, let's assume it's in a 'configs' subdir of the project root
# Or, if packaged, it might be alongside the executable or in user app data.
# This path needs to be determined robustly.
# For now, let's assume a 'configs' directory relative to this script's location
# (if run from project root)
# or a more robust path finding mechanism.

# A more robust way to find the project root or user config directory:
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # This assumes config_manager.py is in app/
# DEFAULT_CONFIG_DIR = os.path.join(PROJECT_ROOT, "configs")
# DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILENAME)

# For a packaged application, user-specific config is better:
# try:
#     # PySide6 / PyQt6
#     from PySide6.QtCore import QStandardPaths
#     APP_DATA_DIR = QStandardPaths.writableLocation(
#         QStandardPaths.StandardLocation.AppConfigLocation
#     )
#     # APP_DATA_DIR will be like C:/Users/user/AppData/Local/YourAppName
#     # You might need to set organizationName and applicationName for QApplication first.
# except ImportError:
# Fallback for non-Qt environments or if QStandardPaths is not yet usable
APP_NAME = "VideoWatermarkRemover"  # Define your app name
APP_AUTHOR = "YourOrg"  # Define your org name (optional, for path construction)

try:
    # Try to use platformdirs for a robust user config location
    from platformdirs import user_config_dir

    CONFIG_DIR = user_config_dir(APP_NAME, APP_AUTHOR)
except ImportError:
    # Fallback if platformdirs is not installed (though it should be a dependency if used)
    USER_HOME = os.path.expanduser("~")
    if os.name == "nt":  # Windows
        CONFIG_DIR = os.path.join(USER_HOME, "AppData", "Local", APP_AUTHOR, APP_NAME)
    elif os.name == "posix":  # Linux, macOS
        CONFIG_DIR = os.path.join(USER_HOME, ".config", APP_NAME.lower())
    else:
        CONFIG_DIR = os.path.join(USER_HOME, f".{APP_NAME.lower()}")

DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, DEFAULT_CONFIG_FILENAME)


class ConfigManager:
    """
    Manages loading and saving application configuration using configparser.
    """

    # 默认值只维护大写 section 一份；小写镜像（Phase3 测试兼容）由下方程序化生成
    _BASE_DEFAULTS: Dict[str, Dict[str, str]] = {
        "Paths": {
            "ffmpeg_path": "ffmpeg",
            "default_model_dir": "./models",
            "last_input_dir": "",
            "last_output_dir": "",
        },
        "Processing": {
            "default_output_suffix": "_processed",
            "auto_start_processing": "no",
            "gpu_acceleration": "auto",
            # Phase3 期望的键
            "default_detection_sensitivity": "0.5",
            "default_inpainting_method": "auto",
        },
        "Logging": {
            "log_level": "INFO",
            "log_file_path": os.path.join(CONFIG_DIR, "app.log"),
        },
        "Models": {
            "detection_model_path": "",
            "inpainting_model_path": "",
            "default_confidence_threshold": "0.5",
        },
        "Advanced": {},
        "Batch": {
            "max_concurrent_files": "1",
            "auto_retry_failed": "yes",
            "max_retry_count": "3",
            "delete_temp_files": "yes",
            "show_progress_details": "yes",
        },
        "YOLO": {
            # 模型类型：yolo11s / yolo11x-watermark / yolo11x-watermark-corzent / custom
            "model_type": "yolo11x-watermark",
            # 仅当 model_type=custom 时有效
            "custom_model_path": "",
            # 检测阈值
            "conf_threshold": "0.25",
            "iou_threshold": "0.45",
            # 推理批大小
            "batch_size": "8",
            # 是否自动下载缺失模型（yes/no）
            "auto_download_model": "yes",
            # 记录下载源（huggingface/github），便于排障与文档一致性
            "model_download_source": "huggingface",
            # 掩码生成（bbox→mask）微调参数：用于改善边界不准
            "mask_padding_px": "4",
            "mask_padding_ratio": "0.02",
            "mask_padding_max": "24",
            "mask_erode_iterations": "0",
            "mask_dilate_iterations": "0",
            "mask_close_kernel": "5",
        },
    }

    _DEFAULTS: Dict[str, Dict[str, str]] = {
        key: dict(options)
        for section, options in _BASE_DEFAULTS.items()
        for key in (section, section.lower())
    }

    @staticmethod
    def get_config_path() -> str:
        """Returns the determined config path."""
        return DEFAULT_CONFIG_PATH

    @staticmethod
    def load_config(config_path: Optional[str] = None) -> ConfigParser:
        """
        Loads configuration from the given path or the default path.
        If the config file doesn't exist, it creates one with default values.
        """
        path_to_load = config_path if config_path else DEFAULT_CONFIG_PATH
        config = configparser.ConfigParser()

        if not os.path.exists(path_to_load):
            logger.info(f"Config file not found at {path_to_load}. Creating with defaults.")
            ConfigManager._create_default_config(path_to_load)

        try:
            config.read(path_to_load, encoding="utf-8")
        except configparser.Error as e:
            logger.error(f"Error reading config file {path_to_load}: {e}. Loading defaults.")
            # Fallback to in-memory defaults if read fails badly
            config = ConfigManager._get_default_config_parser()

        # Ensure essential sections and options exist, even if file was partially corrupted
        ConfigManager._ensure_default_sections(config)
        return config

    @staticmethod
    def _get_default_config_parser() -> ConfigParser:
        """Returns a ConfigParser object populated with default settings."""
        config = configparser.ConfigParser()
        for section, options in ConfigManager._DEFAULTS.items():
            config[section] = cast(MutableMapping[str, str], options)
        return config

    @staticmethod
    def _ensure_default_sections(config_parser_instance: ConfigParser) -> None:
        """Ensures that the loaded config has all default sections and options."""
        defaults = ConfigManager._get_default_config_parser()
        for section in defaults.sections():
            if not config_parser_instance.has_section(section):
                config_parser_instance.add_section(section)
            for option, value in defaults.items(section):
                if not config_parser_instance.has_option(section, option):
                    config_parser_instance.set(section, option, value)

    # ===================== Phase3 兼容 API =====================

    @staticmethod
    def _get_option_with_fallback(
        config: ConfigParser, sections: list[str], option: str, fallback: Optional[str] = None
    ) -> Optional[str]:
        """按优先级依次读取多个 section 的同名配置。"""
        for section in sections:
            if config.has_option(section, option):
                return config.get(section, option)
        return fallback

    @staticmethod
    def get_detection_sensitivity(config: ConfigParser, default: float = 0.5) -> float:
        """
        获取水印检测敏感度，范围 [0, 1]，无效值回退到默认值。
        """
        raw = ConfigManager._get_option_with_fallback(
            config, ["processing", "Processing"], "default_detection_sensitivity"
        )
        try:
            value = float(raw) if raw is not None else default
        except (TypeError, ValueError):
            return default

        if 0.0 <= value <= 1.0:
            return value
        return default

    @staticmethod
    def get_inpainting_method(config: ConfigParser, default: str = "auto") -> str:
        """
        获取修复方法，限制在允许集合内。
        """
        raw = ConfigManager._get_option_with_fallback(
            config, ["processing", "Processing"], "default_inpainting_method", fallback=default
        )
        method = (raw or default).lower()
        allowed = {"auto", "telea", "ns", "custom"}
        return method if method in allowed else default

    # ===================== 批处理配置 API =====================

    @staticmethod
    def get_batch_max_concurrent(config: ConfigParser, default: int = 1) -> int:
        """
        获取批处理最大并发文件数，限制在1-8之间。
        """
        raw = ConfigManager._get_option_with_fallback(
            config, ["batch", "Batch"], "max_concurrent_files"
        )
        try:
            value = int(raw) if raw is not None else default
        except (TypeError, ValueError):
            return default
        return max(1, min(value, 8))

    @staticmethod
    def get_batch_auto_retry(config: ConfigParser, default: bool = True) -> bool:
        """
        是否自动重试失败的文件。
        """
        raw = ConfigManager._get_option_with_fallback(
            config, ["batch", "Batch"], "auto_retry_failed"
        )
        if raw is None:
            return default
        value = raw.strip().lower()
        return value in {"true", "yes", "1", "y", "on"}

    @staticmethod
    def get_batch_max_retry_count(config: ConfigParser, default: int = 3) -> int:
        """
        获取失败重试次数，限制在0-10之间。
        """
        raw = ConfigManager._get_option_with_fallback(config, ["batch", "Batch"], "max_retry_count")
        try:
            value = int(raw) if raw is not None else default
        except (TypeError, ValueError):
            return default
        return max(0, min(value, 10))

    @staticmethod
    def _create_default_config(config_path: str) -> None:
        """
        Creates a new configuration file with default settings.
        """
        config_dir = os.path.dirname(config_path)
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
                logger.info(f"Created config directory: {config_dir}")
            except OSError as e:
                logger.error(f"Error creating config directory {config_dir}: {e}")
                # Cannot proceed if directory creation fails
                return

        config = ConfigManager._get_default_config_parser()
        try:
            with open(config_path, "w", encoding="utf-8") as configfile:
                config.write(configfile)
            logger.info(f"Default config file created at {config_path}")
        except IOError as e:
            logger.error(f"Error writing default config file to {config_path}: {e}")

    @staticmethod
    def save_config(config: ConfigParser, config_path: Optional[str] = None) -> bool:
        """
        Saves the configuration object to the given path or the default path.
        """
        path_to_save = config_path if config_path else DEFAULT_CONFIG_PATH
        config_dir = os.path.dirname(path_to_save)
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
            except OSError as e:
                logger.error(f"Error creating directory {config_dir} for saving config: {e}")
                return False

        try:
            with open(path_to_save, "w", encoding="utf-8") as configfile:
                config.write(configfile)
            logger.info(f"Config saved to {path_to_save}")
            return True
        except IOError as e:
            logger.error(f"Error saving config to {path_to_save}: {e}")
            return False

    @staticmethod
    def update_config_value(
        section: str, option: str, value: Any, config_path: Optional[str] = None
    ) -> bool:
        """
        Updates a specific value in the config file and saves it.
        """
        config = ConfigManager.load_config(config_path)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, str(value))  # Values must be strings for configparser
        return ConfigManager.save_config(config, config_path)
