def main_window_styles(colors: dict) -> str:
    return f"""
    QMainWindow {{
        background-color: {colors['background']};
        color: {colors['text_primary']};
    }}

    QWidget {{
        color: {colors['text_primary']};
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    }}

    QWidget#header_bar {{
        background-color: {colors['card']};
        border: 1px solid {colors['border']};
        border-radius: 10px;
    }}

    QLabel#title_primary {{
        font-size: 18px;
        font-weight: bold;
        color: {colors['primary']};
        padding: 0px;
        margin: 0px;
    }}

    QLabel#title_secondary {{
        font-size: 14px;
        font-weight: 500;
        color: {colors['text_secondary']};
        padding: 0px;
        margin: 0px;
    }}

    QLabel#status_badge {{
        padding: 6px 12px;
        border-radius: 14px;
        background-color: {colors['card']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        font-weight: 600;
        font-size: 12px;
    }}
    """
