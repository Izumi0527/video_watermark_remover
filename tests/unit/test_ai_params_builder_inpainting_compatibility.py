#!/usr/bin/env python3
"""
AIParamsBuilder 修复参数兼容归一化测试。
"""

from __future__ import annotations

from app.config.validators import ConfigValidator
from app.ui.utils.ai_params_builder import AIParamsBuilder


class _DummyPreferences:
    """最小偏好设置桩，仅用于构建 ai_params。"""

    def __init__(self, auto_mode: bool = True) -> None:
        self._auto_mode = auto_mode

    def get_preference(self, section: str, key: str, default=None):
        if section == "processing" and key == "auto_mode":
            return self._auto_mode
        return default


def _build_with_method(method: str, enable_gpu: bool = True) -> dict:
    builder = AIParamsBuilder()
    return builder.build_from_ui(
        preferences=_DummyPreferences(auto_mode=True),
        advanced_params={
            "inpainting_method": method,
            "enable_gpu": enable_gpu,
        },
        manual_selections=None,
        input_file_path=None,
    )


def test_validator_accepts_auto_inpainting_algorithm() -> None:
    """验证器应接受 auto，避免兼容值再次被回退成 gpu_dl。"""
    validator = ConfigValidator()

    assert validator.validate("inpainting_algorithm", "auto") == "auto"


def test_map_inpainting_method_supports_current_ui_labels() -> None:
    """当前 UI 中文文案应继续稳定映射。"""
    builder = AIParamsBuilder()

    assert builder._map_inpainting_method("GPU 深度学习 U-Net (推荐)") == "gpu_dl"
    assert builder._map_inpainting_method("TELEA 快速修复 (OpenCV)") == "telea"
    assert builder._map_inpainting_method("Navier-Stokes 高质量 (OpenCV)") == "navier_stokes"
    assert builder._map_inpainting_method("自定义插值方法") == "custom_interpolation"


def test_map_inpainting_method_supports_legacy_and_english_aliases() -> None:
    """历史别名、后端短名和合理英文别名应统一收敛到规范算法名。"""
    builder = AIParamsBuilder()

    assert builder._map_inpainting_method("auto") == "auto"
    assert builder._map_inpainting_method("telea") == "telea"
    assert builder._map_inpainting_method("ns") == "navier_stokes"
    assert builder._map_inpainting_method("navier-stokes") == "navier_stokes"
    assert builder._map_inpainting_method("navier stokes") == "navier_stokes"
    assert builder._map_inpainting_method("custom") == "custom_interpolation"
    assert builder._map_inpainting_method("custom interpolation") == "custom_interpolation"
    assert builder._map_inpainting_method("custom_interpolation") == "custom_interpolation"
    assert builder._map_inpainting_method("gpu_dl") == "gpu_dl"
    assert builder._map_inpainting_method("gpu-u-net") == "gpu_dl"
    assert builder._map_inpainting_method("gpu deep learning u-net") == "gpu_dl"


def test_unknown_or_auto_method_falls_back_to_safe_auto_without_gpu() -> None:
    """未知值与 auto 都应安全回退到 auto，且不能误启用 GPU 修复。"""
    unknown_params = _build_with_method("legacy_unknown_method", enable_gpu=True)
    auto_params = _build_with_method("auto", enable_gpu=True)

    assert unknown_params["inpainting_algorithm"] == "auto"
    assert unknown_params["use_gpu_inpainting"] is False

    assert auto_params["inpainting_algorithm"] == "auto"
    assert auto_params["use_gpu_inpainting"] is False


def test_only_explicit_gpu_dl_enables_gpu_inpainting() -> None:
    """只有显式 gpu_dl 语义才允许启用 GPU 修复。"""
    explicit_gpu = _build_with_method("gpu_dl", enable_gpu=True)
    ui_gpu = _build_with_method("GPU 深度学习 U-Net (推荐)", enable_gpu=True)
    disabled_gpu = _build_with_method("gpu_dl", enable_gpu=False)
    auto_mode = _build_with_method("auto", enable_gpu=True)

    assert explicit_gpu["inpainting_algorithm"] == "gpu_dl"
    assert explicit_gpu["use_gpu_inpainting"] is True

    assert ui_gpu["inpainting_algorithm"] == "gpu_dl"
    assert ui_gpu["use_gpu_inpainting"] is True

    assert disabled_gpu["inpainting_algorithm"] == "gpu_dl"
    assert disabled_gpu["use_gpu_inpainting"] is False

    assert auto_mode["inpainting_algorithm"] == "auto"
    assert auto_mode["use_gpu_inpainting"] is False
