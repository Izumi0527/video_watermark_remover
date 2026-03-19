# flake8: noqa
# mypy: ignore-errors
"""兼容旧路径的用户偏好管理器入口。"""

from .preferences import UserPreferencesManager, get_preferences_manager

__all__ = ["UserPreferencesManager", "get_preferences_manager"]
