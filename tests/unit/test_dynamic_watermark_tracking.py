#!/usr/bin/env python3
"""
动态水印跟随修复的回归测试

覆盖两类关键行为：
1. 自动检测模式下，历史手动框不能覆盖逐帧检测
2. 手动模式下，手动框选仍然保持原有静态修复行为
"""

import configparser
import importlib
import logging
import sys
import types

import numpy as np
import pytest


def _install_ai_runtime_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """为纯单元测试注入轻量依赖，并确保作用域限定在当前测试。"""
    torch_module = types.ModuleType("torch")
    torch_module.cuda = types.SimpleNamespace(
        is_available=lambda: False,
        get_device_name=lambda _index: "Stub GPU",
    )
    torch_module.device = lambda name: name
    monkeypatch.setitem(sys.modules, "torch", torch_module)

    dl_inpainter_module = types.ModuleType("app.core.ai.dl_inpainter")
    dl_inpainter_module.last_init_kwargs = None
    dl_inpainter_module.last_load_model_path = None
    dl_inpainter_module.next_load_model_result = True
    dl_inpainter_module.last_inpaint_kwargs = None

    class _DummyDeepLearningInpainter:
        def __init__(self, *args, **kwargs):
            dl_inpainter_module.last_init_kwargs = dict(kwargs)
            self.last_profile_used = None
            self.last_retry_info = None

        def load_model(self, model_path=None):
            dl_inpainter_module.last_load_model_path = model_path
            return dl_inpainter_module.next_load_model_result

        def inpaint_frame(self, frame, mask, radius=3, quality_level=3, profile=None):
            dl_inpainter_module.last_inpaint_kwargs = {
                "radius": radius,
                "quality_level": quality_level,
                "profile": profile,
            }
            self.last_profile_used = {
                "requested_radius": radius,
                "quality_level": quality_level,
                "mask_expand_px": radius + quality_level,
                "mask_feather_px": quality_level,
            }
            return frame.copy()

    dl_inpainter_module.DeepLearningInpainter = _DummyDeepLearningInpainter
    monkeypatch.setitem(sys.modules, "app.core.ai.dl_inpainter", dl_inpainter_module)

    image_inpainter_module = types.ModuleType("app.core.ai.image_inpainter")

    class _DummyImageInpainter:
        def __init__(self, *args, **kwargs):
            pass

        def load_model(self):
            return True

        def inpaint_frame(self, frame, mask, method=None, radius=3, quality_level=3):
            return frame.copy()

    image_inpainter_module.ImageInpainter = _DummyImageInpainter
    monkeypatch.setitem(sys.modules, "app.core.ai.image_inpainter", image_inpainter_module)

    image_processor_module = types.ModuleType("app.core.ai.image_processor")
    image_processor_module.apply_preprocessing = lambda frame, **kwargs: frame
    image_processor_module.apply_postprocessing = (
        lambda original_frame, processed_frame, mask, **kwargs: processed_frame
    )
    monkeypatch.setitem(sys.modules, "app.core.ai.image_processor", image_processor_module)

    yolo_detector_module = types.ModuleType("app.core.ai.yolo_detector")
    yolo_detector_module.last_init_kwargs = None

    class _DummyYOLOWatermarkDetector:
        def __init__(self, *args, **kwargs):
            yolo_detector_module.last_init_kwargs = dict(kwargs)
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
    handler.quality_level = 3
    handler.inpainting_algorithm = "auto"
    handler.inpaint_radius = 3
    handler.last_inpainting_method_used = None
    handler.enable_blur_preprocess = False
    handler.enable_denoise_preprocess = False
    handler.enable_sharp_preprocess = False
    handler.enable_smooth_postprocess = False
    handler.enable_blend_postprocess = False
    handler.enable_enhance_postprocess = False
    handler.requested_gpu_inpainting = False
    handler.use_gpu_inpainting = False
    handler.gpu_inpainting_fallback_reason = None
    handler.configured_inpainting_model_path = None
    handler.loaded_inpainting_model_path = None
    handler.last_inpainting_backend = None
    handler.device = "cpu"
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


def _build_test_config(inpainting_model_path: str = "") -> configparser.ConfigParser:
    """构造仅包含 GPU 修复权重路径的测试配置。"""
    config = configparser.ConfigParser()
    config["Models"] = {"inpainting_model_path": inpainting_model_path}
    return config


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


