# 高级参数组件模块
from .advanced_parameters_widget import AdvancedParametersWidget
from .advanced_parameters_tabs import (
    DetectionParametersTab,
    InpaintingParametersTab, 
    PerformanceParametersTab,
    OutputParametersTab
)

__all__ = [
    'AdvancedParametersWidget',
    'DetectionParametersTab',
    'InpaintingParametersTab',
    'PerformanceParametersTab', 
    'OutputParametersTab'
]