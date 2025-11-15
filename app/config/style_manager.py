#!/usr/bin/env python3
"""
样式管理器核心模块

提供现代化界面样式管理功能：
1. 主题切换和管理
2. 调色板配置
3. 完整样式表生成和应用

从 modern_style_manager.py 重构拆分
作者: Claude Code Assistant  
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

from PyQt6.QtGui import QPalette, QColor
from typing import Dict, Optional

from .theme_definitions import (
    THEME_COLORS, 
    DEFAULT_THEME, 
    get_theme_colors, 
    validate_theme
)
from .style_factory import StyleFactory


class ModernStyleManager:
    """
    现代化样式管理器
    
    负责管理应用程序的整体视觉样式，包括：
    - 主题切换（暗色/亮色）
    - 调色板配置
    - 样式表生成和应用
    """

    def __init__(self, theme: str = DEFAULT_THEME):
        """
        初始化样式管理器
        
        Args:
            theme: 主题名称，默认为暗色主题
            
        Raises:
            ValueError: 如果主题名称无效
        """
        if not validate_theme(theme):
            raise ValueError(f"无效的主题名称: {theme}")
        
        self.theme = theme
        self.colors = get_theme_colors(theme)
        self.style_factory = StyleFactory(self.colors)

    def set_theme(self, theme: str) -> None:
        """
        设置主题
        
        Args:
            theme: 主题名称
            
        Raises:
            ValueError: 如果主题名称无效
        """
        if not validate_theme(theme):
            raise ValueError(f"无效的主题名称: {theme}")
        
        self.theme = theme
        self.colors = get_theme_colors(theme)
        self.style_factory = StyleFactory(self.colors)

    def get_complete_stylesheet(self) -> str:
        """
        获取完整样式表
        
        Returns:
            完整的Qt样式表字符串
        """
        return f"""
        {self.style_factory.get_main_window_stylesheet()}
        {self.style_factory.get_button_stylesheet()}
        {self.style_factory.get_groupbox_stylesheet()}
        {self.style_factory.get_tab_stylesheet()}
        {self.style_factory.get_progressbar_stylesheet()}
        {self.style_factory.get_textedit_stylesheet()}
        {self.style_factory.get_checkbox_stylesheet()}
        {self.style_factory.get_listwidget_stylesheet()}
        {self.style_factory.get_additional_styles()}
        """

    def apply_palette(self, app) -> None:
        """
        应用调色板到应用程序
        
        Args:
            app: Qt应用程序实例
        """
        palette = QPalette()

        # 设置各种颜色角色
        palette.setColor(QPalette.ColorRole.Window, QColor(self.colors["background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(self.colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(self.colors["surface"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self.colors["hover"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(self.colors["card"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(self.colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(self.colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(self.colors["surface"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(self.colors["primary_light"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(self.colors["primary"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(self.colors["primary"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))

        app.setPalette(palette)

    def get_color(self, color_key: str) -> str:
        """
        获取当前主题中指定颜色的值
        
        Args:
            color_key: 颜色键名
            
        Returns:
            颜色值（如：#2196F3）
            
        Raises:
            KeyError: 如果颜色键不存在
        """
        if color_key not in self.colors:
            raise KeyError(f"颜色键 '{color_key}' 在当前主题中不存在")
        
        return self.colors[color_key]

    def get_theme_info(self) -> Dict[str, any]:
        """
        获取当前主题信息
        
        Returns:
            主题信息字典，包含主题名称和主要颜色
        """
        return {
            "name": self.theme,
            "primary_color": self.colors["primary"],
            "background_color": self.colors["background"],
            "text_color": self.colors["text_primary"],
            "total_colors": len(self.colors)
        }

    def apply_to_widget(self, widget, style_type: Optional[str] = None) -> None:
        """
        将样式应用到指定组件
        
        Args:
            widget: Qt组件实例
            style_type: 样式类型（可选，用于特定组件样式）
        """
        if style_type == "button":
            widget.setStyleSheet(self.style_factory.get_button_stylesheet())
        elif style_type == "groupbox":
            widget.setStyleSheet(self.style_factory.get_groupbox_stylesheet())
        elif style_type == "tab":
            widget.setStyleSheet(self.style_factory.get_tab_stylesheet())
        elif style_type == "progressbar":
            widget.setStyleSheet(self.style_factory.get_progressbar_stylesheet())
        elif style_type == "textedit":
            widget.setStyleSheet(self.style_factory.get_textedit_stylesheet())
        elif style_type == "checkbox":
            widget.setStyleSheet(self.style_factory.get_checkbox_stylesheet())
        elif style_type == "listwidget":
            widget.setStyleSheet(self.style_factory.get_listwidget_stylesheet())
        else:
            # 默认应用完整样式表
            widget.setStyleSheet(self.get_complete_stylesheet())

    def __str__(self) -> str:
        """字符串表示"""
        return f"ModernStyleManager(theme='{self.theme}')"

    def __repr__(self) -> str:
        """调试字符串表示"""
        return f"ModernStyleManager(theme='{self.theme}', colors_count={len(self.colors)})"