def test_ai_params_builder_opencv_method_disables_gpu_inpainting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """选择 OpenCV 修复算法时应禁用 GPU 深度学习修复，避免算法选择被覆盖。"""
    _, ai_params_builder_cls = _load_test_targets(monkeypatch)
    builder = ai_params_builder_cls()

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(auto_mode=True),
        advanced_params={
            "inpainting_method": "TELEA 快速修复 (OpenCV)",
            "enable_gpu": True,
        },
        manual_selections=None,
        input_file_path=None,
    )

    assert ai_params["inpainting_algorithm"] == "telea"
    assert ai_params["use_gpu_inpainting"] is False


def test_ai_params_builder_gpu_unet_respects_enable_gpu_toggle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """选择 GPU U-Net 时，enable_gpu 复选框应决定是否启用 GPU 深度学习修复。"""
    _, ai_params_builder_cls = _load_test_targets(monkeypatch)
    builder = ai_params_builder_cls()

    enabled_params = builder.build_from_ui(
        preferences=_DummyPreferences(auto_mode=True),
        advanced_params={
            "inpainting_method": "GPU 深度学习 U-Net (推荐)",
            "enable_gpu": True,
        },
        manual_selections=None,
        input_file_path=None,
    )
    assert enabled_params["inpainting_algorithm"] == "gpu_dl"
    assert enabled_params["use_gpu_inpainting"] is True

    disabled_params = builder.build_from_ui(
        preferences=_DummyPreferences(auto_mode=True),
        advanced_params={
            "inpainting_method": "GPU 深度学习 U-Net (推荐)",
            "enable_gpu": False,
        },
        manual_selections=None,
        input_file_path=None,
    )
    assert disabled_params["inpainting_algorithm"] == "gpu_dl"
    assert disabled_params["use_gpu_inpainting"] is False


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


def test_ai_handler_passes_min_area_pixels_to_yolo_detector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AIHandler 初始化检测器时应透传最小检测区域，确保 UI 参数真正进入后处理。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    yolo_detector_module = sys.modules["app.core.ai.yolo_detector"]

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "conf_threshold": 0.35,
            "device": "cpu",
            "min_area_pixels": 321,
        },
    )

    assert handler.watermark_detector is not None
    assert yolo_detector_module.last_init_kwargs["min_area_pixels"] == 321


def test_ai_handler_passes_inpainting_params_to_opencv_inpainter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AIHandler 应把修复算法、半径、质量真正透传给 OpenCV 修复器。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "use_gpu_inpainting": False,
            "device": "cpu",
            "inpainting_algorithm": "telea",
            "inpaint_radius": 7,
            "quality_level": 5,
        },
    )
    captured = {}

    def fake_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        captured["method"] = method
        captured["radius"] = radius
        captured["quality_level"] = quality_level
        return frame.copy()

    handler.image_inpainter.inpaint_frame = fake_inpaint

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert captured == {
        "method": "telea",
        "radius": 7,
        "quality_level": 5,
    }
    assert info["inpainting_method"] == "telea"


