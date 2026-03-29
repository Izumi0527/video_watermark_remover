"""LaMa 修复后端。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, cast

import cv2
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


@dataclass(frozen=True)
class _PreparedBatchItem:
    """LaMa 批量推理的单项输入。"""

    original_frame: np.ndarray
    raw_mask: np.ndarray
    roi_rect: Optional[_RoiRect]
    prepared_frame: np.ndarray
    prepared_mask: np.ndarray
    target_shape: tuple[int, int]
    runtime_resize_applied: bool


_LAMA_BATCH_BUCKET_STEP = 128
# 默认批量上限：更大的 batch 往往能更好喂满 GPU，但也更容易触发 OOM。
# 这里采用“默认更激进 + 运行期自动拆分回退”的策略：
# - 正常情况下提升吞吐
# - 一旦触发显存压力，自动拆分为更小的批，保证稳定性
_LAMA_BATCH_MAX_GROUP_SIZE = 8


def _is_cuda_oom_error(exc: Exception) -> bool:
    """尽量稳健地判断 CUDA OOM（避免引入 torch 依赖）。"""
    message = str(exc).lower()
    return "out of memory" in message and ("cuda" in message or "cublas" in message)


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


def _resize_inputs_if_needed(
    frame: np.ndarray,
    mask: np.ndarray,
    *,
    resize_limit: Optional[int],
) -> tuple[np.ndarray, np.ndarray, bool]:
    """按运行时预算收缩输入尺寸。"""
    if resize_limit is None:
        return frame, mask, False

    height, width = frame.shape[:2]
    max_dimension = max(height, width)
    if max_dimension <= resize_limit:
        return frame, mask, False

    scale = resize_limit / float(max_dimension)
    resized_width = max(1, int(round(width * scale)))
    resized_height = max(1, int(round(height * scale)))

    resized_frame = cv2.resize(
        frame,
        (resized_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )
    resized_mask = cv2.resize(
        mask,
        (resized_width, resized_height),
        interpolation=cv2.INTER_NEAREST,
    )
    return resized_frame, np.asarray(resized_mask, dtype=np.uint8), True


def _restore_result_size(
    result: np.ndarray,
    *,
    target_shape: tuple[int, int],
) -> np.ndarray:
    """把推理输出恢复到目标尺寸。"""
    target_height, target_width = target_shape
    if result.shape[:2] == (target_height, target_width):
        return result
    restored = cv2.resize(
        result,
        (target_width, target_height),
        interpolation=cv2.INTER_CUBIC,
    )
    return np.asarray(restored, dtype=np.uint8)


def _ceil_to_step(value: int, step: int) -> int:
    if step <= 1:
        return int(value)
    return int(((max(1, int(value)) + step - 1) // step) * step)


def _build_prepared_item_bucket_key(item: _PreparedBatchItem) -> tuple[str, int, int]:
    height, width = item.prepared_frame.shape[:2]
    bucket_mode = "roi" if item.roi_rect is not None else "full"
    return (
        bucket_mode,
        _ceil_to_step(height, _LAMA_BATCH_BUCKET_STEP),
        _ceil_to_step(width, _LAMA_BATCH_BUCKET_STEP),
    )


def _group_prepared_batch_items(
    prepared_items: list[_PreparedBatchItem],
    *,
    max_group_size: int,
) -> list[tuple[tuple[str, int, int], list[int]]]:
    ordered_keys: list[tuple[str, int, int]] = []
    bucket_to_indices: dict[tuple[str, int, int], list[int]] = {}

    for index, item in enumerate(prepared_items):
        bucket_key = _build_prepared_item_bucket_key(item)
        if bucket_key not in bucket_to_indices:
            bucket_to_indices[bucket_key] = []
            ordered_keys.append(bucket_key)
        bucket_to_indices[bucket_key].append(index)

    grouped_items: list[tuple[tuple[str, int, int], list[int]]] = []
    normalized_group_size = max(1, int(max_group_size or 1))
    for bucket_key in ordered_keys:
        indices = bucket_to_indices[bucket_key]
        for start in range(0, len(indices), normalized_group_size):
            grouped_items.append((bucket_key, indices[start : start + normalized_group_size]))

    return grouped_items


def _build_lama_trace(
    *,
    backend: "LaMaInpaintingBackend",
    quality_level: int,
    inpaint_radius: int,
    roi_rect: Optional[_RoiRect],
    memory_budget_mb: Any,
    normalized_resize_limit: Optional[int],
    runtime_resize_applied: bool,
    batch_size: int = 1,
) -> dict[str, Any]:
    trace = {
        "inpainting_backend": backend.backend_id,
        "inpainting_method": backend.backend_id,
        "effective_quality_level": int(quality_level),
        "effective_inpaint_radius": int(inpaint_radius),
        "configured_inpainting_asset_ref": backend.asset_ref,
        "loaded_inpainting_asset_ref": backend.loaded_asset_ref,
        "configured_inpainting_model_path": backend.asset_ref,
        "loaded_inpainting_model_path": backend.loaded_model_path,
        "roi_used": roi_rect is not None,
        "memory_budget_mb": memory_budget_mb,
        "resize_limit": normalized_resize_limit,
        "runtime_resize_applied": runtime_resize_applied,
        "gpu_inpainting_profile": {
            "quality_level": int(quality_level),
            "requested_radius": int(inpaint_radius),
            "memory_budget_mb": memory_budget_mb,
            "resize_limit": normalized_resize_limit,
            "batch_size": int(batch_size),
        },
        "gpu_inpainting_retry": None,
        "gpu_inpainting_oom_retry_used": False,
        "gpu_inpainting_retry_count": 0,
        "gpu_inpainting_retry_profile": None,
    }
    if roi_rect is not None:
        trace["roi_rect"] = roi_rect.to_xywh()
        trace["roi_area_ratio"] = float(roi_rect.area_ratio)
        trace["roi_padding"] = int(roi_rect.padding)
    return trace


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
        runtime_profile = self.get_runtime_profile()
        resize_limit = runtime_profile.get("resize_limit")
        memory_budget_mb = runtime_profile.get("memory_budget_mb")
        normalized_resize_limit = max(64, int(resize_limit)) if resize_limit is not None else None
        runtime_resize_applied = False

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
                resized_frame, resized_mask, runtime_resize_applied = _resize_inputs_if_needed(
                    cropped_frame,
                    cropped_mask,
                    resize_limit=normalized_resize_limit,
                )

                cropped_result = self.runner(
                    resized_frame,
                    resized_mask,
                    inpaint_radius=inpaint_radius,
                    quality_level=quality_level,
                    device=self.torch_device,
                    asset_ref=self.asset_ref,
                    memory_budget_mb=memory_budget_mb,
                    resize_limit=normalized_resize_limit,
                )
                resolved_crop = _restore_result_size(
                    np.asarray(cropped_result if cropped_result is not None else resized_frame),
                    target_shape=cropped_frame.shape[:2],
                )

                # 仅将 mask 区域（轻微膨胀）写回，避免无关区域抖动导致视频闪烁。
                mask_bool = _dilate_mask_if_needed(cropped_mask > 0, inpaint_radius=inpaint_radius)
                output = frame.copy()
                output_roi = output[roi_rect.y1 : roi_rect.y2, roi_rect.x1 : roi_rect.x2]
                output_roi[mask_bool] = resolved_crop[mask_bool]
                output[roi_rect.y1 : roi_rect.y2, roi_rect.x1 : roi_rect.x2] = output_roi

                self._last_trace = _build_lama_trace(
                    backend=self,
                    quality_level=quality_level,
                    inpaint_radius=inpaint_radius,
                    roi_rect=roi_rect,
                    memory_budget_mb=memory_budget_mb,
                    normalized_resize_limit=normalized_resize_limit,
                    runtime_resize_applied=runtime_resize_applied,
                )

                return output
            except Exception:
                # ROI 优化不能影响稳定性：任何 ROI 拼接异常都回退到整帧推理。
                roi_rect = None
                runtime_resize_applied = False

        resized_frame, resized_mask, runtime_resize_applied = _resize_inputs_if_needed(
            frame,
            raw_mask,
            resize_limit=normalized_resize_limit,
        )

        result = self.runner(
            resized_frame,
            resized_mask,
            inpaint_radius=inpaint_radius,
            quality_level=quality_level,
            device=self.torch_device,
            asset_ref=self.asset_ref,
            memory_budget_mb=memory_budget_mb,
            resize_limit=normalized_resize_limit,
        )
        resolved = _restore_result_size(
            np.asarray(result if result is not None else resized_frame),
            target_shape=frame.shape[:2],
        )
        self._last_trace = _build_lama_trace(
            backend=self,
            quality_level=quality_level,
            inpaint_radius=inpaint_radius,
            roi_rect=None,
            memory_budget_mb=memory_budget_mb,
            normalized_resize_limit=normalized_resize_limit,
            runtime_resize_applied=runtime_resize_applied,
        )
        return resolved

    def batch_inpaint_frames(  # noqa: C901
        self,
        frames: list[np.ndarray],
        masks: list[np.ndarray],
        *,
        inpaint_radius: int,
        quality_level: int,
        opencv_method: str = "auto",
    ) -> list[dict[str, Any]]:
        """对同一批帧执行 LaMa 批量推理，降低逐帧调用开销。"""
        if self.runner is None:
            raise RuntimeError("LaMa backend not loaded")

        runner = self.runner
        del opencv_method
        if not frames or not masks or len(frames) != len(masks):
            raise RuntimeError("LaMa batch inpainting requires aligned frame/mask inputs")

        runtime_profile = self.get_runtime_profile()
        resize_limit = runtime_profile.get("resize_limit")
        memory_budget_mb = runtime_profile.get("memory_budget_mb")
        normalized_resize_limit = max(64, int(resize_limit)) if resize_limit is not None else None

        prepared_items: list[_PreparedBatchItem] = []
        for frame, mask in zip(frames, masks):
            raw_mask = _normalize_mask(mask)
            roi_rect = _compute_roi_rect(
                frame,
                raw_mask,
                inpaint_radius=inpaint_radius,
                quality_level=quality_level,
            )
            if roi_rect is not None:
                cropped_frame = frame[roi_rect.y1 : roi_rect.y2, roi_rect.x1 : roi_rect.x2]
                cropped_mask = raw_mask[roi_rect.y1 : roi_rect.y2, roi_rect.x1 : roi_rect.x2]
                resized_frame, resized_mask, runtime_resize_applied = _resize_inputs_if_needed(
                    cropped_frame,
                    cropped_mask,
                    resize_limit=normalized_resize_limit,
                )
                prepared_items.append(
                    _PreparedBatchItem(
                        original_frame=frame,
                        raw_mask=raw_mask,
                        roi_rect=roi_rect,
                        prepared_frame=resized_frame,
                        prepared_mask=resized_mask,
                        target_shape=cropped_frame.shape[:2],
                        runtime_resize_applied=runtime_resize_applied,
                    )
                )
                continue

            resized_frame, resized_mask, runtime_resize_applied = _resize_inputs_if_needed(
                frame,
                raw_mask,
                resize_limit=normalized_resize_limit,
            )
            prepared_items.append(
                _PreparedBatchItem(
                    original_frame=frame,
                    raw_mask=raw_mask,
                    roi_rect=None,
                    prepared_frame=resized_frame,
                    prepared_mask=resized_mask,
                    target_shape=frame.shape[:2],
                    runtime_resize_applied=runtime_resize_applied,
                )
            )

        runner_batch = getattr(runner, "run_batch", None)
        max_group_size = runtime_profile.get("lama_batch_max_group_size")
        if max_group_size is None:
            max_group_size = runtime_profile.get("batch_max_group_size")
        try:
            max_group_size = int(max_group_size or _LAMA_BATCH_MAX_GROUP_SIZE)
        except (TypeError, ValueError):
            max_group_size = _LAMA_BATCH_MAX_GROUP_SIZE
        max_group_size = max(1, min(32, int(max_group_size)))

        grouped_items = _group_prepared_batch_items(prepared_items, max_group_size=max_group_size)
        grouped_results: dict[int, dict[str, Any]] = {}
        batch_group_sizes: list[int] = []
        batch_group_buckets: list[dict[str, Any]] = []
        executed_group_count = 0

        def _execute_group_indices(
            bucket_key: tuple[str, int, int],
            item_indices: list[int],
        ) -> list[tuple[list[int], list[Any]]]:
            """执行一组索引；若 batch 触发 OOM 则递归拆分。"""
            group_items = [prepared_items[index] for index in item_indices]
            if not group_items:
                return []

            if not callable(runner_batch):
                outputs = [
                    runner(
                        item.prepared_frame,
                        item.prepared_mask,
                        inpaint_radius=inpaint_radius,
                        quality_level=quality_level,
                        device=self.torch_device,
                        asset_ref=self.asset_ref,
                        memory_budget_mb=memory_budget_mb,
                        resize_limit=normalized_resize_limit,
                    )
                    for item in group_items
                ]
                return [(item_indices, outputs)]

            try:
                outputs = runner_batch(
                    [item.prepared_frame for item in group_items],
                    [item.prepared_mask for item in group_items],
                    inpaint_radius=inpaint_radius,
                    quality_level=quality_level,
                    device=self.torch_device,
                    asset_ref=self.asset_ref,
                    memory_budget_mb=memory_budget_mb,
                    resize_limit=normalized_resize_limit,
                )
                return [(item_indices, outputs)]
            except Exception as exc:  # noqa: BLE001
                if _is_cuda_oom_error(exc) and len(item_indices) > 1:
                    mid = max(1, len(item_indices) // 2)
                    left = _execute_group_indices(bucket_key, item_indices[:mid])
                    right = _execute_group_indices(bucket_key, item_indices[mid:])
                    return [*left, *right]

                # 非 OOM 或已经拆到单帧：回退到逐帧调用，避免整批直接失败。
                outputs = [
                    runner(
                        item.prepared_frame,
                        item.prepared_mask,
                        inpaint_radius=inpaint_radius,
                        quality_level=quality_level,
                        device=self.torch_device,
                        asset_ref=self.asset_ref,
                        memory_budget_mb=memory_budget_mb,
                        resize_limit=normalized_resize_limit,
                    )
                    for item in group_items
                ]
                return [(item_indices, outputs)]

        for bucket_key, item_indices in grouped_items:
            executed_groups = _execute_group_indices(bucket_key, list(item_indices))
            for executed_indices, batch_outputs in executed_groups:
                group_items = [prepared_items[index] for index in executed_indices]
                group_size = len(group_items)
                executed_group_count += 1
                batch_group_sizes.append(group_size)
                batch_group_buckets.append(
                    {
                        "mode": bucket_key[0],
                        "height": bucket_key[1],
                        "width": bucket_key[2],
                        "size": group_size,
                    }
                )

                if len(batch_outputs) != group_size:
                    raise RuntimeError(
                        "LaMa batch output count mismatch: "
                        f"expected={group_size} actual={len(batch_outputs)}"
                    )

                for item_index, item, raw_output in zip(
                    executed_indices, group_items, batch_outputs
                ):
                    resolved = _restore_result_size(
                        np.asarray(raw_output if raw_output is not None else item.prepared_frame),
                        target_shape=item.target_shape,
                    )
                    if item.roi_rect is not None:
                        mask_roi = item.raw_mask[
                            item.roi_rect.y1 : item.roi_rect.y2,
                            item.roi_rect.x1 : item.roi_rect.x2,
                        ]
                        mask_bool = _dilate_mask_if_needed(
                            mask_roi > 0, inpaint_radius=inpaint_radius
                        )
                        output = item.original_frame.copy()
                        output_roi = output[
                            item.roi_rect.y1 : item.roi_rect.y2,
                            item.roi_rect.x1 : item.roi_rect.x2,
                        ]
                        output_roi[mask_bool] = resolved[mask_bool]
                        output[
                            item.roi_rect.y1 : item.roi_rect.y2,
                            item.roi_rect.x1 : item.roi_rect.x2,
                        ] = output_roi
                    else:
                        output = resolved

                    trace = _build_lama_trace(
                        backend=self,
                        quality_level=quality_level,
                        inpaint_radius=inpaint_radius,
                        roi_rect=item.roi_rect,
                        memory_budget_mb=memory_budget_mb,
                        normalized_resize_limit=normalized_resize_limit,
                        runtime_resize_applied=item.runtime_resize_applied,
                        batch_size=group_size,
                    )
                    trace["batch_group_index"] = executed_group_count
                    trace["batch_group_count"] = 0
                    trace["batch_total_candidates"] = len(prepared_items)
                    trace["batch_bucket"] = {
                        "mode": bucket_key[0],
                        "height": bucket_key[1],
                        "width": bucket_key[2],
                    }
                    profile = trace.get("gpu_inpainting_profile")
                    if isinstance(profile, dict):
                        profile["batch_group_index"] = executed_group_count
                        profile["batch_group_count"] = 0
                        profile["batch_total_candidates"] = len(prepared_items)
                        profile["batch_bucket_mode"] = bucket_key[0]
                        profile["batch_bucket_height"] = bucket_key[1]
                        profile["batch_bucket_width"] = bucket_key[2]

                    grouped_results[item_index] = {"frame": output, "trace": trace}

        results = [grouped_results[index] for index in range(len(prepared_items))]

        if results:
            group_count = len(batch_group_sizes)
            for result in results:
                trace_snapshot = result.get("trace")
                if not isinstance(trace_snapshot, dict):
                    continue
                trace_snapshot["batch_group_count"] = group_count
                profile = trace_snapshot.get("gpu_inpainting_profile")
                if isinstance(profile, dict):
                    profile["batch_group_count"] = group_count

            last_trace_snapshot = results[-1].get("trace")
            aggregate_trace: dict[str, Any] = (
                dict(last_trace_snapshot) if isinstance(last_trace_snapshot, dict) else {}
            )
            aggregate_trace["batch_group_count"] = group_count
            aggregate_trace["batch_group_sizes"] = list(batch_group_sizes)
            aggregate_trace["batch_total_candidates"] = len(prepared_items)
            aggregate_trace["batch_group_buckets"] = list(batch_group_buckets)
            self._last_trace = aggregate_trace
        return results
