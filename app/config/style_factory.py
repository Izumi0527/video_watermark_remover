#!/usr/bin/env python3
"""
样式工厂模块

提供各种UI组件的样式表生成功能：
1. 基础组件样式（按钮、标签等）
2. 高级组件样式（标签页、进度条等）
3. 复合样式生成器

从 modern_style_manager.py 重构拆分
作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

from typing import Dict


class StyleFactory:
    """样式工厂类，生成各种UI组件的样式表"""
    
    def __init__(self, theme_colors: Dict[str, str]):
        """
        初始化样式工厂
        
        Args:
            theme_colors: 主题颜色字典
        """
        self.colors = theme_colors
    
    def get_main_window_stylesheet(self) -> str:
        """获取主窗口样式表"""
        return f"""
        QMainWindow {{
            background-color: {self.colors['background']};
            color: {self.colors['text_primary']};
        }}

        QWidget {{
            background-color: {self.colors['background']};
            color: {self.colors['text_primary']};
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        }}

        /* 标题标签 */
        QLabel#title {{
            font-size: 18px;
            font-weight: bold;
            color: {self.colors['primary']};
            padding: 10px;
        }}

        /* 状态标签 */
        QLabel#status {{
            color: {self.colors['text_secondary']};
            padding: 5px;
        }}
        """

    def get_button_stylesheet(self) -> str:
        """获取按钮样式表"""
        return f"""
        QPushButton {{
            background-color: {self.colors['surface']};
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            min-height: 20px;
        }}

        QPushButton:hover {{
            background-color: {self.colors['hover']};
            border-color: {self.colors['primary_light']};
        }}

        QPushButton:pressed {{
            background-color: {self.colors['primary_dark']};
            color: white;
        }}

        QPushButton:disabled {{
            background-color: {self.colors['surface']};
            color: {self.colors['text_disabled']};
            border-color: {self.colors['text_disabled']};
        }}

        /* 主要按钮样式 */
        QPushButton#primary {{
            background-color: {self.colors['primary']};
            color: white;
            border: none;
            font-weight: bold;
        }}

        QPushButton#primary:hover {{
            background-color: {self.colors['primary_light']};
        }}

        QPushButton#primary:pressed {{
            background-color: {self.colors['primary_dark']};
        }}

        QPushButton#primary:disabled {{
            background-color: {self.colors['text_disabled']};
        }}

        /* 成功按钮样式 */
        QPushButton#success {{
            background-color: {self.colors['success']};
            color: white;
            border: none;
            font-weight: bold;
        }}

        QPushButton#success:hover {{
            background-color: #66BB6A;
        }}

        /* 危险按钮样式 */
        QPushButton#danger {{
            background-color: {self.colors['error']};
            color: white;
            border: none;
            font-weight: bold;
        }}

        QPushButton#danger:hover {{
            background-color: #EF5350;
        }}
        """

    def get_groupbox_stylesheet(self) -> str:
        """获取分组框样式表"""
        return f"""
        QGroupBox {{
            background-color: {self.colors['card']};
            border: 1px solid {self.colors['border']};
            border-radius: 8px;
            margin-top: 8px;
            padding-top: 10px;
            font-weight: 500;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: {self.colors['primary']};
            font-weight: bold;
        }}
        """

    def get_tab_stylesheet(self) -> str:
        """获取标签页样式表"""
        return f"""
        QTabWidget::pane {{
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            background-color: {self.colors['surface']};
        }}

        QTabBar::tab {{
            background-color: {self.colors['surface']};
            color: {self.colors['text_secondary']};
            border: 1px solid {self.colors['border']};
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            padding: 8px 16px;
            margin-right: 2px;
            min-width: 80px;
        }}

        QTabBar::tab:selected {{
            background-color: {self.colors['primary']};
            color: white;
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {self.colors['hover']};
            color: {self.colors['text_primary']};
        }}
        """

    def get_progressbar_stylesheet(self) -> str:
        """获取进度条样式表"""
        return f"""
        QProgressBar {{
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            background-color: {self.colors['surface']};
            text-align: center;
            color: {self.colors['text_primary']};
            font-weight: bold;
        }}

        QProgressBar::chunk {{
            background-color: {self.colors['primary']};
            border-radius: 3px;
        }}
        """

    def get_textedit_stylesheet(self) -> str:
        """获取文本编辑框样式表"""
        return f"""
        QTextEdit {{
            background-color: {self.colors['surface']};
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            padding: 8px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            selection-background-color: {self.colors['primary']};
        }}

        QTextEdit:focus {{
            border-color: {self.colors['primary']};
        }}
        """

    def get_checkbox_stylesheet(self) -> str:
        """获取复选框样式表"""
        return f"""
        QCheckBox {{
            color: {self.colors['text_primary']};
            font-weight: 500;
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 2px solid {self.colors['border']};
            border-radius: 3px;
            background-color: {self.colors['surface']};
        }}

        QCheckBox::indicator:checked {{
            background-color: {self.colors['primary']};
            border-color: {self.colors['primary']};
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiI
                HZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3J
                nLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEzLjUgNEw2IDExLjUgMi41IDgiIHN0cm9rZT0id2hpd
                GUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZ
                WpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
        }}

        QCheckBox::indicator:hover {{
            border-color: {self.colors['primary_light']};
        }}
        """

    def get_listwidget_stylesheet(self) -> str:
        """获取列表组件样式表"""
        return f"""
        QListWidget {{
            background-color: {self.colors['surface']};
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            padding: 4px;
            alternate-background-color: {self.colors['hover']};
        }}

        QListWidget::item {{
            padding: 8px;
            border-radius: 2px;
            margin: 1px;
        }}

        QListWidget::item:selected {{
            background-color: {self.colors['primary']};
            color: white;
        }}

        QListWidget::item:hover {{
            background-color: {self.colors['hover']};
        }}
        """

    def get_additional_styles(self) -> str:
        """获取额外的UI组件样式"""
        return f"""
        /* 分割器样式 */
        QSplitter::handle {{
            background-color: {self.colors['border']};
        }}

        QSplitter::handle:horizontal {{
            width: 2px;
        }}

        QSplitter::handle:vertical {{
            height: 2px;
        }}

        /* 滚动条样式 */
        QScrollBar:vertical {{
            background-color: {self.colors['surface']};
            width: 12px;
            border: none;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {self.colors['border']};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {self.colors['text_secondary']};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}

        /* 工具提示样式 */
        QToolTip {{
            background-color: {self.colors['card']};
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            padding: 4px;
        }}
        """