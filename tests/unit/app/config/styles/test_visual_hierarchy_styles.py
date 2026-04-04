from app.config.styles.colors import get_theme_colors
from app.config.styles.sections.groupbox import groupbox_styles
from app.config.styles.sections.label import label_styles
from app.config.styles.sections.tab import tab_styles


def test_groupbox_styles_reduce_nested_border_weight_and_strengthen_titles():
    """分组框应减轻边框存在感，同时提升标题对比度。"""
    colors = get_theme_colors("light")
    stylesheet = groupbox_styles(colors)

    assert f"border: 1px solid {colors['background']};" in stylesheet
    assert f"color: {colors['text_primary']};" in stylesheet
    assert f"background-color: {colors['card']};" in stylesheet


def test_tab_styles_raise_text_contrast_and_soften_pane_border():
    """标签页应减轻 pane 边框，并提升未选中/选中文字对比度。"""
    colors = get_theme_colors("light")
    stylesheet = tab_styles(colors)

    assert f"QTabWidget::pane" in stylesheet
    assert f"border: 1px solid {colors['background']};" in stylesheet
    assert f"background-color: {colors['hover']};" in stylesheet
    assert f"color: {colors['text_primary']};" in stylesheet
    assert "font-weight: 600;" in stylesheet
    assert f"color: {colors['primary_dark']};" in stylesheet
    assert "font-weight: 700;" in stylesheet


def test_label_styles_strengthen_title_and_subtitle_readability():
    """标题与副标题标签应使用更强的对比度和更稳定的字重。"""
    colors = get_theme_colors("light")
    stylesheet = label_styles(colors)

    assert 'QLabel[class="title"]' in stylesheet
    assert f"color: {colors['text_primary']};" in stylesheet
    assert 'QLabel[class="subtitle"]' in stylesheet
    assert f"color: {colors['primary_dark']};" in stylesheet
    assert "font-weight: 500;" in stylesheet
