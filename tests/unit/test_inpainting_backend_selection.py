#!/usr/bin/env python3
"""
统一修复后端选择参数测试。
"""

from __future__ import annotations

import builtins
import importlib
import sys
import types

import pytest

from app.config.validators import ConfigValidator
from app.ui.utils.ai_params_builder import AIParamsBuilder
from tests.unit.test_dynamic_watermark_tracking import _install_ai_runtime_stubs


class _DummyPreferences:
    """最小偏好设置桩，仅用于构建 ai_params。"""

    def get_preference(self, section: str, key: str, default=None):
        if section == "processing" and key == "auto_mode":
            return True
        return default


def _build_with_method(method: str, enable_gpu: bool = True) -> dict:
    builder = AIParamsBuilder()
    return builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "inpainting_method": method,
            "enable_gpu": enable_gpu,
        },
        manual_selections=None,
        input_file_path=None,
    )


def test_validator_accepts_requested_backend_and_opencv_method() -> None:
    """验证器应接受新的后端选择与 OpenCV 方法枚举。"""
    validator = ConfigValidator()

    assert validator.validate("requested_inpainting_backend", "lama") == "lama"
    assert validator.validate("requested_inpainting_backend", "opencv") == "opencv"
    assert validator.validate("opencv_inpainting_method", "telea") == "telea"
    assert validator.validate("opencv_inpainting_method", "auto") == "auto"


def test_builder_maps_future_lama_label_to_requested_backend() -> None:
    """未来 UI 的 LaMa 文案应能提前映射到统一 backend 字段。"""
    params = _build_with_method("LaMa 深度学习修复（推荐）", enable_gpu=True)

    assert params["requested_inpainting_backend"] == "lama"
    assert params["use_gpu_inpainting"] is True


def test_builder_maps_legacy_gpu_label_to_lama_backend() -> None:
    """旧 GPU U-Net 文案应自动迁移到 LaMa backend（legacy_unet 已移除）。"""
    params = _build_with_method("GPU 深度学习 U-Net (推荐)", enable_gpu=True)

    assert params["requested_inpainting_backend"] == "lama"
    assert params["use_gpu_inpainting"] is True


def test_builder_detects_cuda_without_torch_preload(monkeypatch: pytest.MonkeyPatch) -> None:
    """即使 torch 尚未预加载，也应通过显式探测识别可用 CUDA。"""
    builder_module = importlib.import_module("app.ui.utils.ai_params_builder")
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builder_module, "detect_cuda_available", lambda: True)

    params = _build_with_method("LaMa 深度学习修复（推荐）", enable_gpu=True)

    assert params["requested_inpainting_backend"] == "lama"
    assert params["use_gpu_inpainting"] is True


def test_detect_cuda_available_imports_torch_when_not_preloaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """helper 应在 torch 未预加载时主动导入并读取 CUDA 能力。"""
    builder_module = importlib.import_module("app.ui.utils.ai_params_builder")
    real_import = builtins.__import__
    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True))

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "torch":
            return fake_torch
        return real_import(name, globals, locals, fromlist, level)

    builder_module.detect_cuda_available.cache_clear()
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", _fake_import)

    assert builder_module.detect_cuda_available() is True
    builder_module.detect_cuda_available.cache_clear()


def test_detect_cuda_available_returns_false_when_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """helper 在 torch 导入失败时应安全回退为 False。"""
    builder_module = importlib.import_module("app.ui.utils.ai_params_builder")
    real_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "torch":
            raise ImportError("torch unavailable")
        return real_import(name, globals, locals, fromlist, level)

    builder_module.detect_cuda_available.cache_clear()
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", _fake_import)

    assert builder_module.detect_cuda_available() is False
    builder_module.detect_cuda_available.cache_clear()


def test_builder_maps_opencv_label_to_backend_and_method() -> None:
    """OpenCV 文案应拆分为 backend 与 opencv method。"""
    params = _build_with_method("TELEA 快速修复 (OpenCV)", enable_gpu=True)

    assert params["requested_inpainting_backend"] == "opencv"
    assert params["opencv_inpainting_method"] == "telea"
    assert params["use_gpu_inpainting"] is False


def test_factory_creates_expected_backend_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """backend factory 应返回 OpenCV，并对未知值安全回退。"""
    _install_ai_runtime_stubs(monkeypatch)
    for module_name in (
        "app.core.ai.inpainting_backends.factory",
        "app.core.ai.inpainting_backends.base",
        "app.core.ai.inpainting_backends.opencv_backend",
    ):
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    factory_module = importlib.import_module("app.core.ai.inpainting_backends.factory")
    create_inpainting_backend = factory_module.create_inpainting_backend

    opencv_backend = create_inpainting_backend(
        requested_backend="opencv",
        config=None,
        torch_device="cpu",
    )
    unknown_backend = create_inpainting_backend(
        requested_backend="unexpected_backend",
        config=None,
        torch_device="cpu",
    )

    assert opencv_backend.backend_id == "opencv"
    assert unknown_backend.backend_id == "opencv"
    assert callable(getattr(opencv_backend, "load"))
    assert callable(getattr(opencv_backend, "inpaint_frame"))
