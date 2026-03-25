"""统一修复后端基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import numpy as np


class BaseInpaintingBackend(ABC):
    """统一修复后端接口。"""

    backend_id = "unknown"

    def __init__(self) -> None:
        self._last_trace: Dict[str, Any] = {}

    @abstractmethod
    def load(self) -> bool:
        """加载后端资源。"""

    @abstractmethod
    def inpaint_frame(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        *,
        inpaint_radius: int,
        quality_level: int,
        opencv_method: str = "auto",
    ) -> np.ndarray:
        """执行单帧修复。"""

    def get_last_trace(self) -> Dict[str, Any]:
        """返回最近一次执行的追溯信息。"""
        return dict(self._last_trace)

    def cleanup(self) -> None:
        """释放资源。"""
