#!/usr/bin/env python3
"""
界面样式管理模块（合并版）

提供完整的样式管理功能：
1. 主题定义（ThemeDefinitions）
2. 样式工厂（StyleFactory）
3. 核心管理器（ModernStyleManager）
4. 便利函数

重构说明：
将原来的 5 个文件合并为 1 个，简化 config/ 目录结构
- theme_definitions.py → 主题常量和函数
- style_factory.py → StyleFactory 类
- style_manager.py → ModernStyleManager 类
- style_utils.py → 便利函数
- modern_style_manager.py → 兼容层导出

作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v3.0 (合并版)
"""

from PyQt6.QtGui import QPalette, QColor
from typing import Dict, Any, Optional


# ============================================================
# 主题定义
# ============================================================

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


# ============================================================
# 样式工厂
# ============================================================

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


# ============================================================
# 核心管理器
# ============================================================

class ModernStyleManager:
    """
    现代化样式管理器

    负责管理应用程序的整体视觉样式，包括：
    - 主题切换（暗色/亮色）
    - 调色板配置
    - 样式表生成和应用
    """

    # 为了向后兼容，保留原始的COLORS类属性
    COLORS = THEME_COLORS

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

    def get_theme_info(self) -> Dict[str, Any]:
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


# ============================================================
# 便利函数
# ============================================================

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


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    """测试代码"""
    print("=== 样式管理模块测试 ===")

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

    # 测试主题切换
    style_manager = get_dark_style()
    print(f"\n当前主题: {style_manager.theme}")
    print(f"主色调: {style_manager.colors['primary']}")

    if switch_theme(style_manager, "light"):
        print(f"切换后主题: {style_manager.theme}")
        print(f"主色调: {style_manager.colors['primary']}")

    print("\n✅ 样式管理模块测试完成")
