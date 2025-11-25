def groupbox_styles(colors: dict) -> str:
    return f"""
    QGroupBox {{
        background-color: {colors['card']};
        border: 1px solid {colors['border']};
        border-radius: 10px;
        margin-top: 1.2em;
        padding: 15px;
        font-family: 'Segoe UI', sans-serif;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 20px;
        padding: 0 5px;
        color: {colors['primary']};
        font-weight: bold;
        font-size: 14px;
        background-color: {colors['background']};
    }}
    """
