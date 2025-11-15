import configparser
import logging
import os
from configparser import ConfigParser
from typing import Any, Optional

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
        config["Paths"] = {
            "ffmpeg_path": "ffmpeg",  # Assumes ffmpeg is in PATH
            "default_model_dir": "./models",  # Relative to project or app root
            "last_input_dir": "",
            "last_output_dir": "",
        }
        config["Processing"] = {
            "default_output_suffix": "_processed",
            "auto_start_processing": "no",  # yes/no
            "gpu_acceleration": "auto",  # auto/yes/no
        }
        config["Logging"] = {
            "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
            "log_file_path": os.path.join(
                CONFIG_DIR, "app.log"
            ),  # Use the same dir as config for logs
        }
        config["Models"] = {
            "detection_model_path": "",  # Path to detection model
            "inpainting_model_path": "",  # Path to inpainting model
            "default_confidence_threshold": "0.5",
        }
        # Add more sections and default values as needed
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


if __name__ == "__main__":
    # Example usage:
    logger.info(f"Default config path: {ConfigManager.get_config_path()}")

    # Load (or create if not exists)
    my_config = ConfigManager.load_config()

    # Get a value
    ffmpeg_path = my_config.get("Paths", "ffmpeg_path", fallback="ffmpeg_not_found")
    logger.info(f"FFmpeg path from config: {ffmpeg_path}")

    log_level = my_config.get("Logging", "log_level")
    logger.info(f"Log level: {log_level}")

    # Update a value
    # ConfigManager.update_config_value('Paths', 'last_input_dir', '/new/path/to/videos')
    # updated_config = ConfigManager.load_config() # Reload to see change
    # logger.info(f"Updated last_input_dir: {updated_config.get('Paths', 'last_input_dir')}")

    # Ensure the default config file (default_config.ini in project's configs
    # dir) is also created for reference
    project_configs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs"
    )
    reference_default_config_path = os.path.join(project_configs_dir, "default_config.ini")
    if not os.path.exists(reference_default_config_path):
        logger.info(f"Creating reference default_config.ini at {reference_default_config_path}")
        ConfigManager._create_default_config(reference_default_config_path)
    else:
        logger.info(
            f"Reference default_config.ini already exists at {reference_default_config_path}"
        )

    logger.info("config_manager.py executed directly (for testing purposes).")