def test_ai_handler_higher_quality_strengthens_postprocess_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """更高质量等级应让后处理强度整体上升。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    ai_handler_module = sys.modules["app.core.ai.ai_handler"]
    profiles = []

    def fake_apply_postprocessing(original_frame, processed_frame, mask, **kwargs):
        profiles.append(dict(kwargs))
        return processed_frame

    monkeypatch.setattr(ai_handler_module, "apply_postprocessing", fake_apply_postprocessing)

    for quality_level in (1, 5):
        handler = ai_handler_cls(
            config=None,
            ai_params={
                "use_gpu_inpainting": False,
                "device": "cpu",
                "quality_level": quality_level,
                "enable_smooth_postprocess": True,
                "enable_blend_postprocess": True,
                "enable_enhance_postprocess": True,
            },
        )
        handler.image_inpainter.inpaint_frame = (
            lambda frame, mask, method=None, radius=3, quality_level=3: frame.copy()
        )
        handler.process_frame(
            _create_test_frame(),
            {
                "auto_detect": False,
                "user_mask": [(1, 1, 10, 10)],
            },
        )

    low_quality, high_quality = profiles
    assert low_quality["smooth_blur_radius"] < high_quality["smooth_blur_radius"]
    assert low_quality["blend_ratio"] < high_quality["blend_ratio"]
    assert low_quality["enhance_contrast"] < high_quality["enhance_contrast"]


def test_ai_handler_passes_configured_inpainting_model_path_to_dl_inpainter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 修复启用时应把配置中的权重路径真实传给深度学习修复器。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    dl_inpainter_module = sys.modules["app.core.ai.dl_inpainter"]
    torch_module.cuda.is_available = lambda: True

    model_path = tmp_path / "stub-unet.pth"
    model_path.write_bytes(b"stub")

    handler = ai_handler_cls(
        config=_build_test_config(str(model_path)),
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
        },
    )

    assert handler.load_models() is True
    assert dl_inpainter_module.last_load_model_path == str(model_path)
    assert handler.use_gpu_inpainting is True
    assert handler.dl_inpainter is not None


def test_ai_handler_falls_back_to_opencv_when_inpainting_model_path_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未配置 GPU 修复权重时应明确降级到 OpenCV，而不是继续走随机初始化成功路径。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    dl_inpainter_module = sys.modules["app.core.ai.dl_inpainter"]
    torch_module.cuda.is_available = lambda: True

    handler = ai_handler_cls(
        config=_build_test_config(""),
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
        },
    )
    captured = {}

    def fake_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        captured["method"] = method
        return frame.copy()

    handler.image_inpainter.inpaint_frame = fake_inpaint

    assert handler.load_models() is True
    assert dl_inpainter_module.last_load_model_path is None
    assert handler.use_gpu_inpainting is False

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert captured["method"] == "auto"
    assert info["inpainting_backend"] == "opencv"
    assert info["gpu_inpainting_requested"] is True
    assert info["gpu_inpainting_fallback_reason"] == "missing_inpainting_model_path"


def test_ai_handler_passes_gpu_profile_params_to_dl_inpainter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 路径启用时应把修复半径和质量真实传给深度学习修复器。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    dl_inpainter_module = sys.modules["app.core.ai.dl_inpainter"]
    torch_module.cuda.is_available = lambda: True

    model_path = tmp_path / "stub-unet.pth"
    model_path.write_bytes(b"stub")

    handler = ai_handler_cls(
        config=_build_test_config(str(model_path)),
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
            "quality_level": 5,
            "inpaint_radius": 7,
        },
    )

    assert handler.load_models() is True

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert dl_inpainter_module.last_inpaint_kwargs["radius"] == 7
    assert dl_inpainter_module.last_inpaint_kwargs["quality_level"] == 5
    assert info["inpainting_backend"] == "gpu_deep_learning_unet"
    assert info["gpu_inpainting_profile"]["requested_radius"] == 7
    assert info["gpu_inpainting_profile"]["quality_level"] == 5


def test_ai_handler_does_not_report_gpu_success_when_dl_inpainting_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 修复执行失败时，processing_info 不应误报成功后端。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    model_path = tmp_path / "stub-unet.pth"
    model_path.write_bytes(b"stub")

    handler = ai_handler_cls(
        config=_build_test_config(str(model_path)),
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
            "quality_level": 4,
            "inpaint_radius": 6,
        },
    )
    assert handler.load_models() is True

    def raise_inpaint_error(frame, mask, radius=3, quality_level=3, profile=None):
        raise RuntimeError("gpu inpaint failed")

    handler.dl_inpainter.inpaint_frame = raise_inpaint_error

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["inpainting_backend"] is None
    assert info["inpainting_method"] is None
    assert info["gpu_inpainting_profile"] is None


def test_ai_handler_reports_gpu_oom_retry_info(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 路径发生 OOM 重试后应把重试观测真实写入 processing_info。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    model_path = tmp_path / "stub-unet.pth"
    model_path.write_bytes(b"stub")

    handler = ai_handler_cls(
        config=_build_test_config(str(model_path)),
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
            "quality_level": 5,
            "inpaint_radius": 7,
        },
    )
    assert handler.load_models() is True

    def fake_inpaint(frame, mask, radius=3, quality_level=3, profile=None):
        handler.dl_inpainter.last_profile_used = {
            "requested_radius": radius,
            "quality_level": quality_level,
            "mask_expand_px": 8,
            "mask_feather_px": 5,
            "blend_ratio": 0.72,
            "resize_limit": 768,
        }
        handler.dl_inpainter.last_retry_info = {"applied": True, "count": 1, "reason": "oom"}
        return frame.copy()

    handler.dl_inpainter.inpaint_frame = fake_inpaint

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["inpainting_backend"] == "gpu_deep_learning_unet"
    assert info["gpu_inpainting_profile"]["resize_limit"] == 768
    assert info["gpu_inpainting_retry"] == {"applied": True, "count": 1, "reason": "oom"}
