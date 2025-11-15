#!/usr/bin/env python3
"""
样式工具函数模块

提供样式管理的便利函数和工具：
1. 便利工厂函数
2. 样式应用辅助函数
3. 主题检测和转换工具

从 modern_style_manager.py 重构拆分
作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

from typing import Optional
from .style_manager import ModernStyleManager
from .theme_definitions import DEFAULT_THEME, AVAILABLE_THEMES, validate_theme


def get_dark_style() -> ModernStyleManager:
    """
    获取暗色主题样式管理器
    
    Returns:
        配置为暗色主题的样式管理器实例
    """
    return ModernStyleManager("dark")


def get_light_style() -> ModernStyleManager:
    """
    获取亮色主题样式管理器
    
    Returns:
        配置为亮色主题的样式管理器实例
    """
    return ModernStyleManager("light")


def get_style_manager(theme: Optional[str] = None) -> ModernStyleManager:
    """
    获取样式管理器实例
    
    Args:
        theme: 主题名称，如果为None则使用默认主题
        
    Returns:
        样式管理器实例
    """
    if theme is None:
        theme = DEFAULT_THEME
    
    return ModernStyleManager(theme)


def apply_global_style(app, theme: str = DEFAULT_THEME) -> ModernStyleManager:
    """
    为整个应用程序应用全局样式
    
    Args:
        app: Qt应用程序实例
        theme: 主题名称
        
    Returns:
        创建的样式管理器实例
    """
    style_manager = ModernStyleManager(theme)
    
    # 应用调色板
    style_manager.apply_palette(app)
    
    # 应用样式表
    app.setStyleSheet(style_manager.get_complete_stylesheet())
    
    return style_manager


def get_available_themes() -> list:
    """
    获取所有可用的主题名称
    
    Returns:
        可用主题名称列表
    """
    return AVAILABLE_THEMES.copy()


def is_valid_theme(theme: str) -> bool:
    """
    检查主题名称是否有效
    
    Args:
        theme: 主题名称
        
    Returns:
        如果主题有效返回True，否则返回False
    """
    return validate_theme(theme)


def switch_theme(style_manager: ModernStyleManager, new_theme: str) -> bool:
    """
    切换样式管理器的主题
    
    Args:
        style_manager: 样式管理器实例
        new_theme: 新主题名称
        
    Returns:
        切换成功返回True，失败返回False
    """
    if not validate_theme(new_theme):
        return False
    
    try:
        style_manager.set_theme(new_theme)
        return True
    except Exception:
        return False


def get_theme_preview_info(theme: str) -> Optional[dict]:
    """
    获取主题预览信息
    
    Args:
        theme: 主题名称
        
    Returns:
        主题预览信息字典，如果主题无效返回None
    """
    if not validate_theme(theme):
        return None
    
    try:
        temp_manager = ModernStyleManager(theme)
        return temp_manager.get_theme_info()
    except Exception:
        return None


if __name__ == "__main__":
    """测试代码"""
    print("=== 样式工具函数测试 ===")
    
    # 测试便利函数
    dark_manager = get_dark_style()
    light_manager = get_light_style()
    
    print(f"暗色主题管理器: {dark_manager}")
    print(f"亮色主题管理器: {light_manager}")
    
    # 测试主题列表
    themes = get_available_themes()
    print(f"可用主题: {themes}")
    
    # 测试主题预览
    for theme in themes:
        info = get_theme_preview_info(theme)
        print(f"{theme} 主题预览: {info}")
    
    print("✅ 样式工具函数测试完成")