"""批处理组件模块。"""

from .batch_processor_thread import BatchProcessorThread, FileQueueManager, ProcessingStatus

__all__ = ["BatchProcessingWidget", "BatchProcessorThread", "ProcessingStatus", "FileQueueManager"]


def __getattr__(name: str):
    """按需加载重量级 Qt 组件，避免线程子模块导入时触发 UI 依赖。"""
    if name == "BatchProcessingWidget":
        from .batch_processing_widget import BatchProcessingWidget

        return BatchProcessingWidget
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
