"""
偏好设置包入口，兼容原有导出接口。
"""

from .defaults import PreferencesDefaults
from .manager import UserPreferencesManager, get_preferences_manager
from .storage import PreferencesStorage
from .validator import PreferencesValidator

__all__ = [
    "PreferencesDefaults",
    "PreferencesStorage",
    "PreferencesValidator",
    "UserPreferencesManager",
    "get_preferences_manager",
]
