def additional_styles(colors: dict) -> str:
    return f"""
    QSplitter::handle {{
        background-color: transparent;
        margin: 2px;
    }}

    QSplitter::handle:horizontal {{ width: 4px; }}
    QSplitter::handle:vertical {{ height: 4px; }}

    QSplitter::handle:hover {{
        background-color: {colors['primary_light']};
        border-radius: 2px;
    }}

    QScrollBar:vertical {{
        background-color: transparent;
        width: 10px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {colors['text_disabled']};
        border-radius: 5px;
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {colors['text_secondary']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

    QToolTip {{
        background-color: {colors['card']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 4px;
    }}

    QLabel#preview_placeholder, QLabel#image_label {{
        border: 1px solid {colors['border']};
        border-radius: 8px;
        background-color: {colors['surface']};
        color: {colors['text_secondary']};
        font-size: 11pt;
    }}

    QLabel#comparison_info {{
         background-color: {colors['surface']};
         border: 1px solid {colors['primary']};
         border-radius: 6px;
         padding: 6px 12px;
         color: {colors['primary']};
         font-weight: 600;
    }}

    QFrame#preview_container {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        padding: 6px;
    }}

    QLabel#preview_title {{
        font-weight: bold;
        color: {colors['text_primary']};
        font-size: 14px;
        padding-bottom: 5px;
    }}

    QScrollArea#image_scroll_area {{
        border: 1px solid {colors['border']};
        background-color: {colors['background']};
    }}

    QScrollArea#control_scroll_area {{
        background-color: transparent;
        border: none;
    }}

    QWidget#control_content {{ background-color: transparent; }}

    QLabel#info_label {{
        color: {colors['text_secondary']};
        font-style: italic;
        padding-left: 10px;
    }}

    QFrame#phase_container {{
        background-color: {colors['card']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
    }}

    QLabel#phase_icon {{ font-size: 24px; }}

    QLabel#phase_text {{
        font-size: 14px;
        font-weight: bold;
        color: {colors['text_secondary']};
    }}

    QFrame#info_container {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
    }}

    QLabel[class="info_label"] {{
        font-size: 11px;
        color: {colors['text_secondary']};
    }}

    QLabel[class="info_value"] {{
        font-size: 12px;
        font-weight: bold;
        color: {colors['text_primary']};
    }}
    """
