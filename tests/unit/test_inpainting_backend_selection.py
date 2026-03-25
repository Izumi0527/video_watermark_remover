#!/usr/bin/env python3
"""
统一修复后端选择参数测试。
"""

from __future__ import annotations

import importlib
import sys

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
    assert validator.validate("requested_inpainting_backend", "legacy_unet") == "legacy_unet"
    assert validator.validate("requested_inpainting_backend", "opencv") == "opencv"
    assert validator.validate("opencv_inpainting_method", "telea") == "telea"
    assert validator.validate("opencv_inpainting_method", "auto") == "auto"


def test_builder_maps_future_lama_label_to_requested_backend() -> None:
    """未来 UI 的 LaMa 文案应能提前映射到统一 backend 字段。"""
    params = _build_with_method("LaMa 深度学习修复（推荐）", enable_gpu=True)

    assert params["requested_inpainting_backend"] == "lama"
    assert params["use_gpu_inpainting"] is True


def test_builder_maps_legacy_gpu_label_to_legacy_unet_backend() -> None:
    """当前 GPU U-Net 文案应明确收敛到 legacy U-Net backend。"""
    params = _build_with_method("GPU 深度学习 U-Net (推荐)", enable_gpu=True)

    assert params["requested_inpainting_backend"] == "legacy_unet"
    assert params["use_gpu_inpainting"] is True


def test_builder_maps_opencv_label_to_backend_and_method() -> None:
    """OpenCV 文案应拆分为 backend 与 opencv method。"""
    params = _build_with_method("TELEA 快速修复 (OpenCV)", enable_gpu=True)

    assert params["requested_inpainting_backend"] == "opencv"
    assert params["opencv_inpainting_method"] == "telea"
    assert params["use_gpu_inpainting"] is False


def test_factory_creates_expected_backend_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """backend factory 应返回 OpenCV / legacy U-Net，并对未知值安全回退。"""
    _install_ai_runtime_stubs(monkeypatch)
    for module_name in (
        "app.core.ai.inpainting_backends.factory",
        "app.core.ai.inpainting_backends.base",
        "app.core.ai.inpainting_backends.opencv_backend",
        "app.core.ai.inpainting_backends.legacy_unet_backend",
    ):
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    factory_module = importlib.import_module("app.core.ai.inpainting_backends.factory")
    create_inpainting_backend = factory_module.create_inpainting_backend

    opencv_backend = create_inpainting_backend(
        requested_backend="opencv",
        config=None,
        torch_device="cpu",
    )
    legacy_backend = create_inpainting_backend(
        requested_backend="legacy_unet",
        config=None,
        torch_device="cpu",
    )
    unknown_backend = create_inpainting_backend(
        requested_backend="unexpected_backend",
        config=None,
        torch_device="cpu",
    )

    assert opencv_backend.backend_id == "opencv"
    assert legacy_backend.backend_id == "legacy_unet"
    assert unknown_backend.backend_id == "opencv"
    assert callable(getattr(opencv_backend, "load"))
    assert callable(getattr(legacy_backend, "inpaint_frame"))
