#!/usr/bin/env python3
"""
AIHandler 单进程 LaMa 批修复回归测试。
"""

from __future__ import annotations

import sys

import numpy as np
import pytest

from tests.unit.test_dynamic_watermark_tracking import _load_test_targets


class _StaticBatchDetector:
    def __init__(self, masks):
        self._masks = masks
        self.batch_calls = 0
        self.single_calls = 0

    def detect_batch(self, _frames):
        self.batch_calls += 1
        return [mask.copy() for mask in self._masks]

    def detect_watermark(self, frame):
        self.single_calls += 1
        return np.zeros(frame.shape[:2], dtype=np.uint8)


def _create_mask() -> np.ndarray:
    mask = np.zeros((48, 64), dtype=np.uint8)
    mask[8:16, 12:20] = 255
    return mask


def _create_frame(seed: int) -> np.ndarray:
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    frame[:, :, 1] = seed
    return frame


def test_ai_handler_process_frames_batch_prefers_lama_backend_batch_inpainting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai_handler_cls, _ = _load_test_targets(monkeypatch)

    frames = [_create_frame(10), _create_frame(20)]
    masks = [_create_mask(), _create_mask()]
    detector = _StaticBatchDetector(masks)

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
            "requested_inpainting_backend": "lama",
            "quality_level": 3,
            "inpaint_radius": 3,
        },
    )
    handler.watermark_detector = detector

    captured: dict[str, object] = {"batch_calls": 0, "single_calls": 0}

    class _BatchBackend:
        backend_id = "lama"

        def batch_inpaint_frames(
            self,
            input_frames,
            input_masks,
            *,
            inpaint_radius,
            quality_level,
            opencv_method="auto",
        ):
            captured["batch_calls"] = captured.get("batch_calls", 0) + 1
            captured["frames_len"] = len(input_frames)
            captured["masks_len"] = len(input_masks)
            captured["radius"] = inpaint_radius
            captured["quality_level"] = quality_level
            outputs = []
            for index, frame in enumerate(input_frames):
                processed = frame.copy()
                processed[:, :, 0] = index + 1
                outputs.append(
                    {
                        "frame": processed,
                        "trace": {
                            "inpainting_backend": "lama",
                            "inpainting_method": "lama",
                            "effective_quality_level": quality_level,
                            "effective_inpaint_radius": inpaint_radius,
                            "gpu_inpainting_profile": {
                                "quality_level": quality_level,
                                "requested_radius": inpaint_radius,
                            },
                            "gpu_inpainting_retry": None,
                            "gpu_inpainting_oom_retry_used": False,
                            "gpu_inpainting_retry_count": 0,
                            "gpu_inpainting_retry_profile": None,
                            "loaded_inpainting_asset_ref": "stub-lama.pt",
                            "loaded_inpainting_model_path": "stub-lama.pt",
                        },
                    }
                )
            return outputs

        def get_last_trace(self):
            return {}

    handler.deep_inpainting_backend = _BatchBackend()
    handler.use_gpu_inpainting = True
    handler.inpaint_frame = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("不应回退到单帧 inpaint_frame")
    )

    results = handler.process_frames_batch(
        frames,
        {
            "auto_detect": True,
            "user_mask": None,
            "detection_sensitivity": 0.5,
        },
    )

    assert detector.batch_calls == 1
    assert detector.single_calls == 0
    assert captured["batch_calls"] == 1
    assert captured["frames_len"] == 2
    assert captured["masks_len"] == 2
    assert captured["radius"] == 3
    assert captured["quality_level"] == 3
    assert len(results) == 2
    assert int(results[0][0][0, 0, 0]) == 1
    assert int(results[1][0][0, 0, 0]) == 2
    assert results[0][1]["inpainting_backend"] == "lama"
    assert results[1][1]["inpainting_backend"] == "lama"


def test_ai_handler_build_gpu_runtime_profile_caps_lama_resize_limit_for_throughput(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "use_gpu_inpainting": True,
            "device": "auto",
            "requested_inpainting_backend": "lama",
            "quality_level": 3,
            "inpaint_radius": 3,
            "gpu_memory_mb": 4096,
        },
    )

    profile = handler.build_gpu_runtime_profile((720, 1280, 3))

    assert profile["memory_budget_mb"] == 4096
    assert profile["resize_limit"] == 960


def test_ai_handler_logs_batch_lama_observation(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    frames = [_create_frame(10), _create_frame(20)]
    masks = [_create_mask(), _create_mask()]
    detector = _StaticBatchDetector(masks)

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "use_gpu_inpainting": True,
            "device": "auto",
            "requested_inpainting_backend": "lama",
            "quality_level": 3,
            "inpaint_radius": 3,
            "gpu_memory_mb": 4096,
        },
    )
    handler.watermark_detector = detector

    class _ObservedBatchBackend:
        backend_id = "lama"

        def batch_inpaint_frames(
            self,
            input_frames,
            input_masks,
            *,
            inpaint_radius,
            quality_level,
            opencv_method="auto",
        ):
            del input_masks, inpaint_radius, quality_level, opencv_method
            return [
                {
                    "frame": frame.copy(),
                    "trace": {
                        "inpainting_backend": "lama",
                        "inpainting_method": "lama",
                        "gpu_inpainting_profile": {
                            "batch_size": len(input_frames),
                        },
                    },
                }
                for frame in input_frames
            ]

        def get_last_trace(self):
            return {}

    handler.deep_inpainting_backend = _ObservedBatchBackend()
    handler.use_gpu_inpainting = True

    with caplog.at_level("INFO"):
        results = handler.process_frames_batch(
            frames,
            {
                "auto_detect": True,
                "user_mask": None,
                "detection_sensitivity": 0.5,
            },
        )

    assert len(results) == 2
    assert any(
        "批量 LaMa 修复" in record.message and "candidates=2" in record.message
        for record in caplog.records
    )
