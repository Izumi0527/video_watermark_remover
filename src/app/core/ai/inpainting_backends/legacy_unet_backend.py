"""兼容 legacy U-Net 修复后端。"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

import numpy as np

from .base import BaseInpaintingBackend

if TYPE_CHECKING:
    from ..dl_inpainter import DeepLearningInpainter


class LegacyUNetInpaintingBackend(BaseInpaintingBackend):
    """对现有 DeepLearningInpainter 的统一后端包装。"""

    backend_id = "legacy_unet"

    def __init__(
        self,
        config=None,
        torch_device=None,
        model_path: Optional[str] = None,
        dl_inpainter: Optional["DeepLearningInpainter"] = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.torch_device = torch_device
        self.model_path = model_path
        self.dl_inpainter = dl_inpainter
        self.loaded_model_path: Optional[str] = None

    def load(self) -> bool:
        if not self.model_path:
            self._last_trace = {
                "inpainting_backend": self.backend_id,
                "load_success": False,
                "load_failure_reason": "missing_inpainting_model_path",
                "configured_inpainting_model_path": self.model_path,
                "loaded_inpainting_model_path": None,
            }
            return False

        if not os.path.exists(self.model_path):
            self._last_trace = {
                "inpainting_backend": self.backend_id,
                "load_success": False,
                "load_failure_reason": "inpainting_model_path_not_found",
                "configured_inpainting_model_path": self.model_path,
                "loaded_inpainting_model_path": None,
            }
            return False

        from ..dl_inpainter import DeepLearningInpainter

        self.dl_inpainter = self.dl_inpainter or DeepLearningInpainter(
            config=self.config,
            device=self.torch_device,
        )
        loaded = bool(self.dl_inpainter.load_model(model_path=self.model_path))
        self.loaded_model_path = self.model_path if loaded else None
        self._last_trace = {
            "inpainting_backend": self.backend_id,
            "load_success": loaded,
            "load_failure_reason": None if loaded else "inpainting_model_load_failed",
            "configured_inpainting_model_path": self.model_path,
            "loaded_inpainting_model_path": self.loaded_model_path,
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
        if self.dl_inpainter is None:
            raise RuntimeError("legacy U-Net backend not loaded")

        result = self.dl_inpainter.inpaint_frame(
            frame,
            mask,
            radius=inpaint_radius,
            quality_level=quality_level,
        )
        profile = getattr(self.dl_inpainter, "last_profile_used", None)
        retry_profile = getattr(self.dl_inpainter, "last_retry_profile_used", None)
        retry_info = getattr(self.dl_inpainter, "last_retry_info", None)
        chosen_profile = profile if isinstance(profile, dict) else retry_profile
        chosen_quality = (
            chosen_profile.get("quality_level") if isinstance(chosen_profile, dict) else None
        )
        chosen_radius = (
            chosen_profile.get("requested_radius") if isinstance(chosen_profile, dict) else None
        )
        self._last_trace = {
            "inpainting_backend": "gpu_deep_learning_unet",
            "inpainting_method": "gpu_deep_learning_unet",
            "gpu_inpainting_profile": dict(profile) if isinstance(profile, dict) else None,
            "gpu_inpainting_retry": dict(retry_info) if isinstance(retry_info, dict) else None,
            "gpu_inpainting_oom_retry_used": bool(
                getattr(self.dl_inpainter, "last_oom_retry_used", False)
            ),
            "gpu_inpainting_retry_count": int(
                getattr(self.dl_inpainter, "last_oom_retry_count", 0)
            ),
            "gpu_inpainting_retry_profile": (
                dict(retry_profile) if isinstance(retry_profile, dict) else None
            ),
            "effective_quality_level": (
                int(chosen_quality) if chosen_quality is not None else None
            ),
            "effective_inpaint_radius": (int(chosen_radius) if chosen_radius is not None else None),
            "configured_inpainting_model_path": self.model_path,
            "loaded_inpainting_model_path": self.loaded_model_path,
        }
        return np.asarray(result)

    def cleanup(self) -> None:
        if self.dl_inpainter is not None and hasattr(self.dl_inpainter, "cleanup"):
            self.dl_inpainter.cleanup()
