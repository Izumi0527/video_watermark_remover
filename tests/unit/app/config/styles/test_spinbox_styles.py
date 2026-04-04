from app.config.styles.colors import get_theme_colors


def test_spinbox_styles_use_compact_panel_density():
    """SpinBox 样式应与紧凑参数面板风格保持一致。"""
    from app.config.styles.sections.spinbox import spinbox_styles

    stylesheet = spinbox_styles(get_theme_colors("light"))

    assert "QSpinBox," in stylesheet
    assert "QDoubleSpinBox" in stylesheet
    assert "border-radius: 10px;" in stylesheet
    assert "padding: 5px 34px 5px 12px;" in stylesheet
    assert "min-height: 18px;" in stylesheet
    assert "width: 18px;" in stylesheet
    assert "subcontrol-position: top right;" in stylesheet
    assert "subcontrol-position: bottom right;" in stylesheet
