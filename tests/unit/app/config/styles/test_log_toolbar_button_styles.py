from app.config.styles.colors import get_theme_colors
from app.config.styles.sections.buttons import button_styles
from app.config.styles.sections.checkbox import checkbox_styles
from app.config.styles.sections.combobox import combobox_styles
from app.config.styles.sections.textedit import textedit_styles


def test_log_toolbar_buttons_match_panel_input_height_density():
    """日志工具栏按钮应与上方参数输入框保持接近的垂直厚度。"""
    stylesheet = button_styles(get_theme_colors("light"))

    assert "QPushButton#btn_clear_log, QPushButton#btn_save_log" in stylesheet
    assert "border-radius: 8px;" in stylesheet
    assert "min-height: 18px;" in stylesheet
    assert "padding: 5px 12px;" in stylesheet


def test_log_toolbar_combobox_matches_panel_input_density():
    """日志级别下拉框应在保留完整文本的同时匹配参数输入框厚度。"""
    stylesheet = combobox_styles(get_theme_colors("light"))

    assert "QComboBox#log_toolbar_combo" in stylesheet
    assert "padding: 5px 28px 5px 10px;" in stylesheet
    assert "min-height: 18px;" in stylesheet
    assert "min-width: 96px;" in stylesheet
    assert "padding: 4px 27px 4px 9px;" in stylesheet


def test_log_toolbar_checkbox_uses_compact_indicator():
    """自动滚动复选框应与工具栏控件保持统一高度与更紧凑指示器。"""
    stylesheet = checkbox_styles(get_theme_colors("light"))

    assert "QCheckBox#log_toolbar_checkbox" in stylesheet
    assert "spacing: 6px;" in stylesheet
    assert "min-height: 34px;" in stylesheet
    assert "QCheckBox#log_toolbar_checkbox::indicator" in stylesheet
    assert "width: 16px;" in stylesheet
    assert "height: 16px;" in stylesheet


def test_log_toolbar_popup_has_dedicated_dropdown_view_styles():
    """日志级别下拉弹层应使用局部样式，避免影响全局下拉框。"""
    colors = get_theme_colors("light")
    stylesheet = combobox_styles(colors)

    assert "QAbstractItemView#log_toolbar_combo_view" in stylesheet
    assert f"border: 1px solid {colors['primary_light']};" in stylesheet
    assert "padding: 6px;" in stylesheet
    assert "QAbstractItemView#log_toolbar_combo_view::item" in stylesheet
    assert f"color: {colors['text_primary']};" in stylesheet
    assert "font-weight: 600;" in stylesheet
    assert "padding: 4px 10px;" in stylesheet
    assert "min-height: 14px;" in stylesheet


def test_log_output_uses_readable_surface_and_spacing():
    """日志正文区域应使用更高对比底板与更宽松的内容留白。"""
    stylesheet = textedit_styles(get_theme_colors("light"))
    colors = get_theme_colors("light")

    assert "QTextEdit#log_output" in stylesheet
    assert f"background-color: {colors['surface']};" in stylesheet
    assert "border-radius: 10px;" in stylesheet
    assert "padding: 0;" in stylesheet
