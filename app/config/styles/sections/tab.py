def tab_styles(colors: dict) -> str:
    return f"""
    QTabWidget::pane {{
        border: 1px solid {colors['border']};
        border-radius: 0 0 8px 8px;
        background-color: {colors['surface']};
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {colors['background']};
        color: {colors['text_secondary']};
        border: 1px solid {colors['border']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 20px;
        margin-right: 4px;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        background-color: {colors['surface']};
        color: {colors['primary']};
        font-weight: bold;
        border-bottom: 1px solid {colors['surface']};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {colors['hover']};
        color: {colors['text_primary']};
    }}
    """
