#!/usr/bin/env python3
"""样式片段模块

Phase 6 重构: 按组件类型分类到子目录
- containers/: 容器组件（窗口、分组框、标签页）
- controls/: 输入控件（按钮、复选框、下拉框、文本框）
- display/: 展示组件（标签、列表、进度条）
- additional.py: 杂项样式（保持在根目录）

为保持向后兼容，所有样式函数可从此模块直接导入
"""

# 杂项样式
from .additional import additional_styles

# 容器组件样式
from .containers import groupbox_styles, main_window_styles, tab_styles

# 输入控件样式
from .controls import button_styles, checkbox_styles, combobox_styles, textedit_styles

# 展示组件样式
from .display import label_styles, listwidget_styles, progressbar_styles

__all__ = [
    # 容器组件
    "groupbox_styles",
    "main_window_styles",
    "tab_styles",
    # 输入控件
    "button_styles",
    "checkbox_styles",
    "combobox_styles",
    "textedit_styles",
    # 展示组件
    "label_styles",
    "listwidget_styles",
    "progressbar_styles",
    # 杂项
    "additional_styles",
]
