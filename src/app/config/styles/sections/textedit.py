"""文本编辑样式片段。"""


def textedit_styles(colors: dict) -> str:
    """文本编辑样式."""
    return f"""
    QTextEdit {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 8px;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        selection-background-color: {colors['primary']};
    }}

    QTextEdit:focus {{ border-color: {colors['primary']}; }}

    QTextEdit#log_output {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        font-family: 'Consolas', monospace;
        border: 1px solid {colors['border']};
        border-radius: 10px;
        padding: 0;
        selection-background-color: {colors['primary_light']};
    }}
    """
