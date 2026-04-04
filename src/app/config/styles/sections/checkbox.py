"""复选框样式片段。"""

from pathlib import Path


def _get_checkbox_icon_path() -> str:
    """获取勾选图标的绝对路径（Qt样式表格式）."""
    # 从当前文件位置计算图标路径
    current_dir = Path(__file__).parent
    icon_path = current_dir.parent.parent.parent / "assets" / "icons" / "checkbox_checked.svg"
    # Qt 样式表需要使用正斜杠路径格式
    return icon_path.as_posix()


def checkbox_styles(colors: dict) -> str:
    """复选框样式."""
    icon_path = _get_checkbox_icon_path()

    return f"""
    QCheckBox {{
        color: {colors['text_primary']};
        font-weight: 500;
        spacing: 8px;
    }}

    QCheckBox#log_toolbar_checkbox {{
        spacing: 6px;
        min-height: 34px;
        padding: 0 2px 0 0;
        font-weight: 600;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {colors['text_secondary']};
        border-radius: 4px;
        background-color: transparent;
    }}

    QCheckBox#log_toolbar_checkbox::indicator {{
        width: 16px;
        height: 16px;
        margin-right: 2px;
    }}

    QCheckBox::indicator:checked {{
        background-color: {colors['primary']};
        border-color: {colors['primary']};
        image: url({icon_path});
    }}

    QCheckBox::indicator:hover {{ border-color: {colors['primary']}; }}
    """
