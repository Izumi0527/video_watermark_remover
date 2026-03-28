#!/usr/bin/env python3
"""
AIHandler 复制优化回归测试。
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.unit.test_dynamic_watermark_tracking import (
    _build_lightweight_ai_handler,
    _load_test_targets,
)


class _TrackingFrame(np.ndarray):
    copy_count = 0

    def copy(self, order="C"):
        type(self).copy_count += 1
        return np.array(self, copy=True, order=order).view(type(self))


class _EmptyMaskDetector:
    def detect_watermark(self, frame):
        return np.zeros(frame.shape[:2], dtype=np.uint8)


def _create_tracking_frame() -> _TrackingFrame:
    frame = np.zeros((48, 64, 3), dtype=np.uint8).view(_TrackingFrame)
    _TrackingFrame.copy_count = 0
    return frame


def test_ai_handler_no_watermark_fast_path_avoids_full_frame_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    handler = _build_lightweight_ai_handler(_EmptyMaskDetector(), ai_handler_cls)

    frame = _create_tracking_frame()
    processed_frame, info = handler.process_frame(
        frame,
        {
            "auto_detect": True,
            "user_mask": None,
        },
    )

    assert _TrackingFrame.copy_count == 0
    assert processed_frame is frame
    assert info["watermark_areas_found"] == 0
