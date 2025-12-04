#!/usr/bin/env python3
"""控件类组件样式模块

包含：按钮、复选框、下拉框、文本框等输入控件的样式定义
"""

from ..buttons import button_styles
from ..checkbox import checkbox_styles
from ..combobox import combobox_styles
from ..textedit import textedit_styles

__all__ = [
    "button_styles",
    "checkbox_styles",
    "combobox_styles",
    "textedit_styles",
]
