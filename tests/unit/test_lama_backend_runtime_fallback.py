#!/usr/bin/env python3
"""
LaMa backend 运行期降级回归测试。
"""

from __future__ import annotations

import logging
import shutil
import sys
import uuid
from pathlib import Path

import pytest

from tests.unit.test_dynamic_watermark_tracking import (
    _create_test_frame,
    _load_test_targets,
)


@pytest.fixture
def tmp_path() -> Path:
    """使用仓库内临时目录，避免系统 Temp 的 .lock 权限噪音。"""
    base_dir = Path.cwd() / ".tmp_pytest_lama_runtime"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = base_dir / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_ai_handler_falls_back_to_opencv_when_lama_asset_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """请求 LaMa 且资源缺失时，应在加载阶段降级到 OpenCV。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "requested_inpainting_backend": "lama",
            "use_gpu_inpainting": True,
            "device": "cuda",
            "lama_model_path": "models/missing-lama.ckpt",
        },
    )
    assert handler.load_models() is True
    assert handler.use_gpu_inpainting is False

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["requested_inpainting_backend"] == "lama"
    assert info["actual_inpainting_backend"] == "opencv"
    assert info["inpainting_fallback_reason"] == "lama_model_path_not_found"


def test_ai_handler_falls_back_to_opencv_when_lama_runtime_inpainting_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """LaMa 运行期抛异常时，当前帧应立即回退到 OpenCV。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    lama_asset = tmp_path / "lama.ckpt"
    lama_asset.write_bytes(b"stub")

    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    monkeypatch.setattr(
        LaMaInpaintingBackend,
        "_create_runner",
        lambda self: (lambda frame, mask, **kwargs: (_ for _ in ()).throw(RuntimeError("lama runtime failed"))),
    )

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "requested_inpainting_backend": "lama",
            "use_gpu_inpainting": True,
            "device": "cuda",
            "lama_model_path": str(lama_asset),
            "quality_level": 4,
            "inpaint_radius": 6,
        },
    )
    assert handler.load_models() is True

    captured: dict[str, object] = {}

    def fake_opencv_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        captured["method"] = method
        captured["radius"] = radius
        captured["quality_level"] = quality_level
        return frame.copy()

    handler.image_inpainter.inpaint_frame = fake_opencv_inpaint

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
    assert info["requested_inpainting_backend"] == "lama"
    assert info["actual_inpainting_backend"] == "opencv"
    assert info["inpainting_fallback_reason"] == "lama_runtime_exception"


def test_ai_handler_resolves_lama_asset_from_env_for_main_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """主应用链路应能从 VWR_LAMA_MODEL_PATH 解析 LaMa 资源。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    lama_asset = tmp_path / "big-lama.pt"
    lama_asset.write_bytes(b"stub")
    monkeypatch.setenv("VWR_LAMA_MODEL_PATH", str(lama_asset))

    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    monkeypatch.setattr(
        LaMaInpaintingBackend,
        "_create_runner",
        lambda self: (lambda frame, mask, **kwargs: frame.copy()),
    )

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "requested_inpainting_backend": "lama",
            "use_gpu_inpainting": True,
            "device": "cuda",
        },
    )

    assert handler.configured_lama_model_path == str(lama_asset)
    assert handler.configured_inpainting_asset_ref == str(lama_asset)
    assert handler.load_models() is True
    assert handler.use_gpu_inpainting is True
    assert handler.loaded_inpainting_asset_ref == str(lama_asset)


def test_ai_handler_missing_lama_asset_logs_expected_downgrade_message(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """缺少 LaMa 模型路径时应提示可预期降级，而不是打误导性的 error。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VWR_LAMA_MODEL_PATH", raising=False)
    monkeypatch.setattr(ai_handler_cls, "_resolve_lama_model_path", lambda self: None)

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "requested_inpainting_backend": "lama",
            "use_gpu_inpainting": True,
            "device": "cuda",
        },
    )

    with caplog.at_level(logging.WARNING):
        assert handler.load_models() is True

    assert "Failed to load deep learning inpainter" not in caplog.text
    assert "未配置 LaMa 模型路径" in caplog.text
    assert "当前改用 OpenCV 修复" in caplog.text


def test_ai_handler_resolves_lama_asset_from_project_candidate_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """当项目目录存在 models/big-lama.pt 时，主应用链路应自动解析该候选路径。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    project_models_dir = tmp_path / "models"
    project_models_dir.mkdir(parents=True, exist_ok=True)
    lama_asset = project_models_dir / "big-lama.pt"
    lama_asset.write_bytes(b"stub")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VWR_LAMA_MODEL_PATH", raising=False)

    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    monkeypatch.setattr(
        LaMaInpaintingBackend,
        "_create_runner",
        lambda self: (lambda frame, mask, **kwargs: frame.copy()),
    )

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "requested_inpainting_backend": "lama",
            "use_gpu_inpainting": True,
            "device": "cuda",
        },
    )

    assert handler.configured_lama_model_path == str(lama_asset)
    assert handler.configured_inpainting_asset_ref == str(lama_asset)
    assert handler.load_models() is True
    assert handler.use_gpu_inpainting is True


def test_ai_handler_logs_actual_backend_name_when_lama_loads_successfully(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """LaMa 加载成功时，成功日志应展示实际 backend，而不是固定写成 U-Net。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    lama_asset = tmp_path / "big-lama.pt"
    lama_asset.write_bytes(b"stub")

    from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

    monkeypatch.setattr(
        LaMaInpaintingBackend,
        "_create_runner",
        lambda self: (lambda frame, mask, **kwargs: frame.copy()),
    )

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "requested_inpainting_backend": "lama",
            "use_gpu_inpainting": True,
            "device": "cuda",
            "lama_model_path": str(lama_asset),
        },
    )

    with caplog.at_level(logging.INFO):
        assert handler.load_models() is True

    assert "Image Inpainting: LaMa TorchScript" in caplog.text
