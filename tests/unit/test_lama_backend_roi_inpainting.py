#!/usr/bin/env python3
"""
LaMa backend ROI 裁剪修复回归测试。

目标：
- 当水印区域明显小于整帧时，LaMa backend 应启用 ROI 裁剪以提升吞吐；
- 写回结果时只覆盖 mask 区域，避免无关区域抖动造成视频闪烁；
- 当修复区域过大时，应回退到整帧推理，避免缺失全局上下文导致质量下降。
"""

from __future__ import annotations

import numpy as np


def test_lama_backend_uses_roi_when_mask_area_is_small() -> None:
    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    # 给背景做一些非零值，便于断言“未被修改”
    frame[:, :, 1] = 10

    mask = np.zeros((240, 320), dtype=np.uint8)
    mask[8:16, 12:20] = 255

    captured: dict[str, object] = {}

    def fake_runner(input_frame: np.ndarray, input_mask: np.ndarray, **_kwargs):
        captured["frame_shape"] = tuple(input_frame.shape)
        captured["mask_shape"] = tuple(np.asarray(input_mask).shape)
        # 返回全白图，后续应只写回 mask 区域
        return np.ones_like(input_frame, dtype=np.uint8) * 255

    backend = LaMaInpaintingBackend(asset_ref="stub", runner=fake_runner)
    output = backend.inpaint_frame(
        frame,
        mask,
        inpaint_radius=0,
        quality_level=3,
    )

    assert captured["frame_shape"] != tuple(frame.shape)
    assert captured["mask_shape"] == captured["frame_shape"][:2]
    assert backend.get_last_trace().get("roi_used") is True

    # mask 区域被修复（变白）
    assert int(output[10, 15, 0]) == 255
    assert int(output[10, 15, 1]) == 255
    assert int(output[10, 15, 2]) == 255

    # 非 mask 区域保持原始值
    assert int(output[0, 0, 0]) == 0
    assert int(output[0, 0, 1]) == 10
    assert int(output[0, 0, 2]) == 0


def test_lama_backend_falls_back_to_full_frame_when_mask_is_large() -> None:
    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    mask = np.ones((240, 320), dtype=np.uint8) * 255

    captured: dict[str, object] = {}

    def fake_runner(input_frame: np.ndarray, input_mask: np.ndarray, **_kwargs):
        captured["frame_shape"] = tuple(input_frame.shape)
        captured["mask_shape"] = tuple(np.asarray(input_mask).shape)
        return input_frame

    backend = LaMaInpaintingBackend(asset_ref="stub", runner=fake_runner)
    output = backend.inpaint_frame(
        frame,
        mask,
        inpaint_radius=0,
        quality_level=3,
    )

    assert captured["frame_shape"] == tuple(frame.shape)
    assert captured["mask_shape"] == tuple(mask.shape)
    assert backend.get_last_trace().get("roi_used") is False
    assert output.shape == frame.shape
