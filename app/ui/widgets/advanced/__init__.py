# 高级参数组件模块
from .advanced_parameters_tabs import (
    DetectionParametersTab,
    InpaintingParametersTab,
    OutputParametersTab,
    PerformanceParametersTab,
)
from .advanced_parameters_widget import AdvancedParametersWidget

__all__ = [
    "AdvancedParametersWidget",
    "DetectionParametersTab",
    "InpaintingParametersTab",
    "PerformanceParametersTab",
    "OutputParametersTab",
]
