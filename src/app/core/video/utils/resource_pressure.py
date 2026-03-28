"""资源压力与内存耗尽错误识别工具。"""

from __future__ import annotations

_RESOURCE_EXHAUSTION_TOKENS = (
    "memoryerror",
    "memory_pressure",
    "unable to allocate",
    "insufficient memory",
    "out of memory",
    "outofmemory",
    "bad allocation",
    "memory allocation failure",
    "cv::outofmemoryerror",
    "ptxas fatal",
    "nvrtc compilation failed",
)


def is_resource_pressure_error(error: Exception | str | None) -> bool:
    """判断异常是否属于资源压力/内存耗尽类错误。"""
    if error is None:
        return False
    if isinstance(error, MemoryError):
        return True

    lowered = str(error).strip().lower()
    return any(token in lowered for token in _RESOURCE_EXHAUSTION_TOKENS)


__all__ = ["is_resource_pressure_error"]
