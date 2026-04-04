"""下拉框样式片段。"""


def combobox_styles(colors: dict) -> str:
    """下拉框样式."""
    return f"""
    QComboBox {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 10px;
        padding: 6px 14px 6px 12px;
        min-height: 18px;
        font-weight: 500;
        selection-background-color: {colors['primary_light']};
    }}

    QComboBox#compact_combobox {{
        border-radius: 8px;
        padding: 4px 10px 4px 10px;
        min-height: 14px;
    }}

    QComboBox#log_toolbar_combo {{
        border-radius: 8px;
        padding: 5px 28px 5px 10px;
        min-height: 18px;
        min-width: 96px;
    }}

    QComboBox:hover {{
        background-color: {colors['hover']};
        border-color: {colors['primary_light']};
    }}

    QComboBox:on {{
        background-color: {colors['hover']};
        border-color: {colors['primary']};
    }}

    QComboBox:focus {{
        border: 2px solid {colors['primary']};
        padding: 5px 13px 5px 11px;
        background-color: {colors['surface']};
    }}

    QComboBox#compact_combobox:focus {{
        padding: 3px 9px 3px 9px;
    }}

    QComboBox#log_toolbar_combo:focus {{
        padding: 4px 27px 4px 9px;
    }}

    QComboBox:disabled {{
        background-color: {colors['surface']};
        color: {colors['text_disabled']};
        border-color: {colors['border']};
    }}

    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 28px;
        border: none;
        border-left: 1px solid {colors['border']};
        margin: 2px 4px 2px 0;
    }}

    QComboBox#compact_combobox::drop-down {{
        width: 24px;
    }}

    QComboBox#log_toolbar_combo::drop-down {{
        width: 22px;
    }}

    QAbstractItemView#log_toolbar_combo_view {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['primary_light']};
        border-radius: 8px;
        padding: 6px;
        outline: none;
        selection-background-color: {colors['primary']};
        selection-color: {colors['surface']};
    }}

    QAbstractItemView#log_toolbar_combo_view::item {{
        color: {colors['text_primary']};
        font-weight: 600;
        padding: 4px 10px;
        min-height: 14px;
        border-radius: 6px;
    }}

    QAbstractItemView#log_toolbar_combo_view::item:hover {{
        background-color: {colors['hover']};
    }}

    QAbstractItemView#log_toolbar_combo_view::item:selected {{
        background-color: {colors['primary']};
        color: {colors['surface']};
    }}

    QComboBox::down-arrow {{
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Rya2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Rya2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
        width: 12px;
        height: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 10px;
        padding: 4px;
        selection-background-color: {colors['primary']};
        selection-color: white;
        outline: none;
    }}

    QComboBox QAbstractItemView::item {{
        padding: 6px 12px;
        min-height: 16px;
        border-radius: 7px;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background-color: {colors['hover']};
    }}

    QComboBox QAbstractItemView::item:selected {{
        background-color: {colors['primary']};
        color: {colors['surface']};
    }}
    """
