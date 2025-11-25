def button_styles(colors: dict) -> str:
    return f"""
    QPushButton {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
        min-height: 25px;
    }}

    QPushButton:hover {{
        background-color: {colors['hover']};
        border-color: {colors['primary_light']};
    }}

    QPushButton:pressed {{
        background-color: {colors['primary_dark']};
        color: white;
    }}

    QPushButton:disabled {{
        background-color: {colors['surface']};
        color: {colors['text_disabled']};
        border-color: {colors['border']};
    }}

    QPushButton#btn_start {{
        background-color: {colors['success']};
        color: white;
        border: none;
        font-size: 14px;
        font-weight: bold;
    }}

    QPushButton#btn_start:hover {{ background-color: #66BB6A; }}
    QPushButton#btn_start:pressed {{ background-color: #388E3C; }}

    QPushButton#btn_start:disabled {{
        background-color: {colors['surface']};
        color: {colors['text_disabled']};
        border: 1px solid {colors['border']};
    }}

    QPushButton#btn_stop {{
        background-color: {colors['error']};
        color: white;
        border: none;
        font-size: 14px;
        font-weight: bold;
    }}

    QPushButton#btn_stop:hover {{ background-color: #EF5350; }}
    QPushButton#btn_stop:pressed {{ background-color: #C62828; }}

    QPushButton#btn_stop:disabled {{
        background-color: {colors['surface']};
        color: {colors['text_disabled']};
        border: 1px solid {colors['border']};
    }}

    QPushButton[class="primary"] {{
        background-color: {colors['primary']};
        color: white;
        border: none;
        font-weight: bold;
    }}

    QPushButton[class="primary"]:hover {{ background-color: {colors['primary_light']}; }}
    QPushButton[class="primary"]:pressed {{ background-color: {colors['primary_dark']}; }}

    QPushButton#btn_import {{
        font-size: 13px;
        min-height: 16px;
        padding: 8px 12px;
    }}

    QPushButton#primary {{
        background-color: {colors['primary']};
        color: white;
        border: none;
        font-weight: bold;
    }}

    QPushButton#primary:hover {{ background-color: {colors['primary_light']}; }}
    QPushButton#primary:pressed {{ background-color: {colors['primary_dark']}; }}
    QPushButton#primary:disabled {{ background-color: {colors['text_disabled']}; }}

    QPushButton#success {{
        background-color: {colors['success']};
        color: white;
        border: none;
        font-weight: bold;
    }}

    QPushButton#success:hover {{ background-color: #66BB6A; }}

    QPushButton#danger {{
        background-color: {colors['error']};
        color: white;
        border: none;
        font-weight: bold;
    }}

    QPushButton#danger:hover {{ background-color: #EF5350; }}

    QPushButton#btn_clear, QPushButton#btn_clear_log, QPushButton#btn_save_log {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        min-height: 16px;
        padding: 8px 12px;
    }}

    QPushButton#btn_clear:hover, QPushButton#btn_clear_log:hover, QPushButton#btn_save_log:hover {{
         border-color: {colors['primary']};
         color: {colors['primary']};
    }}

    QPushButton#btn_export, QPushButton#btn_theme_toggle {{
        min-height: 16px;
        padding: 8px 12px;
    }}
    """
