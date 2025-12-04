#!/usr/bin/env python3
"""
高级处理参数控制界面 - Tab页面实现

包含各个参数控制Tab的具体实现：
1. 水印检测参数Tab
2. 图像修复参数Tab
3. 性能参数Tab
4. 输出参数Tab

注意：此文件保留用于向后兼容，实际实现已拆分到 tabs/ 子目录
"""

# Phase 6: 从拆分后的模块重新导出（向后兼容）
from .tabs import (
    DetectionParametersTab,
    InpaintingParametersTab,
    OutputParametersTab,
    PerformanceParametersTab,
)

__all__ = [
    "DetectionParametersTab",
    "InpaintingParametersTab",
    "PerformanceParametersTab",
    "OutputParametersTab",
]
