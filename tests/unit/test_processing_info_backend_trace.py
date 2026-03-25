#!/usr/bin/env python3
"""
processing_info 修复后端追溯契约测试。
"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

from tests.unit.test_dynamic_watermark_tracking import (
    _build_test_config,
    _create_test_frame,
    _load_test_targets,
)


@pytest.fixture
def tmp_path() -> Path:
    """使用仓库内临时目录，避免系统 Temp 的 .lock 权限噪音。"""
    base_dir = Path.cwd() / ".tmp_pytest_processing_trace"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = base_dir / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_processing_info_reports_requested_and_actual_backend_for_opencv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenCV 路径应同时记录请求后端、实际后端与统一 fallback 字段。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "requested_inpainting_backend": "opencv",
            "opencv_inpainting_method": "telea",
            "use_gpu_inpainting": False,
            "device": "cpu",
            "inpainting_algorithm": "telea",
        },
    )

    def fake_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        handler.image_inpainter.last_method_used = method
        return frame.copy()

    handler.image_inpainter.inpaint_frame = fake_inpaint

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["requested_inpainting_backend"] == "opencv"
    assert info["actual_inpainting_backend"] == "opencv"
    assert info["inpainting_backend"] == "opencv"
    assert info["inpainting_fallback_reason"] is None
    assert info["gpu_inpainting_fallback_reason"] is None


def test_processing_info_reports_backend_trace_when_legacy_unet_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """legacy U-Net 运行期降级时，应记录 requested/actual/fallback 三元组。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    model_path = tmp_path / "stub-unet.pth"
    model_path.write_bytes(b"stub")

    handler = ai_handler_cls(
        config=_build_test_config(str(model_path)),
        ai_params={
            "requested_inpainting_backend": "legacy_unet",
            "use_gpu_inpainting": True,
            "device": "cuda",
            "quality_level": 4,
            "inpaint_radius": 6,
        },
    )
    assert handler.load_models() is True

    def raise_gpu_error(frame, mask, radius=3, quality_level=3, profile=None):
        raise RuntimeError("legacy unet runtime failed")

    def fallback_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        handler.image_inpainter.last_method_used = "telea"
        return frame.copy()

    handler.dl_inpainter.inpaint_frame = raise_gpu_error
    handler.image_inpainter.inpaint_frame = fallback_inpaint

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["requested_inpainting_backend"] == "legacy_unet"
    assert info["actual_inpainting_backend"] == "opencv"
    assert info["inpainting_backend"] == "opencv"
    assert info["inpainting_fallback_reason"] == "gpu_runtime_exception"
    assert info["gpu_inpainting_fallback_reason"] == "gpu_runtime_exception"
