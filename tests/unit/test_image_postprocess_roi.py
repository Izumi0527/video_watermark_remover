#!/usr/bin/env python3
"""
图像后处理 ROI 收敛回归测试。
"""

from __future__ import annotations

import numpy as np


def test_apply_postprocessing_limits_small_mask_work_to_roi(monkeypatch) -> None:
    from app.core.ai import image_processor

    original = np.zeros((120, 160, 3), dtype=np.uint8)
    processed = np.zeros((120, 160, 3), dtype=np.uint8)
    mask = np.zeros((120, 160), dtype=np.uint8)
    mask[20:28, 30:38] = 255

    captured: list[tuple[str, tuple[int, ...], tuple[int, ...], tuple[int, ...]]] = []

    def fake_smooth(original_frame, processed_frame, roi_mask, **_kwargs):
        captured.append(
            (
                "smooth",
                tuple(original_frame.shape),
                tuple(processed_frame.shape),
                tuple(roi_mask.shape),
            )
        )
        return processed_frame

    def fake_blend(original_frame, processed_frame, roi_mask, **_kwargs):
        captured.append(
            (
                "blend",
                tuple(original_frame.shape),
                tuple(processed_frame.shape),
                tuple(roi_mask.shape),
            )
        )
        return processed_frame

    def fake_enhance(frame, roi_mask=None, **_kwargs):
        mask_shape = tuple(roi_mask.shape) if roi_mask is not None else tuple()
        captured.append(("enhance", tuple(frame.shape), tuple(frame.shape), mask_shape))
        return frame

    monkeypatch.setattr(image_processor, "postprocess_smooth_edges", fake_smooth)
    monkeypatch.setattr(image_processor, "postprocess_blend", fake_blend)
    monkeypatch.setattr(image_processor, "postprocess_enhance", fake_enhance)

    result = image_processor.apply_postprocessing(
        original,
        processed,
        mask,
        enable_smooth=True,
        enable_blend=True,
        enable_enhance=True,
    )

    assert result.shape == original.shape
    assert captured
    assert all(item[1][0] < original.shape[0] for item in captured)
    assert all(item[1][1] < original.shape[1] for item in captured)


def test_apply_postprocessing_keeps_full_frame_path_for_large_mask(monkeypatch) -> None:
    from app.core.ai import image_processor

    original = np.zeros((80, 100, 3), dtype=np.uint8)
    processed = np.zeros((80, 100, 3), dtype=np.uint8)
    mask = np.ones((80, 100), dtype=np.uint8) * 255

    captured: list[tuple[str, tuple[int, ...]]] = []

    def fake_smooth(original_frame, processed_frame, roi_mask, **_kwargs):
        captured.append(("smooth", tuple(original_frame.shape)))
        return processed_frame

    monkeypatch.setattr(image_processor, "postprocess_smooth_edges", fake_smooth)

    result = image_processor.apply_postprocessing(
        original,
        processed,
        mask,
        enable_smooth=True,
    )

    assert result.shape == original.shape
    assert captured == [("smooth", original.shape)]
