#!/usr/bin/env python3
"""
LaMa backend 运行时预算生效测试。
"""

from __future__ import annotations

import numpy as np


def test_lama_backend_applies_runtime_budget_to_resize_limit() -> None:
    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    frame = np.zeros((1200, 1600, 3), dtype=np.uint8)
    mask = np.ones((1200, 1600), dtype=np.uint8) * 255
    captured: dict[str, object] = {}

    def fake_runner(input_frame: np.ndarray, input_mask: np.ndarray, **kwargs):
        captured["frame_shape"] = tuple(input_frame.shape)
        captured["mask_shape"] = tuple(np.asarray(input_mask).shape)
        captured["memory_budget_mb"] = kwargs.get("memory_budget_mb")
        captured["resize_limit"] = kwargs.get("resize_limit")
        return np.ones_like(input_frame, dtype=np.uint8) * 127

    backend = LaMaInpaintingBackend(asset_ref="stub", runner=fake_runner)
    backend.set_runtime_profile({"memory_budget_mb": 1024, "resize_limit": 640})

    output = backend.inpaint_frame(
        frame,
        mask,
        inpaint_radius=3,
        quality_level=3,
    )

    assert captured["frame_shape"][0] <= 640
    assert captured["frame_shape"][1] <= 640
    assert captured["mask_shape"] == captured["frame_shape"][:2]
    assert captured["memory_budget_mb"] == 1024
    assert captured["resize_limit"] == 640
    assert output.shape == frame.shape

    trace = backend.get_last_trace()
    assert trace["memory_budget_mb"] == 1024
    assert trace["resize_limit"] == 640
    assert trace["runtime_resize_applied"] is True
