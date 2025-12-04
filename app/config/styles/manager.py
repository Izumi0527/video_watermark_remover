"""样式管理入口，负责主题切换、调色板与样式应用."""
import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from .colors import (
    AVAILABLE_THEMES,
    DEFAULT_THEME,
    THEME_COLORS,
    get_available_themes,
    get_theme_colors,
    is_valid_theme,
    validate_theme,
)
from .factory import StyleFactory


class ModernStyleManager:
    """现代化样式管理器，负责主题、调色板及样式表应用。"""

    # 为向后兼容暴露颜色
    COLORS = THEME_COLORS

    def __init__(self, theme: str = DEFAULT_THEME):
        """初始化样式管理器."""
        if not validate_theme(theme):
            raise ValueError(f"无效的主题名称: {theme}")

        self.logger = logging.getLogger(__name__)
        self.theme = theme
        self.colors = get_theme_colors(theme)
        self.style_factory = StyleFactory(self.colors)
        self._processing_speeds: List[float] = []
        self._start_time = 0.0

    def set_theme(self, theme: str) -> None:
        """切换到指定主题."""
        if not validate_theme(theme):
            raise ValueError(f"无效的主题名称: {theme}")

        self.theme = theme
        self.colors = get_theme_colors(theme)
        self.style_factory = StyleFactory(self.colors)

    def toggle_theme(self) -> str:
        """在明暗主题间切换并返回新主题名."""
        new_theme = "light" if self.theme == "dark" else "dark"
        self.set_theme(new_theme)
        return new_theme

    @property
    def current_theme(self) -> str:
        """获取当前主题名称。"""
        return self.theme

    def get_complete_stylesheet(self) -> str:
        """组合完整样式表字符串."""
        return f"""
        {self.style_factory.get_main_window_stylesheet()}
        {self.style_factory.get_button_stylesheet()}
        {self.style_factory.get_groupbox_stylesheet()}
        {self.style_factory.get_tab_stylesheet()}
        {self.style_factory.get_progressbar_stylesheet()}
        {self.style_factory.get_textedit_stylesheet()}
        {self.style_factory.get_checkbox_stylesheet()}
        {self.style_factory.get_combobox_stylesheet()}
        {self.style_factory.get_label_stylesheet()}
        {self.style_factory.get_listwidget_stylesheet()}
        {self.style_factory.get_additional_styles()}
        """

    def apply_palette(self, app: QApplication) -> None:
        """将调色板应用到 Qt 应用."""
        palette = QPalette()
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

    def apply_style(self, window: Optional[Any] = None) -> None:
        """将当前主题样式应用到全局或指定窗口."""
        try:
            app = QApplication.instance()
            if app and isinstance(app, QApplication):
                self.apply_palette(app)
                app.setStyleSheet(self.get_complete_stylesheet())

            if window:
                window.update()
        except Exception as exc:
            # 防御性兜底，避免因缺少 QApplication 导致崩溃
            self.logger.warning("apply_style fallback due to error: %s", exc)

    def get_color(self, color_key: str) -> str:
        """获取当前主题指定颜色值."""
        if color_key not in self.colors:
            raise KeyError(f"颜色键 '{color_key}' 在当前主题中不存在")
        return self.colors[color_key]

    def get_theme_info(self) -> Dict[str, Any]:
        """返回当前主题的关键色彩信息."""
        return {
            "name": self.theme,
            "primary_color": self.colors["primary"],
            "background_color": self.colors["background"],
            "text_color": self.colors["text_primary"],
            "total_colors": len(self.colors),
        }

    def apply_to_widget(self, widget, style_type: Optional[str] = None) -> None:
        """根据类型为单个组件应用样式."""
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
        elif style_type == "combobox":
            widget.setStyleSheet(self.style_factory.get_combobox_stylesheet())
        elif style_type == "label":
            widget.setStyleSheet(self.style_factory.get_label_stylesheet())
        elif style_type == "listwidget":
            widget.setStyleSheet(self.style_factory.get_listwidget_stylesheet())
        else:
            widget.setStyleSheet(self.get_complete_stylesheet())

    def __str__(self) -> str:
        """字符串表示。"""
        return f"ModernStyleManager(theme='{self.theme}')"

    def __repr__(self) -> str:
        """调试字符串表示。"""
        return f"ModernStyleManager(theme='{self.theme}', colors_count={len(self.colors)})"


# 便利函数
def get_dark_style() -> ModernStyleManager:
    """获取暗色主题样式管理器."""
    return ModernStyleManager("dark")


def get_light_style() -> ModernStyleManager:
    """获取亮色主题样式管理器."""
    return ModernStyleManager("light")


def get_style_manager(theme: Optional[str] = None) -> ModernStyleManager:
    """按主题创建样式管理器."""
    return ModernStyleManager(theme or DEFAULT_THEME)


def apply_global_style(app, theme: str = DEFAULT_THEME) -> ModernStyleManager:
    """应用全局样式并返回管理器实例."""
    style_manager = ModernStyleManager(theme)
    style_manager.apply_palette(app)
    app.setStyleSheet(style_manager.get_complete_stylesheet())
    return style_manager


def switch_theme(style_manager: ModernStyleManager, new_theme: str) -> bool:
    """切换样式管理器主题，成功返回 True."""
    if not validate_theme(new_theme):
        return False
    try:
        style_manager.set_theme(new_theme)
        return True
    except Exception:
        return False


def get_theme_preview_info(theme: str) -> Optional[dict]:
    """获取指定主题的预览信息."""
    if not is_valid_theme(theme):
        return None
    try:
        temp_manager = ModernStyleManager(theme)
        return temp_manager.get_theme_info()
    except Exception:
        return None


__all__ = [
    "ModernStyleManager",
    "get_dark_style",
    "get_light_style",
    "get_style_manager",
    "apply_global_style",
    "switch_theme",
    "get_theme_preview_info",
    "DEFAULT_THEME",
    "AVAILABLE_THEMES",
    "THEME_COLORS",
    "get_available_themes",
    "is_valid_theme",
]
