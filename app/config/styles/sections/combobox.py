def combobox_styles(colors: dict) -> str:
    return f"""
    QComboBox {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 6px 8px;
        min-height: 25px;
        font-weight: 500;
    }}

    QComboBox:hover {{
        border-color: {colors['primary']};
        background-color: {colors['hover']};
    }}

    QComboBox:focus {{ border-color: {colors['primary']}; }}

    QComboBox:disabled {{
        background-color: {colors['surface']};
        color: {colors['text_disabled']};
        border-color: {colors['border']};
    }}

    QComboBox::drop-down {{ border: none; width: 20px; }}

    QComboBox::down-arrow {{
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Rya2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Rya2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
        width: 12px;
        height: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        selection-background-color: {colors['primary']};
        selection-color: white;
        outline: none;
    }}

    QComboBox QAbstractItemView::item {{
        padding: 6px;
        min-height: 25px;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background-color: {colors['hover']};
    }}
    """
