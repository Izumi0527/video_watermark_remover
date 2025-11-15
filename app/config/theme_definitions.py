#!/usr/bin/env python3
"""
主题定义模块

定义所有主题的颜色方案和常量：
1. 暗色主题颜色定义
2. 亮色主题颜色定义
3. 主题相关常量

从 modern_style_manager.py 重构拆分
作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

from typing import Dict, Any


# 主题颜色定义
THEME_COLORS: Dict[str, Dict[str, str]] = {
    "dark": {
        "primary": "#2196F3",  # 主色调蓝色
        "primary_dark": "#1976D2",  # 深主色调
        "primary_light": "#42A5F5",  # 浅主色调
        "secondary": "#FF5722",  # 次要色调橙色
        "background": "#212121",  # 主背景色
        "surface": "#303030",  # 表面背景色
        "card": "#424242",  # 卡片背景色
        "text_primary": "#FFFFFF",  # 主文本色
        "text_secondary": "#B3B3B3",  # 次要文本色
        "text_disabled": "#757575",  # 禁用文本色
        "border": "#555555",  # 边框色
        "hover": "#484848",  # 悬停背景色
        "success": "#4CAF50",  # 成功色绿色
        "warning": "#FF9800",  # 警告色黄色
        "error": "#F44336",  # 错误色红色
        "info": "#2196F3",  # 信息色蓝色
    },
    "light": {
        "primary": "#1976D2",  # 主色调蓝色
        "primary_dark": "#1565C0",  # 深主色调
        "primary_light": "#1E88E5",  # 浅主色调
        "secondary": "#D32F2F",  # 次要色调红色
        "background": "#FAFAFA",  # 主背景色
        "surface": "#FFFFFF",  # 表面背景色
        "card": "#FFFFFF",  # 卡片背景色
        "text_primary": "#212121",  # 主文本色
        "text_secondary": "#757575",  # 次要文本色
        "text_disabled": "#BDBDBD",  # 禁用文本色
        "border": "#E0E0E0",  # 边框色
        "hover": "#F5F5F5",  # 悬停背景色
        "success": "#388E3C",  # 成功色绿色
        "warning": "#F57C00",  # 警告色黄色
        "error": "#D32F2F",  # 错误色红色
        "info": "#1976D2",  # 信息色蓝色
    },
}

# 主题常量
DEFAULT_THEME = "dark"
AVAILABLE_THEMES = list(THEME_COLORS.keys())

# 字体定义
FONT_FAMILIES = {
    "default": "'Segoe UI', 'Microsoft YaHei', sans-serif",
    "monospace": "'Consolas', 'Monaco', 'Courier New', monospace",
}

# 尺寸常量
SIZES = {
    "border_radius": {
        "small": "3px",
        "medium": "4px",
        "large": "6px",
        "xlarge": "8px",
    },
    "padding": {
        "small": "4px",
        "medium": "8px",
        "large": "16px",
    },
    "margins": {
        "small": "2px",
        "medium": "8px",
        "large": "10px",
    },
}


def get_theme_colors(theme: str = DEFAULT_THEME) -> Dict[str, str]:
    """
    获取指定主题的颜色配置
    
    Args:
        theme: 主题名称，默认为暗色主题
        
    Returns:
        该主题的颜色字典
        
    Raises:
        KeyError: 如果主题不存在
    """
    if theme not in THEME_COLORS:
        raise KeyError(f"主题 '{theme}' 不存在。可用主题: {AVAILABLE_THEMES}")
    
    return THEME_COLORS[theme].copy()


def validate_theme(theme: str) -> bool:
    """
    验证主题名称是否有效
    
    Args:
        theme: 主题名称
        
    Returns:
        如果主题有效返回True，否则返回False
    """
    return theme in AVAILABLE_THEMES


def get_color_value(theme: str, color_key: str) -> str:
    """
    获取指定主题中某个颜色的值
    
    Args:
        theme: 主题名称
        color_key: 颜色键名
        
    Returns:
        颜色值（如：#2196F3）
        
    Raises:
        KeyError: 如果主题或颜色键不存在
    """
    theme_colors = get_theme_colors(theme)
    if color_key not in theme_colors:
        raise KeyError(f"颜色键 '{color_key}' 在主题 '{theme}' 中不存在")
    
    return theme_colors[color_key]