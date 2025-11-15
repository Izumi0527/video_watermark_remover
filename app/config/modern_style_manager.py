#!/usr/bin/env python3
"""
现代化界面样式管理器 - 兼容层

保持向后兼容性的统一接口，内部使用重构后的模块化结构：
- theme_definitions: 主题颜色定义
- style_factory: 样式表生成工厂
- style_manager: 核心管理器类
- style_utils: 便利工具函数

重构完成日期: 2025-09-06
作者: Claude Code Assistant
版本: v1.0 (重构版)
"""

# 导入重构后的模块
from .theme_definitions import (
    THEME_COLORS,
    DEFAULT_THEME,
    AVAILABLE_THEMES,
    get_theme_colors,
    validate_theme
)

from .style_factory import StyleFactory

from .style_manager import ModernStyleManager as _ModernStyleManager

from .style_utils import (
    get_dark_style,
    get_light_style,
    get_style_manager,
    apply_global_style,
    get_available_themes,
    is_valid_theme,
    switch_theme,
    get_theme_preview_info
)

# 为了完全向后兼容，重新导出ModernStyleManager类
class ModernStyleManager(_ModernStyleManager):
    """
    现代化样式管理器 - 兼容版本
    
    保持与原始接口完全兼容，同时使用重构后的模块化架构
    """
    
    # 为了向后兼容，保留原始的COLORS类属性
    COLORS = THEME_COLORS
    
    def __init__(self, theme="dark"):
        """
        初始化样式管理器
        
        Args:
            theme: 主题名称，默认为暗色主题
        """
        super().__init__(theme)


# 向后兼容的便利函数（保持原始函数签名）
def get_dark_style():
    """获取暗色主题样式管理器 - 兼容函数"""
    return ModernStyleManager("dark")


def get_light_style():
    """获取亮色主题样式管理器 - 兼容函数"""
    return ModernStyleManager("light")


# 测试代码保持不变
if __name__ == "__main__":
    """测试代码"""
    style_manager = get_dark_style()
    print("✅ 现代化样式管理器创建成功")
    print(f"当前主题: {style_manager.theme}")
    print(f"主色调: {style_manager.colors['primary']}")
    
    # 测试重构后的功能
    print("\n=== 重构后功能测试 ===")
    print(f"可用主题: {get_available_themes()}")
    
    # 测试主题切换
    light_manager = get_light_style()
    print(f"亮色主题主色调: {light_manager.colors['primary']}")
    
    # 测试主题信息
    theme_info = style_manager.get_theme_info()
    print(f"主题信息: {theme_info}")
    
    print("✅ 重构和兼容性测试完成")