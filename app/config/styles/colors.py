"""颜色与主题配置."""

from typing import Dict, List

# 主题颜色定义
THEME_COLORS: Dict[str, Dict[str, str]] = {
    "dark": {
        "primary": "#2196F3",
        "primary_dark": "#1976D2",
        "primary_light": "#42A5F5",
        "secondary": "#FF5722",
        "background": "#212121",
        "surface": "#303030",
        "card": "#505050",
        "text_primary": "#FFFFFF",
        "text_secondary": "#B3B3B3",
        "text_disabled": "#757575",
        "border": "#555555",
        "hover": "#484848",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
        "info": "#2196F3",
    },
    "light": {
        "primary": "#2196F3",
        "primary_dark": "#1976D2",
        "primary_light": "#64B5F6",
        "secondary": "#FF5722",
        "background": "#F3F4F6",
        "surface": "#FFFFFF",
        "card": "#FFFFFF",
        "text_primary": "#1F2937",
        "text_secondary": "#6B7280",
        "text_disabled": "#9CA3AF",
        "border": "#E5E7EB",
        "hover": "#F9FAFB",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "info": "#3B82F6",
    },
}

# 主题常量
DEFAULT_THEME = "dark"
AVAILABLE_THEMES: List[str] = list(THEME_COLORS.keys())


def get_theme_colors(theme: str = DEFAULT_THEME) -> Dict[str, str]:
    """获取指定主题的颜色配置。"""
    if theme not in THEME_COLORS:
        raise KeyError(f"主题 '{theme}' 不存在。可用主题: {AVAILABLE_THEMES}")
    return THEME_COLORS[theme].copy()


def validate_theme(theme: str) -> bool:
    """验证主题名称是否有效。"""
    return theme in AVAILABLE_THEMES


def get_color_value(theme: str, color_key: str) -> str:
    """获取指定主题中某个颜色的值。"""
    theme_colors = get_theme_colors(theme)
    if color_key not in theme_colors:
        raise KeyError(f"颜色键 '{color_key}' 在主题 '{theme}' 中不存在")
    return theme_colors[color_key]


def get_available_themes() -> List[str]:
    """获取所有可用主题名称。"""
    return AVAILABLE_THEMES.copy()


def is_valid_theme(theme: str) -> bool:
    """检查主题名称是否有效。"""
    return validate_theme(theme)


__all__ = [
    "THEME_COLORS",
    "DEFAULT_THEME",
    "AVAILABLE_THEMES",
    "get_theme_colors",
    "validate_theme",
    "get_color_value",
    "get_available_themes",
    "is_valid_theme",
]
