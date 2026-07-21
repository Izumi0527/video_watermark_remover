#!/usr/bin/env python3
"""
AIHandler GPU 运行期降级回归测试。
"""

from __future__ import annotations

import sys

import pytest

from tests.unit.test_dynamic_watermark_tracking import (
    _build_test_config,
    _create_test_frame,
    _install_fake_deep_backend_factory,
    _load_test_targets,
)


def test_ai_handler_falls_back_to_opencv_when_gpu_runtime_inpainting_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 修复运行期抛异常时，当前帧应立即回退到 OpenCV。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    model_path = tmp_path / "stub-lama.pt"
    model_path.write_bytes(b"stub")

    created: dict = {}
    handler = ai_handler_cls(
        config=_build_test_config(str(model_path)),
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
            "quality_level": 4,
            "inpaint_radius": 6,
        },
    )
    _install_fake_deep_backend_factory(monkeypatch, created)
    assert handler.load_models() is True

    captured: dict[str, object] = {}

    def fake_opencv_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        captured["method"] = method
        captured["radius"] = radius
        captured["quality_level"] = quality_level
        handler.image_inpainter.last_quality_level = quality_level
        return frame.copy()

    def raise_gpu_error(frame, mask, radius, quality_level):
        raise RuntimeError("gpu runtime failed")

    handler.image_inpainter.inpaint_frame = fake_opencv_inpaint
    created["backend"].inpaint_frame_impl = raise_gpu_error

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert captured == {
        "method": "auto",
        "radius": 6,
        "quality_level": 4,
    }
    assert info["inpainting_backend"] == "opencv"
    assert info["inpainting_method"] == "auto"
    assert info["gpu_inpainting_requested"] is True
    assert info["gpu_inpainting_fallback_reason"] == "lama_runtime_exception"
    assert info["loaded_inpainting_model_path"] == str(model_path)
    assert handler.use_gpu_inpainting is False
    assert handler.deep_inpainting_backend is None


def test_ai_handler_applies_gpu_memory_budget_to_deep_inpainting_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    model_path = tmp_path / "stub-lama.pt"
    model_path.write_bytes(b"stub")

    created: dict = {}
    handler = ai_handler_cls(
        config=_build_test_config(str(model_path)),
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
            "gpu_memory_mb": 1024,
        },
    )
    _install_fake_deep_backend_factory(monkeypatch, created)
    assert handler.load_models() is True

    runtime_profile = handler.build_gpu_runtime_profile((1080, 1920, 3))

    assert runtime_profile["memory_budget_mb"] == 1024
    assert runtime_profile["resize_limit"] == 640
    assert created["backend"].last_runtime_profile["memory_budget_mb"] == 1024


def test_ai_handler_pushes_runtime_profile_to_active_deep_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
            "gpu_memory_mb": 1024,
            "requested_inpainting_backend": "lama",
        },
    )

    captured: dict[str, object] = {}

    class _Backend:
        def set_runtime_profile(self, profile):
            captured.update(profile)

    handler.deep_inpainting_backend = _Backend()

    runtime_profile = handler.build_gpu_runtime_profile((1080, 1920, 3))

    assert runtime_profile["memory_budget_mb"] == 1024
    assert captured["memory_budget_mb"] == 1024
    assert captured["resize_limit"] == 640
