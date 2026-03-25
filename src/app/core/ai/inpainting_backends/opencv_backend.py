"""OpenCV 修复后端。"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ..image_inpainter import ImageInpainter
from .base import BaseInpaintingBackend


class OpenCVInpaintingBackend(BaseInpaintingBackend):
    """基于现有 ImageInpainter 的 OpenCV 后端适配器。"""

    backend_id = "opencv"

    def __init__(
        self,
        config=None,
        image_inpainter: Optional[ImageInpainter] = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.image_inpainter = image_inpainter or ImageInpainter(config)

    def load(self) -> bool:
        loaded = bool(self.image_inpainter.load_model())
        self._last_trace = {
            "inpainting_backend": self.backend_id,
            "load_success": loaded,
        }
        return loaded

    def inpaint_frame(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        *,
        inpaint_radius: int,
        quality_level: int,
        opencv_method: str = "auto",
    ) -> np.ndarray:
        result = self.image_inpainter.inpaint_frame(
            frame,
            mask,
            method=opencv_method,
            radius=inpaint_radius,
            quality_level=quality_level,
        )
        resolved = np.asarray(result if result is not None else frame)
        self._last_trace = {
            "inpainting_backend": self.backend_id,
            "inpainting_method": getattr(self.image_inpainter, "last_method_used", None)
            or opencv_method,
            "effective_quality_level": getattr(self.image_inpainter, "last_quality_level", None),
            "effective_inpaint_radius": getattr(
                self.image_inpainter, "last_effective_radius", None
            ),
        }
        return resolved
