import types

import pytest

pytest.importorskip("PyQt6")

from app.config import styles


def test_exports():
    """确保关键导出存在且可用。"""
    assert hasattr(styles, "ModernStyleManager")
    assert hasattr(styles, "StyleFactory")
    assert hasattr(styles, "DEFAULT_THEME")
    assert hasattr(styles, "get_available_themes")
    assert hasattr(styles, "get_theme_colors")


def test_theme_functions():
    """验证主题基础函数行为。"""
    themes = styles.get_available_themes()
    assert "dark" in themes
    assert "light" in themes

    colors = styles.get_theme_colors("dark")
    assert colors["primary"].startswith("#")
    assert styles.get_color_value("light", "primary").startswith("#")
    assert styles.validate_theme("dark") is True
    assert styles.is_valid_theme("unknown") is False


def test_manager_basic_usage(qtbot):
    """创建管理器、切换主题并生成样式表。"""
    manager = styles.ModernStyleManager(styles.DEFAULT_THEME)
    assert manager.current_theme == styles.DEFAULT_THEME

    switched = manager.toggle_theme()
    assert switched in styles.AVAILABLE_THEMES

    stylesheet = manager.get_complete_stylesheet()
    assert "QMainWindow" in stylesheet
    assert "QPushButton" in stylesheet


def test_style_factory_sections():
    """确保工厂各方法返回字符串。"""
    colors = styles.get_theme_colors("dark")
    factory = styles.StyleFactory(colors)

    methods = [
        factory.get_main_window_stylesheet,
        factory.get_button_stylesheet,
        factory.get_groupbox_stylesheet,
        factory.get_tab_stylesheet,
        factory.get_progressbar_stylesheet,
        factory.get_textedit_stylesheet,
        factory.get_checkbox_stylesheet,
        factory.get_combobox_stylesheet,
        factory.get_label_stylesheet,
        factory.get_listwidget_stylesheet,
        factory.get_additional_styles,
    ]

    for method in methods:
        result = method()
        assert isinstance(result, str)
        assert len(result) > 10


def test_apply_global_style(monkeypatch):
    """模拟 app 对象应用全局样式（无真实 Qt）。"""
    applied = {}

    class DummyApp:
        def __init__(self):
            self.palette_set = False
            self.stylesheet_set = False

        def setPalette(self, palette):
            applied["palette"] = palette
            self.palette_set = True

        def setStyleSheet(self, ss):
            applied["stylesheet"] = ss
            self.stylesheet_set = True

    dummy_app = DummyApp()

    # 替换 QPalette/QColor 创建以避免真实调用
    class DummyColor:
        def __init__(self, *_args, **_kwargs):
            pass

    class DummyPalette:
        ColorRole = types.SimpleNamespace(
            Window=1,
            WindowText=2,
            Base=3,
            AlternateBase=4,
            ToolTipBase=5,
            ToolTipText=6,
            Text=7,
            Button=8,
            ButtonText=9,
            BrightText=10,
            Link=11,
            Highlight=12,
            HighlightedText=13,
        )

        def setColor(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr("app.config.styles.manager.QColor", DummyColor)
    monkeypatch.setattr("app.config.styles.manager.QPalette", DummyPalette)

    styles.apply_global_style(dummy_app, theme="dark")
    assert dummy_app.palette_set
    assert dummy_app.stylesheet_set
