"""数值输入框样式片段。"""


def spinbox_styles(colors: dict) -> str:
    """QSpinBox / QDoubleSpinBox 样式。"""
    return f"""
    QSpinBox,
    QDoubleSpinBox {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 10px;
        padding: 5px 34px 5px 12px;
        min-height: 18px;
        font-weight: 500;
        selection-background-color: {colors['primary_light']};
    }}

    QSpinBox:hover,
    QDoubleSpinBox:hover {{
        background-color: {colors['hover']};
        border-color: {colors['primary_light']};
    }}

    QSpinBox:focus,
    QDoubleSpinBox:focus {{
        border: 2px solid {colors['primary']};
        padding: 4px 33px 4px 11px;
        background-color: {colors['surface']};
    }}

    QSpinBox:disabled,
    QDoubleSpinBox:disabled {{
        background-color: {colors['surface']};
        color: {colors['text_disabled']};
        border-color: {colors['border']};
    }}

    QSpinBox::up-button,
    QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 18px;
        border-left: 1px solid {colors['border']};
        border-bottom: 1px solid {colors['border']};
        border-top-right-radius: 9px;
        background-color: {colors['hover']};
        margin: 2px 2px 0 0;
    }}

    QSpinBox::down-button,
    QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 18px;
        border-left: 1px solid {colors['border']};
        border-bottom-right-radius: 9px;
        background-color: {colors['hover']};
        margin: 0 2px 2px 0;
    }}

    QSpinBox::up-button:hover,
    QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover,
    QDoubleSpinBox::down-button:hover {{
        background-color: {colors['primary_light']};
    }}
    """
