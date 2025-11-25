"""
基础尺寸和字体配置。
"""

FONT_FAMILIES = {
    "default": "'Segoe UI', 'Microsoft YaHei', sans-serif",
    "monospace": "'Consolas', 'Monaco', 'Courier New', monospace",
}

SIZES = {
    "border_radius": {
        "small": "3px",
        "medium": "4px",
        "large": "6px",
        "xlarge": "8px",
    },
    "padding": {
        "small": "4px",
        "medium": "8px",
        "large": "16px",
    },
    "margins": {
        "small": "2px",
        "medium": "8px",
        "large": "10px",
    },
}

__all__ = ["FONT_FAMILIES", "SIZES"]
