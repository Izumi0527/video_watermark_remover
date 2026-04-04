"""分组框样式片段。"""


def groupbox_styles(colors: dict) -> str:
    """分组框样式."""
    return f"""
    QGroupBox {{
        background-color: {colors['card']};
        border: 1px solid {colors['background']};
        border-radius: 10px;
        margin-top: 1.2em;
        padding: 14px;
        font-family: 'Segoe UI', sans-serif;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 20px;
        padding: 0 5px;
        color: {colors['text_primary']};
        font-weight: 700;
        font-size: 14px;
        background-color: {colors['card']};
    }}

    QGroupBox#file_operations_group::title,
    QGroupBox#processing_mode_group::title,
    QGroupBox#file_queue_group::title,
    QGroupBox#processing_control_group::title,
    QGroupBox#progress_group::title,
    QGroupBox#parameters_group::title,
    QGroupBox#log_group::title,
    QGroupBox#preview_group::title {{
        background-color: {colors['background']};
    }}
    """
