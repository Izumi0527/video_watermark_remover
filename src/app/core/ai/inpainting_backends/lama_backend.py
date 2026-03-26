"""LaMa 修复后端。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, cast

import numpy as np

from .base import BaseInpaintingBackend


@dataclass(frozen=True)
class _RoiRect:
    """用于 ROI 修复的矩形区域。"""

    x1: int
    y1: int
    x2: int
    y2: int
    padding: int
    area_ratio: float

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    def to_xywh(self) -> list[int]:
        return [int(self.x1), int(self.y1), int(self.width), int(self.height)]


def _normalize_mask(mask: np.ndarray) -> np.ndarray:
    raw = np.asarray(mask)
    if raw.ndim == 3:
        raw = raw[..., 0]
    return raw


def _compute_roi_padding(inpaint_radius: int, quality_level: int) -> int:
    # padding 主要用于给模型提供上下文，过小容易出现边界伪影。
    # 这里采用“质量越高，上下文越大”的启发式，避免让用户默认参数过慢。
    quality = int(quality_level) if isinstance(quality_level, int) else 3
    quality = max(1, min(5, quality))
    base_by_quality = {
        1: 24,
        2: 32,
        3: 48,
        4: 64,
        5: 80,
    }[quality]
    radius_pad = max(0, int(inpaint_radius)) * 2
    return int(base_by_quality + radius_pad)


def _expand_to_min_size(
    *,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    min_size: int,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    roi_w = max(0, x2 - x1)
    roi_h = max(0, y2 - y1)

    if roi_w < min_size:
        delta = min_size - roi_w
        left = delta // 2
        right = delta - left
        x1 = max(0, x1 - left)
        x2 = min(width, x2 + right)
        # 二次修正：若触边导致仍不足，则从另一侧补齐
        roi_w = max(0, x2 - x1)
        if roi_w < min_size:
            if x1 == 0:
                x2 = min(width, x1 + min_size)
            elif x2 == width:
                x1 = max(0, x2 - min_size)

    if roi_h < min_size:
        delta = min_size - roi_h
        top = delta // 2
        bottom = delta - top
        y1 = max(0, y1 - top)
        y2 = min(height, y2 + bottom)
        roi_h = max(0, y2 - y1)
        if roi_h < min_size:
            if y1 == 0:
                y2 = min(height, y1 + min_size)
            elif y2 == height:
                y1 = max(0, y2 - min_size)

    return int(x1), int(y1), int(x2), int(y2)


def _compute_roi_rect(
    frame: np.ndarray,
    mask: np.ndarray,
    *,
    inpaint_radius: int,
    quality_level: int,
) -> Optional[_RoiRect]:
    """基于 mask 的非零区域计算 ROI（含 padding），用于减少 LaMa 的整帧推理成本。"""
    height, width = frame.shape[:2]
    if height <= 0 or width <= 0:
        return None

    raw_mask = _normalize_mask(mask)
    if raw_mask.ndim != 2:
        return None

    ys, xs = np.nonzero(raw_mask > 0)
    if xs.size == 0 or ys.size == 0:
        return None

    pad = _compute_roi_padding(inpaint_radius, quality_level)
    x1 = int(max(0, int(xs.min()) - pad))
    x2 = int(min(width, int(xs.max()) + 1 + pad))
    y1 = int(max(0, int(ys.min()) - pad))
    y2 = int(min(height, int(ys.max()) + 1 + pad))

    # 过小的 ROI 容易出现边缘伪影，做一次最小尺寸保障
    x1, y1, x2, y2 = _expand_to_min_size(
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        min_size=128,
        width=width,
        height=height,
    )

    roi_w = max(0, x2 - x1)
    roi_h = max(0, y2 - y1)
    if roi_w <= 0 or roi_h <= 0:
        return None

    area_ratio = float((roi_w * roi_h) / float(height * width))

    # 仅在 ROI 明显小于整帧时启用裁剪，避免大面积修复时因缺少全局上下文导致质量下降。
    if area_ratio >= 0.60:
        return None

    return _RoiRect(
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        padding=int(pad),
        area_ratio=area_ratio,
    )


def _dilate_mask_if_needed(mask_bool: np.ndarray, *, inpaint_radius: int) -> np.ndarray:
    """对掩码做轻微膨胀，减少拼接边界硬切带来的伪影。"""
    if inpaint_radius <= 0:
        return mask_bool
    try:
        import cv2  # 延迟导入，避免在无 OpenCV 环境下影响模块加载

        dilation = max(1, int(round(inpaint_radius)))
        kernel_size = max(3, 1 + 2 * dilation)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated = cv2.dilate(mask_bool.astype(np.uint8) * 255, kernel, iterations=1) > 0
        return dilated
    except Exception:
        return mask_bool


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

    def _create_runner(self) -> Optional[Callable[..., Any]]:
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
            runner = build_lama_runner(
                config=self.config,
                torch_device=self.torch_device,
                asset_ref=self.asset_ref,
            )
            return cast(Callable[..., Any], runner)
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

        del opencv_method

        raw_mask = _normalize_mask(mask)
        roi_rect = _compute_roi_rect(
            frame,
            raw_mask,
            inpaint_radius=inpaint_radius,
            quality_level=quality_level,
        )

        if roi_rect is not None:
            try:
                cropped_frame = frame[roi_rect.y1 : roi_rect.y2, roi_rect.x1 : roi_rect.x2]
                cropped_mask = raw_mask[roi_rect.y1 : roi_rect.y2, roi_rect.x1 : roi_rect.x2]

                cropped_result = self.runner(
                    cropped_frame,
                    cropped_mask,
                    inpaint_radius=inpaint_radius,
                    quality_level=quality_level,
                    device=self.torch_device,
                    asset_ref=self.asset_ref,
                )
                resolved_crop = np.asarray(
                    cropped_result if cropped_result is not None else cropped_frame
                )

                # 仅将 mask 区域（轻微膨胀）写回，避免无关区域抖动导致视频闪烁。
                mask_bool = _dilate_mask_if_needed(cropped_mask > 0, inpaint_radius=inpaint_radius)
                output = frame.copy()
                output_roi = output[roi_rect.y1 : roi_rect.y2, roi_rect.x1 : roi_rect.x2]
                output_roi[mask_bool] = resolved_crop[mask_bool]
                output[roi_rect.y1 : roi_rect.y2, roi_rect.x1 : roi_rect.x2] = output_roi

                self._last_trace = {
                    "inpainting_backend": self.backend_id,
                    "inpainting_method": self.backend_id,
                    "effective_quality_level": int(quality_level),
                    "effective_inpaint_radius": int(inpaint_radius),
                    "configured_inpainting_asset_ref": self.asset_ref,
                    "loaded_inpainting_asset_ref": self.loaded_asset_ref,
                    "configured_inpainting_model_path": self.asset_ref,
                    "loaded_inpainting_model_path": self.loaded_model_path,
                    "roi_used": True,
                    "roi_rect": roi_rect.to_xywh(),
                    "roi_area_ratio": float(roi_rect.area_ratio),
                    "roi_padding": int(roi_rect.padding),
                }

                return output
            except Exception:
                # ROI 优化不能影响稳定性：任何 ROI 拼接异常都回退到整帧推理。
                roi_rect = None

        result = self.runner(
            frame,
            raw_mask,
            inpaint_radius=inpaint_radius,
            quality_level=quality_level,
            device=self.torch_device,
            asset_ref=self.asset_ref,
        )
        resolved = np.asarray(result if result is not None else frame)
        self._last_trace = {
            "inpainting_backend": self.backend_id,
            "inpainting_method": self.backend_id,
            "effective_quality_level": int(quality_level),
            "effective_inpaint_radius": int(inpaint_radius),
            "configured_inpainting_asset_ref": self.asset_ref,
            "loaded_inpainting_asset_ref": self.loaded_asset_ref,
            "configured_inpainting_model_path": self.asset_ref,
            "loaded_inpainting_model_path": self.loaded_model_path,
            "roi_used": False,
        }
        return resolved
