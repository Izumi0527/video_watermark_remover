#!/usr/bin/env python3
"""
动态水印跟随修复的回归测试

覆盖两类关键行为：
1. 自动检测模式下，历史手动框不能覆盖逐帧检测
2. 手动模式下，手动框选仍然保持原有静态修复行为
"""

import importlib
import logging
import sys
import types

import numpy as np
import pytest


def _install_ai_runtime_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """为纯单元测试注入轻量依赖，并确保作用域限定在当前测试。"""
    torch_module = types.ModuleType("torch")
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.device = lambda name: name
    monkeypatch.setitem(sys.modules, "torch", torch_module)

    dl_inpainter_module = types.ModuleType("app.core.ai.dl_inpainter")

    class _DummyDeepLearningInpainter:
        def __init__(self, *args, **kwargs):
            pass

        def load_model(self):
            return True

    dl_inpainter_module.DeepLearningInpainter = _DummyDeepLearningInpainter
    monkeypatch.setitem(sys.modules, "app.core.ai.dl_inpainter", dl_inpainter_module)

    image_inpainter_module = types.ModuleType("app.core.ai.image_inpainter")

    class _DummyImageInpainter:
        def __init__(self, *args, **kwargs):
            pass

        def load_model(self):
            return True

    image_inpainter_module.ImageInpainter = _DummyImageInpainter
    monkeypatch.setitem(sys.modules, "app.core.ai.image_inpainter", image_inpainter_module)

    image_processor_module = types.ModuleType("app.core.ai.image_processor")
    image_processor_module.apply_preprocessing = lambda frame, **kwargs: frame
    image_processor_module.apply_postprocessing = (
        lambda original_frame, processed_frame, mask, **kwargs: processed_frame
    )
    monkeypatch.setitem(sys.modules, "app.core.ai.image_processor", image_processor_module)

    yolo_detector_module = types.ModuleType("app.core.ai.yolo_detector")

    class _DummyYOLOWatermarkDetector:
        def __init__(self, *args, **kwargs):
            self.model = None
            self.device = kwargs.get("device", "cpu")

        def load_model(self):
            return True

        def detect_watermark(self, frame):
            return np.zeros(frame.shape[:2], dtype=np.uint8)

    yolo_detector_module.YOLOWatermarkDetector = _DummyYOLOWatermarkDetector
    monkeypatch.setitem(sys.modules, "app.core.ai.yolo_detector", yolo_detector_module)


def _load_test_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[type, type]:
    """在隔离依赖后延迟导入目标模块，避免污染其他测试。"""
    _install_ai_runtime_stubs(monkeypatch)
    monkeypatch.delitem(sys.modules, "app.core.ai.ai_handler", raising=False)
    monkeypatch.delitem(sys.modules, "app.ui.utils.ai_params_builder", raising=False)

    ai_handler_module = importlib.import_module("app.core.ai.ai_handler")
    ai_params_builder_module = importlib.import_module("app.ui.utils.ai_params_builder")
    return ai_handler_module.AIHandler, ai_params_builder_module.AIParamsBuilder


class _DummyPreferences:
    """用于测试的偏好设置桩对象。"""

    def __init__(self, auto_mode: bool):
        self.auto_mode = auto_mode

    def get_preference(self, section, key, default=None):
        if section == "processing" and key == "auto_mode":
            return self.auto_mode
        return default


class _DummyDetector:
    """用于验证是否真正走到自动检测分支。"""

    def __init__(self, mask: np.ndarray):
        self.mask = mask
        self.call_count = 0

    def detect_watermark(self, frame: np.ndarray) -> np.ndarray:
        self.call_count += 1
        return self.mask.copy()


def _build_lightweight_ai_handler(detector: _DummyDetector, ai_handler_cls: type):
    """构造一个仅用于 `process_frame` 行为测试的轻量 AIHandler。"""
    handler = ai_handler_cls.__new__(ai_handler_cls)
    handler.logger = logging.getLogger(__name__)
    handler.enable_blur_preprocess = False
    handler.enable_denoise_preprocess = False
    handler.enable_sharp_preprocess = False
    handler.enable_smooth_postprocess = False
    handler.enable_blend_postprocess = False
    handler.enable_enhance_postprocess = False
    handler.use_gpu_inpainting = False
    handler.dl_inpainter = None
    handler.watermark_detector = detector
    handler.inpaint_frame = lambda frame, _mask: frame.copy()
    return handler


def _create_test_frame() -> np.ndarray:
    return np.zeros((48, 64, 3), dtype=np.uint8)


def _create_detected_mask() -> np.ndarray:
    mask = np.zeros((48, 64), dtype=np.uint8)
    mask[20:30, 28:42] = 255
    return mask


def test_ai_params_builder_auto_mode_ignores_manual_selections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """自动模式下不应把历史手动框转换成固定 `user_mask`。"""
    _, ai_params_builder_cls = _load_test_targets(monkeypatch)
    builder = ai_params_builder_cls()

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(auto_mode=True),
        advanced_params={},
        manual_selections=[(10, 12, 20, 8)],
        input_file_path=None,
    )

    assert ai_params["auto_detect"] is True
    assert ai_params["user_mask"] is None


def test_ai_params_builder_manual_mode_keeps_manual_selections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """手动模式下仍应保留手动框选区域。"""
    _, ai_params_builder_cls = _load_test_targets(monkeypatch)
    builder = ai_params_builder_cls()

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(auto_mode=False),
        advanced_params={},
        manual_selections=[(10, 12, 20, 8)],
        input_file_path=None,
    )

    assert ai_params["auto_detect"] is False
    assert ai_params["user_mask"] == [(10, 12, 20, 8)]


def test_ai_handler_prefers_auto_detection_when_conflicting_params_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """自动模式与手动掩码冲突时，应优先走自动检测。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _DummyDetector(_create_detected_mask())
    handler = _build_lightweight_ai_handler(detector, ai_handler_cls)

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": True,
            "user_mask": [(1, 1, 10, 10)],
            "detection_sensitivity": 0.5,
        },
    )

    assert detector.call_count == 1
    assert info["detection_method"] == "automatic_yolo"


def test_ai_handler_uses_manual_mask_when_auto_detection_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """手动模式下应继续使用手动选择区域。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _DummyDetector(_create_detected_mask())
    handler = _build_lightweight_ai_handler(detector, ai_handler_cls)

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
            "detection_sensitivity": 0.5,
        },
    )

    assert detector.call_count == 0
    assert info["detection_method"] == "manual_selection"
    assert info["manual_regions_count"] == 1
