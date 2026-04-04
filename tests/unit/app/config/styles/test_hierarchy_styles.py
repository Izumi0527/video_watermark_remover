from app.config.styles.colors import get_theme_colors
from app.config.styles.sections.groupbox import groupbox_styles
from app.config.styles.sections.label import label_styles
from app.config.styles.sections.tab import tab_styles


def test_groupbox_styles_reduce_nested_border_weight_and_strengthen_titles():
    """分组框应减轻边框存在感，并提升标题对比度。"""
    colors = get_theme_colors("light")
    stylesheet = groupbox_styles(colors)

    assert f"border: 1px solid {colors['background']};" in stylesheet
    assert "padding: 14px;" in stylesheet
    assert f"color: {colors['text_primary']};" in stylesheet
    assert "font-weight: 700;" in stylesheet
    assert "QGroupBox::title" in stylesheet
    assert f"background-color: {colors['card']};" in stylesheet
    assert "QGroupBox#parameters_group::title" in stylesheet
    assert "QGroupBox#file_operations_group::title" in stylesheet
    assert f"background-color: {colors['background']};" in stylesheet


def test_tab_styles_raise_text_contrast_and_soften_pane_border():
    """参数页签应提升文字对比度，并减轻 pane 边框层级。"""
    colors = get_theme_colors("light")
    stylesheet = tab_styles(colors)

    assert f"QTabWidget::pane" in stylesheet
    assert f"border: 1px solid {colors['background']};" in stylesheet
    assert f"background-color: {colors['hover']};" in stylesheet
    assert f"color: {colors['text_primary']};" in stylesheet
    assert "font-weight: 600;" in stylesheet
    assert f"color: {colors['primary_dark']};" in stylesheet
    assert "font-weight: 700;" in stylesheet


def test_label_styles_promote_title_and_subtitle_readability():
    """标题类标签应更清晰，说明类标签不再依赖斜体维持层级。"""
    colors = get_theme_colors("light")
    stylesheet = label_styles(colors)

    assert f'QLabel[class="title"]' in stylesheet
    assert f"color: {colors['text_primary']};" in stylesheet
    assert f'QLabel[class="subtitle"]' in stylesheet
    assert f"color: {colors['primary_dark']};" in stylesheet
    assert "font-weight: 500;" in stylesheet
    assert f'QLabel[class="info"]' in stylesheet
    assert "font-style: italic;" not in stylesheet
