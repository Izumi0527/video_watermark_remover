"""标签样式片段。"""


def label_styles(colors: dict) -> str:
    """标签样式."""
    return f"""
    QLabel {{
        color: {colors['text_primary']};
        background-color: transparent;
        border: none;
        padding: 0px;
    }}

    QLabel[class="title"] {{
        font-size: 14px;
        font-weight: bold;
        color: {colors['text_primary']};
    }}

    QLabel[class="subtitle"] {{
        font-size: 12px;
        color: {colors['primary_dark']};
        font-weight: 500;
    }}

    QLabel[class="info"] {{
        color: {colors['text_secondary']};
    }}

    QLabel:disabled {{
        color: {colors['text_disabled']};
    }}
    """
