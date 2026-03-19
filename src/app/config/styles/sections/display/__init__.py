#!/usr/bin/env python3
"""显示类组件样式模块

包含：标签、列表、进度条等展示组件的样式定义
"""

from ..label import label_styles
from ..listwidget import listwidget_styles
from ..progress import progressbar_styles

__all__ = [
    "label_styles",
    "listwidget_styles",
    "progressbar_styles",
]
