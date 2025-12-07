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
        "success_light": "#1B5E20",
        "warning": "#FF9800",
        "warning_light": "#3E2723",
        "warning_dark": "#E65100",
        "error": "#F44336",
        "error_light": "#B71C1C",
        "info": "#2196F3",
        # 日志面板专用颜色
        "log_debug": "#888888",
        "log_info": "#FFFFFF",
        "log_warning": "#FFAA00",
        "log_error": "#FF4444",
        "log_timestamp": "#888888",
    },
    "light": {
        # === 主色系 (再次加深以提高标题可读性) ===
        "primary": "#526F85",  # 主色调（再次加深）
        "primary_dark": "#3D5468",  # 主色深
        "primary_light": "#6B8A9F",  # 主色浅
        # === 辅助色 (基于#F2A64C橙色) ===
        "secondary": "#F2A64C",  # 辅助色
        # === 背景色系 (基于#CEE3DF浅灰绿色) ===
        "background": "#CEE3DF",  # 背景色
        "surface": "#FFFFFF",  # 表面色（保持白色）
        "card": "#FFFFFF",  # 卡片色（保持白色）
        "hover": "#E5F0ED",  # 悬停色（#CEE3DF加浅）
        # === 文字色 ===
        "text_primary": "#2A4250",  # 主文字色（加深20%提高可读性）
        "text_secondary": "#4A6B7F",  # 次级文字色（加深）
        "text_disabled": "#A7BDC9",  # 禁用文字色
        # === 边框色 (基于#96B3AE灰绿色) ===
        "border": "#96B3AE",  # 边框色
        # === 状态色 ===
        "success": "#5DA68A",  # 成功色（绿色，与整体协调）
        "success_light": "#D1E8DF",  # 成功浅色
        "warning": "#F2A64C",  # 警告色（用户提供）
        "warning_light": "#FDF0DC",  # 警告浅色
        "warning_dark": "#C4853D",  # 警告深色
        "error": "#E6664E",  # 错误色（用户提供）
        "error_light": "#FADBD6",  # 错误浅色
        "info": "#89A4B7",  # 信息色（与primary一致）
        # === 日志面板专用颜色 ===
        "log_debug": "#5A7A75",  # 调试日志（加深）
        "log_info": "#2A4250",  # 信息日志（加深）
        "log_warning": "#D9942E",  # 警告日志
        "log_error": "#D64D37",  # 错误日志
        "log_timestamp": "#5A7A75",  # 时间戳（加深）
    },
}

# 主题常量
DEFAULT_THEME = "light"
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
