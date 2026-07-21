#!/usr/bin/env python3
"""
processing_info 质量追溯回归测试。
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


def test_processing_info_reports_requested_and_effective_quality_for_opencv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenCV 路径应同时记录原始请求值和最终实际生效质量。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "use_gpu_inpainting": False,
            "device": "cpu",
            "inpainting_algorithm": "telea",
            "quality_level": 999,
        },
    )

    def fake_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        handler.image_inpainter.last_quality_level = 5
        return frame.copy()

    handler.image_inpainter.inpaint_frame = fake_inpaint

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["requested_quality_level"] == 999
    assert info["quality_level"] == 999
    assert info["effective_quality_level"] == 5
    assert info["inpainting_backend"] == "opencv"


def test_processing_info_reports_requested_and_effective_quality_for_gpu(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 路径应从最后一次实际 profile 中提取生效质量等级。"""
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
            "quality_level": 999,
            "inpaint_radius": 7,
        },
    )
    _install_fake_deep_backend_factory(monkeypatch, created)
    assert handler.load_models() is True

    created["backend"].extra_trace = {"effective_quality_level": 5}

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["requested_quality_level"] == 999
    assert info["quality_level"] == 999
    assert info["effective_quality_level"] == 5
    assert info["inpainting_backend"] == "lama"
