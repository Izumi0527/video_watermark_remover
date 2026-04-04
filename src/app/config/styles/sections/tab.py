"""标签页样式片段。"""


def tab_styles(colors: dict) -> str:
    """标签页样式."""
    return f"""
    QTabWidget::pane {{
        border: 1px solid {colors['background']};
        border-radius: 0 0 8px 8px;
        background-color: {colors['surface']};
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {colors['hover']};
        color: {colors['text_primary']};
        border: 1px solid {colors['background']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 20px;
        margin-right: 4px;
        font-weight: 600;
    }}

    QTabBar::tab:selected {{
        background-color: {colors['surface']};
        color: {colors['primary_dark']};
        font-weight: 700;
        border-bottom: 1px solid {colors['surface']};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {colors['hover']};
        color: {colors['text_primary']};
    }}
    """
