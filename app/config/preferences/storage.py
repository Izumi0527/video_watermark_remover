"""
偏好设置文件存储管理。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .defaults import PreferencesDefaults


class PreferencesStorage:
    """偏好设置存储管理类。"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".video_watermark_remover"

        self.preferences_file = self.config_dir / "user_preferences.json"
        self.logger = logging.getLogger(__name__)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_preferences(self) -> Dict[str, Any]:
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, "r", encoding="utf-8") as f:
                    loaded_prefs = json.load(f)

                preferences = self._merge_preferences(
                    PreferencesDefaults.get_default_preferences(), loaded_prefs
                )
                self.logger.info("User preferences loaded successfully")
                return preferences

            self.logger.info("No existing preferences file, using defaults")
            return PreferencesDefaults.get_default_preferences()

        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error loading preferences: {e}")
            return PreferencesDefaults.get_default_preferences()

    def save_preferences(self, preferences: Dict[str, Any]) -> bool:
        try:
            with open(self.preferences_file, "w", encoding="utf-8") as f:
                json.dump(preferences, f, indent=2, ensure_ascii=False)
            self.logger.info("User preferences saved successfully")
            return True
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error saving preferences: {e}")
            return False

    def export_preferences(self, preferences: Dict[str, Any], export_path: str) -> bool:
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(preferences, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Preferences exported to: {export_path}")
            return True
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error exporting preferences: {e}")
            return False

    def import_preferences(self, import_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                imported_prefs = json.load(f)

            merged_preferences = self._merge_preferences(
                PreferencesDefaults.get_default_preferences(), imported_prefs
            )

            self.logger.info(f"Preferences imported from: {import_path}")
            return merged_preferences
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Error importing preferences: {e}")
            return None

    def _merge_preferences(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        merged = default.copy()
        for category, settings in loaded.items():
            if category in merged and isinstance(settings, dict):
                merged[category].update(settings)
            else:
                merged[category] = settings
        return merged

    def get_config_dir(self) -> Path:
        return self.config_dir

    def get_preferences_file_path(self) -> Path:
        return self.preferences_file

    def preferences_file_exists(self) -> bool:
        return self.preferences_file.exists()


__all__ = ["PreferencesStorage"]
