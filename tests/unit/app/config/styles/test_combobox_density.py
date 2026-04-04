from app.config.styles.colors import get_theme_colors
from app.config.styles.sections.combobox import combobox_styles


def test_combobox_styles_use_compact_vertical_density():
    """下拉框应使用更紧凑的上下留白与列表行高。"""
    stylesheet = combobox_styles(get_theme_colors("light"))

    assert "padding: 6px 14px 6px 12px;" in stylesheet
    assert "min-height: 18px;" in stylesheet
    assert "padding: 4px 10px 4px 10px;" in stylesheet
    assert "margin: 2px 4px 2px 0;" in stylesheet
    assert "padding: 4px;" in stylesheet
    assert "padding: 6px 12px;" in stylesheet
    assert "min-height: 16px;" in stylesheet
