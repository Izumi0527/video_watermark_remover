"""
样式管理包入口，兼容原有导出。

注意：
- 样式相关导出中有一部分依赖 PyQt6（如 `ModernStyleManager` 及调色板应用）。
- 为了让配置/偏好等“非 GUI 逻辑”在无 PyQt6 环境下也能正常导入，本包对 PyQt6 依赖项采用惰性导入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .colors import (
    AVAILABLE_THEMES,
    DEFAULT_THEME,
    THEME_COLORS,
    get_available_themes,
    get_color_value,
    get_theme_colors,
    is_valid_theme,
    validate_theme,
)
from .factory import StyleFactory
from .tokens import FONT_FAMILIES, SIZES

if TYPE_CHECKING:
    from .manager import ModernStyleManager  # noqa: F401

_LAZY_EXPORTS = {
    "ModernStyleManager",
    "apply_global_style",
    "get_dark_style",
    "get_light_style",
    "get_style_manager",
    "get_theme_preview_info",
    "switch_theme",
}

__all__ = [
    "StyleFactory",
    "get_available_themes",
    "get_theme_colors",
    "get_color_value",
    "validate_theme",
    "is_valid_theme",
    "AVAILABLE_THEMES",
    "DEFAULT_THEME",
    "THEME_COLORS",
    "FONT_FAMILIES",
    "SIZES",
    # 惰性导出（PyQt6 依赖）
    *_LAZY_EXPORTS,
]


def __getattr__(name: str) -> Any:  # noqa: ANN401
    if name in _LAZY_EXPORTS:
        try:
            from . import manager as _manager  # 延迟导入（避免无 PyQt6 环境直接失败）

            return getattr(_manager, name)
        except ModuleNotFoundError as exc:
            # 将 PyQt6 缺失转换为 AttributeError，避免影响仅依赖 colors/tokens 的代码路径
            raise AttributeError(f"'{name}' 依赖 PyQt6，当前环境缺失 GUI 依赖：{exc}") from exc

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
