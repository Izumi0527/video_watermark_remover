#!/usr/bin/env python3
"""
高级参数Tab页面子模块

将各个参数Tab拆分到独立文件，提高可维护性。
"""

from .detection_tab import DetectionParametersTab
from .inpainting_tab import InpaintingParametersTab
from .output_tab import OutputParametersTab
from .performance_tab import PerformanceParametersTab

__all__ = [
    "DetectionParametersTab",
    "InpaintingParametersTab",
    "PerformanceParametersTab",
    "OutputParametersTab",
]
