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


def test_lama_backend_batch_inpaint_frames_uses_runner_batch_api() -> None:
    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    frame_a = np.zeros((240, 320, 3), dtype=np.uint8)
    frame_b = np.zeros((240, 320, 3), dtype=np.uint8)
    mask = np.zeros((240, 320), dtype=np.uint8)
    mask[8:16, 12:20] = 255

    captured: dict[str, object] = {"batch_calls": 0}

    class _Runner:
        def run_batch(self, input_frames, input_masks, **kwargs):
            captured["batch_calls"] = int(captured.get("batch_calls", 0)) + 1
            captured["frames_len"] = len(input_frames)
            captured["masks_len"] = len(input_masks)
            captured["quality_level"] = kwargs.get("quality_level")
            outputs = []
            for index, frame in enumerate(input_frames):
                output = np.zeros_like(frame, dtype=np.uint8)
                output[:, :, 2] = index + 1
                outputs.append(output)
            return outputs

    backend = LaMaInpaintingBackend(asset_ref="stub", runner=_Runner())
    results = backend.batch_inpaint_frames(
        [frame_a, frame_b],
        [mask, mask],
        inpaint_radius=3,
        quality_level=4,
    )

    assert captured["batch_calls"] == 1
    assert captured["frames_len"] == 2
    assert captured["masks_len"] == 2
    assert captured["quality_level"] == 4
    assert len(results) == 2
    assert results[0]["trace"]["gpu_inpainting_profile"]["batch_size"] == 2
    assert results[1]["trace"]["gpu_inpainting_profile"]["batch_size"] == 2


def test_lama_backend_batch_inpaint_frames_splits_mixed_roi_shapes_into_smaller_groups() -> None:
    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    frame_small_roi = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame_full = np.zeros((720, 1280, 3), dtype=np.uint8)

    small_mask = np.zeros((720, 1280), dtype=np.uint8)
    small_mask[24:40, 36:60] = 255

    full_mask = np.ones((720, 1280), dtype=np.uint8) * 255

    captured_calls: list[list[tuple[int, int, int]]] = []

    class _Runner:
        def run_batch(self, input_frames, input_masks, **kwargs):
            del input_masks, kwargs
            captured_calls.append([tuple(frame.shape) for frame in input_frames])
            return [np.ones_like(frame, dtype=np.uint8) * 127 for frame in input_frames]

    backend = LaMaInpaintingBackend(asset_ref="stub", runner=_Runner())
    backend.set_runtime_profile({"memory_budget_mb": 2048, "resize_limit": 640})

    results = backend.batch_inpaint_frames(
        [frame_small_roi, frame_full],
        [small_mask, full_mask],
        inpaint_radius=3,
        quality_level=3,
    )

    assert len(captured_calls) == 2
    assert sorted(len(call) for call in captured_calls) == [1, 1]
    assert len({call[0][:2] for call in captured_calls}) == 2
    assert len(results) == 2
    assert results[0]["trace"]["gpu_inpainting_profile"]["batch_size"] == 1
    assert results[1]["trace"]["gpu_inpainting_profile"]["batch_size"] == 1
