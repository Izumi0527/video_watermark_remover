"""LaMa 修复后端。"""

from __future__ import annotations

import os
from typing import Callable, Optional

import numpy as np

from .base import BaseInpaintingBackend


class LaMaInpaintingBackend(BaseInpaintingBackend):
    """LaMa backend 的最小适配层。"""

    backend_id = "lama"

    def __init__(
        self,
        config=None,
        torch_device=None,
        asset_ref: Optional[str] = None,
        runner: Optional[Callable] = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.torch_device = torch_device
        self.asset_ref = asset_ref
        self.runner = runner
        self.loaded_asset_ref: Optional[str] = None
        self.loaded_model_path: Optional[str] = None
        self.runner_init_failure_reason: Optional[str] = None
        self.runner_init_failure_detail: Optional[str] = None

    def _create_runner(self) -> Optional[Callable]:
        """
        创建真实 LaMa runner。
        """
        try:
            from ..lama_runtime import LaMaRuntimeError, build_lama_runner
        except Exception as exc:  # noqa: BLE001
            self.runner_init_failure_reason = "lama_runtime_import_failed"
            self.runner_init_failure_detail = str(exc)
            return None

        try:
            return build_lama_runner(
                config=self.config,
                torch_device=self.torch_device,
                asset_ref=self.asset_ref,
            )
        except LaMaRuntimeError as exc:
            self.runner_init_failure_reason = exc.code
            self.runner_init_failure_detail = str(exc)
            return None
        except Exception as exc:  # noqa: BLE001
            self.runner_init_failure_reason = "lama_runtime_init_failed"
            self.runner_init_failure_detail = str(exc)
            return None

    def load(self) -> bool:
        if not self.asset_ref:
            self._last_trace = {
                "inpainting_backend": self.backend_id,
                "load_success": False,
                "load_failure_reason": "missing_lama_model_path",
                "load_failure_detail": "未提供 LaMa 模型路径。",
                "configured_inpainting_asset_ref": self.asset_ref,
                "loaded_inpainting_asset_ref": None,
                "configured_inpainting_model_path": self.asset_ref,
                "loaded_inpainting_model_path": None,
            }
            return False

        if not os.path.exists(self.asset_ref):
            self._last_trace = {
                "inpainting_backend": self.backend_id,
                "load_success": False,
                "load_failure_reason": "lama_model_path_not_found",
                "load_failure_detail": f"LaMa 模型路径不存在：{self.asset_ref}",
                "configured_inpainting_asset_ref": self.asset_ref,
                "loaded_inpainting_asset_ref": None,
                "configured_inpainting_model_path": self.asset_ref,
                "loaded_inpainting_model_path": None,
            }
            return False

        self.runner_init_failure_reason = None
        self.runner_init_failure_detail = None
        self.runner = self.runner or self._create_runner()
        if self.runner is None:
            self._last_trace = {
                "inpainting_backend": self.backend_id,
                "load_success": False,
                "load_failure_reason": self.runner_init_failure_reason or "lama_runner_unavailable",
                "load_failure_detail": self.runner_init_failure_detail,
                "configured_inpainting_asset_ref": self.asset_ref,
                "loaded_inpainting_asset_ref": None,
                "configured_inpainting_model_path": self.asset_ref,
                "loaded_inpainting_model_path": None,
            }
            return False

        self.loaded_asset_ref = getattr(self.runner, "asset_ref", self.asset_ref)
        self.loaded_model_path = getattr(
            self.runner,
            "model_path",
            self.loaded_asset_ref,
        )
        self._last_trace = {
            "inpainting_backend": self.backend_id,
            "load_success": True,
            "load_failure_reason": None,
            "load_failure_detail": None,
            "configured_inpainting_asset_ref": self.asset_ref,
            "loaded_inpainting_asset_ref": self.loaded_asset_ref,
            "configured_inpainting_model_path": self.asset_ref,
            "loaded_inpainting_model_path": self.loaded_model_path,
        }
        return True

    def inpaint_frame(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        *,
        inpaint_radius: int,
        quality_level: int,
        opencv_method: str = "auto",
    ) -> np.ndarray:
        if self.runner is None:
            raise RuntimeError("LaMa backend not loaded")

        result = self.runner(
            frame,
            mask,
            inpaint_radius=inpaint_radius,
            quality_level=quality_level,
            device=self.torch_device,
            asset_ref=self.asset_ref,
        )
        resolved = np.asarray(result if result is not None else frame)
        self._last_trace = {
            "inpainting_backend": self.backend_id,
            "inpainting_method": self.backend_id,
            "effective_quality_level": quality_level,
            "effective_inpaint_radius": inpaint_radius,
            "configured_inpainting_asset_ref": self.asset_ref,
            "loaded_inpainting_asset_ref": self.loaded_asset_ref,
            "configured_inpainting_model_path": self.asset_ref,
            "loaded_inpainting_model_path": self.loaded_model_path,
        }
        return resolved
