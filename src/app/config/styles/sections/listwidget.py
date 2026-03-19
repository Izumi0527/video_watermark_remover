"""列表组件样式片段。"""


def listwidget_styles(colors: dict) -> str:
    """列表组件样式."""
    return f"""
    QListWidget {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        padding: 4px;
        alternate-background-color: {colors['hover']};
    }}

    QListWidget::item {{
        padding: 8px;
        border-radius: 2px;
        margin: 1px;
    }}

    QListWidget::item:selected {{
        background-color: {colors['primary']};
        color: white;
    }}

    QListWidget::item:hover {{
        background-color: {colors['hover']};
    }}
    """
