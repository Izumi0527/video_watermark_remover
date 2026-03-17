"""
配置管理模块（包入口）。

说明：
- 配置与偏好设置应尽量支持无 GUI 环境（例如 CI、纯后端脚本）；
- `ModernStyleManager` 依赖 PyQt6，这里采用惰性导入，避免导入 `app.config` 时强制要求 PyQt6。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config_manager import ConfigManager
from .validators import ConfigValidator, get_validator, validate_param, validate_params

if TYPE_CHECKING:
    from .preferences import UserPreferencesManager
    from .styles import ModernStyleManager

__all__ = [
    "ConfigManager",
    "UserPreferencesManager",
    "ModernStyleManager",
    "ConfigValidator",
    "get_validator",
    "validate_param",
    "validate_params",
]


def __getattr__(name: str) -> Any:  # noqa: ANN401
    if name == "UserPreferencesManager":
        from .preferences import UserPreferencesManager

        return UserPreferencesManager

    if name == "ModernStyleManager":
        from .styles import ModernStyleManager

        return ModernStyleManager

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
