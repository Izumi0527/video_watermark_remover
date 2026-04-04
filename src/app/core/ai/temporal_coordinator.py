#!/usr/bin/env python3
"""
视频掩码时序协调器。

封装关键帧检测与非关键帧掩码复用逻辑，避免时序状态散落在 AIHandler 中。
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from numpy.typing import NDArray


class TemporalCoordinator:
    """管理视频掩码在关键帧之间的复用、短时丢检和大位移重检。"""

    def __init__(
        self,
        *,
        enabled: bool = True,
        keyframe_interval: int = 3,
        warmup_frames: int = 0,
        max_missing_detections: int = 1,
        max_missed_detections: Optional[int] = None,
        motion_redetect_iou_threshold: float = 0.5,
        scene_change_iou_threshold: Optional[float] = None,
        scene_shift_iou_threshold: Optional[float] = None,
        scene_shift_confirmation_frames: int = 1,
    ) -> None:
        self.enabled = bool(enabled)
        self.keyframe_interval = max(1, int(keyframe_interval or 1))
        self.warmup_frames = max(0, int(warmup_frames or 0))
        self.max_missing_detections = self._resolve_max_missing_detections(
            max_missing_detections=max_missing_detections,
            max_missed_detections=max_missed_detections,
        )
        self.motion_redetect_iou_threshold = self._resolve_motion_iou_threshold(
            motion_redetect_iou_threshold=motion_redetect_iou_threshold,
            scene_change_iou_threshold=scene_change_iou_threshold,
            scene_shift_iou_threshold=scene_shift_iou_threshold,
        )
        self.scene_shift_confirmation_frames = max(0, int(scene_shift_confirmation_frames or 0))
        self._last_mask: Optional[NDArray[np.uint8]] = None
        self._stable_hits = 0
        self._missing_detection_hits = 0
        self._force_detect_remaining = 0

    @staticmethod
    def _resolve_max_missing_detections(
        *,
        max_missing_detections: int,
        max_missed_detections: Optional[int],
    ) -> int:
        raw_value = (
            max_missed_detections if max_missed_detections is not None else max_missing_detections
        )
        return max(0, int(raw_value or 0))

    @staticmethod
    def _resolve_motion_iou_threshold(
        *,
        motion_redetect_iou_threshold: float,
        scene_change_iou_threshold: Optional[float],
        scene_shift_iou_threshold: Optional[float],
    ) -> float:
        raw_value = motion_redetect_iou_threshold
        if scene_change_iou_threshold is not None:
            raw_value = scene_change_iou_threshold
        if scene_shift_iou_threshold is not None:
            raw_value = scene_shift_iou_threshold
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            value = 0.5
        return min(0.999, max(0.0, value))

    @property
    def stable_hits(self) -> int:
        return int(self._stable_hits or 0)

    def configure(
        self,
        *,
        enabled: bool,
        keyframe_interval: int,
        warmup_frames: int,
        max_missing_detections: Optional[int] = None,
        max_missed_detections: Optional[int] = None,
        motion_redetect_iou_threshold: Optional[float] = None,
        scene_change_iou_threshold: Optional[float] = None,
        scene_shift_iou_threshold: Optional[float] = None,
        scene_shift_confirmation_frames: Optional[int] = None,
    ) -> None:
        normalized_enabled = bool(enabled)
        normalized_interval = max(1, int(keyframe_interval or 1))
        normalized_warmup = max(0, int(warmup_frames or 0))
        normalized_missing = self.max_missing_detections
        if max_missing_detections is not None or max_missed_detections is not None:
            normalized_missing = self._resolve_max_missing_detections(
                max_missing_detections=(
                    self.max_missing_detections
                    if max_missing_detections is None
                    else max_missing_detections
                ),
                max_missed_detections=max_missed_detections,
            )
        normalized_iou_threshold = self.motion_redetect_iou_threshold
        if (
            motion_redetect_iou_threshold is not None
            or scene_change_iou_threshold is not None
            or scene_shift_iou_threshold is not None
        ):
            normalized_iou_threshold = self._resolve_motion_iou_threshold(
                motion_redetect_iou_threshold=(
                    self.motion_redetect_iou_threshold
                    if motion_redetect_iou_threshold is None
                    else motion_redetect_iou_threshold
                ),
                scene_change_iou_threshold=scene_change_iou_threshold,
                scene_shift_iou_threshold=scene_shift_iou_threshold,
            )
        normalized_confirmation_frames = self.scene_shift_confirmation_frames
        if scene_shift_confirmation_frames is not None:
            normalized_confirmation_frames = max(0, int(scene_shift_confirmation_frames or 0))

        changed = (
            normalized_enabled != self.enabled
            or normalized_interval != self.keyframe_interval
            or normalized_warmup != self.warmup_frames
            or normalized_missing != self.max_missing_detections
            or normalized_iou_threshold != self.motion_redetect_iou_threshold
            or normalized_confirmation_frames != self.scene_shift_confirmation_frames
        )
        self.enabled = normalized_enabled
        self.keyframe_interval = normalized_interval
        self.warmup_frames = normalized_warmup
        self.max_missing_detections = normalized_missing
        self.motion_redetect_iou_threshold = normalized_iou_threshold
        self.scene_shift_confirmation_frames = normalized_confirmation_frames

        if changed:
            self.reset()

    def reset(self) -> None:
        self._last_mask = None
        self._stable_hits = 0
        self._missing_detection_hits = 0
        self._force_detect_remaining = 0

    def is_ready(self) -> bool:
        if not self.enabled:
            return False
        if self._last_mask is None or not np.any(self._last_mask):
            return False
        return self.stable_hits >= self.warmup_frames

    def should_detect(self, frame_index: int) -> bool:
        if not self.enabled:
            return True
        if self._force_detect_remaining > 0:
            return True
        if not self.is_ready():
            return True
        return int(frame_index) % self.keyframe_interval == 0

    def get_stored_mask_copy(self) -> Optional[NDArray[np.uint8]]:
        if self._last_mask is None or not np.any(self._last_mask):
            return None
        return np.asarray(self._last_mask).copy()

    def get_reusable_mask(self) -> Optional[NDArray[np.uint8]]:
        if not self.enabled or not self.is_ready():
            return None
        return self.get_stored_mask_copy()

    def get_tracked_mask_copy(self) -> Optional[NDArray[np.uint8]]:
        """兼容旧调用方命名。"""
        return self.get_reusable_mask()

    @staticmethod
    def _compute_mask_iou(
        mask_a: Optional[NDArray[np.uint8]],
        mask_b: Optional[NDArray[np.uint8]],
    ) -> float:
        if mask_a is None or mask_b is None:
            return 0.0
        binary_a = np.asarray(mask_a) > 0
        binary_b = np.asarray(mask_b) > 0
        if not np.any(binary_a) or not np.any(binary_b):
            return 0.0
        intersection = int(np.logical_and(binary_a, binary_b).sum())
        union = int(np.logical_or(binary_a, binary_b).sum())
        if union <= 0:
            return 0.0
        return float(intersection / union)

    def _should_force_redetect_after_shift(
        self,
        detected_mask: NDArray[np.uint8],
    ) -> bool:
        previous_mask = self.get_stored_mask_copy()
        if previous_mask is None or not np.any(previous_mask):
            return False
        iou = self._compute_mask_iou(previous_mask, detected_mask)
        return iou < self.motion_redetect_iou_threshold

    def _record_non_empty_detection(
        self,
        detected_mask: NDArray[np.uint8],
    ) -> Optional[NDArray[np.uint8]]:
        detected = np.asarray(detected_mask, dtype=np.uint8).copy()
        shift_detected = self._should_force_redetect_after_shift(detected)
        self._last_mask = detected
        self._stable_hits = 1 if shift_detected else (self.stable_hits + 1)
        self._missing_detection_hits = 0
        self._force_detect_remaining = self.scene_shift_confirmation_frames if shift_detected else 0
        return self.get_stored_mask_copy()

    def _record_empty_detection(self) -> Optional[NDArray[np.uint8]]:
        reusable_mask = self.get_stored_mask_copy()
        if reusable_mask is None or self.max_missing_detections <= 0:
            self.reset()
            return None

        if self._missing_detection_hits < self.max_missing_detections:
            self._missing_detection_hits += 1
            self._force_detect_remaining = max(self._force_detect_remaining, 1)
            return reusable_mask

        self.reset()
        return None

    def record_detection(
        self,
        detected_mask: Optional[NDArray[np.uint8]],
    ) -> Optional[NDArray[np.uint8]]:
        if not self.enabled:
            if detected_mask is None or not np.any(detected_mask):
                return None
            return np.asarray(detected_mask, dtype=np.uint8).copy()

        if detected_mask is None or not np.any(detected_mask):
            return self._record_empty_detection()

        return self._record_non_empty_detection(np.asarray(detected_mask, dtype=np.uint8))

    def update(
        self,
        *,
        frame_index: int,
        detected_mask: Optional[NDArray[np.uint8]],
    ) -> Optional[NDArray[np.uint8]]:
        if detected_mask is not None:
            return self.record_detection(detected_mask)

        if self.should_detect(frame_index):
            return None
        return self.get_reusable_mask()
