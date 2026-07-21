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


class _SequenceDetector:
    """按顺序返回检测结果，用于验证关键帧检测与中间帧复用。"""

    def __init__(self, masks: list[np.ndarray]):
        self._masks = [mask.copy() for mask in masks]
        self.call_count = 0

    def detect_watermark(self, frame: np.ndarray) -> np.ndarray:
        _ = frame
        index = min(self.call_count, len(self._masks) - 1)
        self.call_count += 1
        return self._masks[index].copy()


class _SequenceBatchDetector:
    """同时支持单帧与批量检测的顺序检测桩。"""

    def __init__(self, masks: list[np.ndarray]):
        self._masks = [mask.copy() for mask in masks]
        self._cursor = 0
        self.batch_calls = 0
        self.single_calls = 0

    def _next_mask(self) -> np.ndarray:
        index = min(self._cursor, len(self._masks) - 1)
        self._cursor += 1
        return self._masks[index].copy()

    def detect_batch(self, frames: list[np.ndarray]) -> list[np.ndarray]:
        self.batch_calls += 1
        return [self._next_mask() for _ in frames]

    def detect_watermark(self, frame: np.ndarray) -> np.ndarray:
        _ = frame
        self.single_calls += 1
        return self._next_mask()


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
    handler.last_effective_quality_level = None
    handler.last_effective_inpaint_radius = None
    handler.last_gpu_inpainting_runtime_error = None
    handler.device = "cpu"
    handler.watermark_detector = detector
    handler.inpaint_frame = lambda frame, _mask: frame.copy()
    return handler


def _create_test_frame() -> np.ndarray:
    return np.zeros((48, 64, 3), dtype=np.uint8)


def _create_detected_mask() -> np.ndarray:
    mask = np.zeros((48, 64), dtype=np.uint8)
    mask[20:30, 28:42] = 255
    return mask


def _create_shifted_detected_mask() -> np.ndarray:
    mask = np.zeros((48, 64), dtype=np.uint8)
    mask[20:30, 30:44] = 255
    return mask


def _create_far_shifted_detected_mask() -> np.ndarray:
    mask = np.zeros((48, 64), dtype=np.uint8)
    mask[20:30, 42:56] = 255
    return mask


def _build_test_config(lama_model_path: str = "") -> configparser.ConfigParser:
    """构造仅包含 LaMa 模型路径的测试配置。"""
    config = configparser.ConfigParser()
    config["Models"] = {"lama_model_path": lama_model_path}
    return config


class _FakeDeepBackend:
    """LaMa 深度后端桩：记录调用并通过 trace 回传观测字段。"""

    backend_id = "lama"

    def __init__(self, model_path=None):
        self.model_path = model_path
        self.loaded_model_path = None
        self.loaded_asset_ref = None
        self.last_inpaint_kwargs = None
        self.last_runtime_profile = None
        self.inpaint_frame_impl = None
        self.extra_trace = {}
        self._trace = {}

    def load(self):
        if not self.model_path:
            self._trace = {"load_failure_reason": "missing_lama_model_path"}
            return False
        self.loaded_model_path = self.model_path
        self.loaded_asset_ref = self.model_path
        return True

    def set_runtime_profile(self, profile):
        self.last_runtime_profile = dict(profile)

    def inpaint_frame(self, frame, mask, inpaint_radius=3, quality_level=3, opencv_method="auto"):
        self.last_inpaint_kwargs = {
            "radius": inpaint_radius,
            "quality_level": quality_level,
        }
        if self.inpaint_frame_impl is not None:
            return self.inpaint_frame_impl(frame, mask, inpaint_radius, quality_level)
        self._trace = {
            "inpainting_backend": "lama",
            "inpainting_method": "lama",
            "gpu_inpainting_profile": {
                "requested_radius": inpaint_radius,
                "quality_level": quality_level,
            },
            **self.extra_trace,
        }
        return frame.copy()

    def get_last_trace(self):
        return dict(self._trace)


def _install_fake_deep_backend_factory(monkeypatch: pytest.MonkeyPatch, created: dict) -> None:
    """把 ai_handler 的深度后端工厂替换为 LaMa 桩，OpenCV 请求仍走真实工厂。"""
    ai_handler_module = sys.modules["app.core.ai.ai_handler"]
    real_factory = ai_handler_module.create_inpainting_backend

    def fake_factory(requested_backend, **kwargs):
        if str(requested_backend).strip().lower() == "lama":
            backend = _FakeDeepBackend(model_path=kwargs.get("model_path"))
            created["backend"] = backend
            created["model_path"] = kwargs.get("model_path")
            return backend
        return real_factory(requested_backend, **kwargs)

    monkeypatch.setattr(ai_handler_module, "create_inpainting_backend", fake_factory)


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
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True
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


def test_ai_handler_consumes_temporal_tracking_controls_from_built_ai_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """builder 下沉的新时序参数应被 AIHandler 与 TemporalCoordinator 一致消费。"""
    ai_handler_cls, ai_params_builder_cls = _load_test_targets(monkeypatch)
    builder = ai_params_builder_cls()

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(auto_mode=True),
        advanced_params={
            "enable_mask_tracking": True,
            "mask_tracking_interval": 4,
            "mask_tracking_max_missing_detections": 2,
            "mask_tracking_motion_iou_threshold": 0.28,
            "mask_tracking_scene_shift_confirmation_frames": 3,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    handler = ai_handler_cls(_build_test_config(), ai_params)

    assert ai_params["mask_tracking_max_missing_detections"] == 2
    assert ai_params["mask_tracking_motion_iou_threshold"] == pytest.approx(0.28)
    assert ai_params["mask_tracking_scene_shift_confirmation_frames"] == 3
    assert handler.mask_tracking_max_missing_detections == 2
    assert handler.mask_tracking_motion_iou_threshold == pytest.approx(0.28)
    assert handler.mask_tracking_scene_shift_confirmation_frames == 3
    assert handler.temporal_coordinator.max_missing_detections == 2
    assert handler.temporal_coordinator.motion_redetect_iou_threshold == pytest.approx(0.28)
    assert handler.temporal_coordinator.scene_shift_confirmation_frames == 3


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


def test_ai_handler_uses_temporal_coordinator_for_mask_tracking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """开启掩码跟踪后，AIHandler 应通过时序协调器复用非关键帧掩码。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _SequenceDetector([_create_detected_mask(), _create_shifted_detected_mask()])
    handler = _build_lightweight_ai_handler(detector, ai_handler_cls)
    handler.enable_mask_tracking = True
    handler.mask_tracking_interval = 3
    handler.mask_tracking_warmup_frames = 0

    frame = _create_test_frame()
    params = {
        "auto_detect": True,
        "user_mask": None,
        "detection_sensitivity": 0.5,
    }

    _, first_info = handler.process_frame(frame, params)
    _, second_info = handler.process_frame(frame, params)
    _, third_info = handler.process_frame(frame, params)
    _, fourth_info = handler.process_frame(frame, params)

    assert hasattr(handler, "temporal_coordinator")
    assert first_info["detection_method"] == "automatic_yolo"
    assert second_info["detection_method"] == "mask_tracking_reuse_last"
    assert third_info["detection_method"] == "mask_tracking_reuse_last"
    assert fourth_info["detection_method"] == "automatic_yolo"
    assert detector.call_count == 2


def test_ai_handler_long_sequence_keeps_keyframe_and_reuse_pattern(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """长序列单帧处理时，应持续保持关键帧检测与中间帧复用节奏。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _SequenceDetector(
        [
            _create_detected_mask(),
            _create_shifted_detected_mask(),
            _create_detected_mask(),
        ]
    )
    handler = _build_lightweight_ai_handler(detector, ai_handler_cls)
    handler.enable_mask_tracking = True
    handler.mask_tracking_interval = 3
    handler.mask_tracking_warmup_frames = 0

    params = {
        "auto_detect": True,
        "user_mask": None,
        "detection_sensitivity": 0.5,
    }

    detection_methods = []
    for _ in range(7):
        _, info = handler.process_frame(_create_test_frame(), params)
        detection_methods.append(info["detection_method"])

    assert detection_methods == [
        "automatic_yolo",
        "mask_tracking_reuse_last",
        "mask_tracking_reuse_last",
        "automatic_yolo",
        "mask_tracking_reuse_last",
        "mask_tracking_reuse_last",
        "automatic_yolo",
    ]
    assert detector.call_count == 3


def test_ai_handler_batch_cold_start_keeps_conservative_detection_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """冷启动批次应保持保守检测，不在同批内因前帧稳定而回收后续检测位点。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _SequenceBatchDetector(
        [
            _create_detected_mask(),
            _create_shifted_detected_mask(),
            _create_detected_mask(),
            _create_shifted_detected_mask(),
        ]
    )
    handler = ai_handler_cls(
        config=None,
        ai_params={
            "use_gpu_inpainting": False,
            "device": "cpu",
            "enable_mask_tracking": True,
            "mask_tracking_interval": 3,
            "mask_tracking_warmup_frames": 1,
        },
    )
    handler.watermark_detector = detector

    params = {
        "auto_detect": True,
        "user_mask": None,
        "detection_sensitivity": 0.5,
    }

    first_batch_results = handler.process_frames_batch(
        [_create_test_frame(), _create_test_frame(), _create_test_frame()],
        params,
    )
    first_batch_methods = [info["detection_method"] for _, info in first_batch_results]

    second_batch_results = handler.process_frames_batch(
        [_create_test_frame(), _create_test_frame(), _create_test_frame()],
        params,
    )
    second_batch_methods = [info["detection_method"] for _, info in second_batch_results]

    assert first_batch_methods == [
        "automatic_yolo",
        "automatic_yolo",
        "automatic_yolo",
    ]
    assert second_batch_methods == [
        "automatic_yolo",
        "mask_tracking_reuse_last",
        "mask_tracking_reuse_last",
    ]
    assert detector.batch_calls == 2
    assert detector.single_calls == 0


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


def test_ai_handler_passes_configured_lama_model_path_to_deep_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 修复启用时应把配置中的模型路径真实传给深度修复后端。"""
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
        },
    )
    _install_fake_deep_backend_factory(monkeypatch, created)

    assert handler.load_models() is True
    assert created["model_path"] == str(model_path)
    assert handler.use_gpu_inpainting is True
    assert handler.deep_inpainting_backend is not None
    assert handler.loaded_inpainting_model_path == str(model_path)


def test_ai_handler_falls_back_to_opencv_when_lama_model_path_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未配置 LaMa 模型路径时应明确降级到 OpenCV。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    torch_module = sys.modules["torch"]
    torch_module.cuda.is_available = lambda: True

    created: dict = {}
    handler = ai_handler_cls(
        config=_build_test_config(""),
        ai_params={
            "use_gpu_inpainting": True,
            "device": "cuda",
        },
    )
    _install_fake_deep_backend_factory(monkeypatch, created)
    # 仓库可能存在 models/big-lama.pt 候选文件，显式清空以模拟"未配置"场景
    handler.configured_lama_model_path = None
    handler.configured_inpainting_asset_ref = None
    captured = {}

    def fake_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        captured["method"] = method
        return frame.copy()

    handler.image_inpainter.inpaint_frame = fake_inpaint

    assert handler.load_models() is True
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
    assert info["gpu_inpainting_fallback_reason"] == "missing_lama_model_path"


def test_ai_handler_passes_gpu_profile_params_to_deep_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 路径启用时应把修复半径和质量真实传给深度修复后端。"""
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
            "quality_level": 5,
            "inpaint_radius": 7,
        },
    )
    _install_fake_deep_backend_factory(monkeypatch, created)

    assert handler.load_models() is True

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    backend = created["backend"]
    assert backend.last_inpaint_kwargs["radius"] == 7
    assert backend.last_inpaint_kwargs["quality_level"] == 5
    assert info["inpainting_backend"] == "lama"
    assert info["gpu_inpainting_profile"]["requested_radius"] == 7
    assert info["gpu_inpainting_profile"]["quality_level"] == 5


def test_ai_handler_falls_back_to_opencv_when_deep_inpainting_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 修复执行失败时，应降级到 OpenCV 且不误报 GPU 成功。"""
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

    def raise_inpaint_error(frame, mask, radius, quality_level):
        raise RuntimeError("gpu inpaint failed")

    created["backend"].inpaint_frame_impl = raise_inpaint_error
    captured = {}

    def fallback_inpaint(frame, mask, method=None, radius=3, quality_level=3):
        captured["method"] = method
        captured["radius"] = radius
        captured["quality_level"] = quality_level
        handler.image_inpainter.last_quality_level = 2
        handler.image_inpainter.last_effective_radius = 9
        handler.image_inpainter.last_method_used = "telea"
        return frame.copy()

    handler.image_inpainter.inpaint_frame = fallback_inpaint

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
    assert handler.use_gpu_inpainting is False
    assert info["inpainting_backend"] == "opencv"
    assert info["inpainting_method"] == "telea"
    assert info["gpu_inpainting_profile"] is None
    assert info["gpu_inpainting_fallback_reason"] == "lama_runtime_exception"
    assert "gpu inpaint failed" in info["gpu_inpainting_runtime_error"]
    assert info["loaded_inpainting_model_path"] == str(model_path)
    assert info["quality_level"] == 4
    assert info["requested_quality_level"] == 4
    assert info["effective_quality_level"] == 2
    assert info["effective_inpaint_radius"] == 9


def test_ai_handler_reports_effective_quality_level_from_gpu_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 路径成功时，应把 trace 中的实际质量等级写入 processing_info。"""
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
            "quality_level": 9,
            "inpaint_radius": 6,
        },
    )
    _install_fake_deep_backend_factory(monkeypatch, created)
    assert handler.load_models() is True

    created["backend"].extra_trace = {
        "effective_quality_level": 5,
        "effective_inpaint_radius": 6,
    }

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["quality_level"] == 9
    assert info["requested_quality_level"] == 9
    assert info["effective_quality_level"] == 5
    assert info["effective_inpaint_radius"] == 6
    assert info["inpainting_backend"] == "lama"


def test_ai_handler_reports_gpu_oom_retry_info(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """GPU 路径发生 OOM 重试后应把重试观测真实写入 processing_info。"""
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
            "quality_level": 5,
            "inpaint_radius": 7,
        },
    )
    _install_fake_deep_backend_factory(monkeypatch, created)
    assert handler.load_models() is True

    created["backend"].extra_trace = {
        "gpu_inpainting_profile": {
            "requested_radius": 7,
            "quality_level": 5,
            "resize_limit": 768,
        },
        "gpu_inpainting_retry": {"applied": True, "count": 1, "reason": "oom"},
    }

    _, info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": False,
            "user_mask": [(1, 1, 10, 10)],
        },
    )

    assert info["inpainting_backend"] == "lama"
    assert info["gpu_inpainting_profile"]["resize_limit"] == 768
    assert info["gpu_inpainting_retry"] == {"applied": True, "count": 1, "reason": "oom"}


def test_ai_handler_reuses_temporal_mask_between_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """启用时序协调后，非关键帧应复用上一帧稳定掩码。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _DummyDetector(_create_detected_mask())
    handler = _build_lightweight_ai_handler(detector, ai_handler_cls)
    handler.enable_mask_tracking = True
    handler.mask_tracking_interval = 3
    handler.mask_tracking_warmup_frames = 0

    _, first_info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": True,
            "user_mask": None,
            "detection_sensitivity": 0.5,
        },
    )
    _, second_info = handler.process_frame(
        _create_test_frame(),
        {
            "auto_detect": True,
            "user_mask": None,
            "detection_sensitivity": 0.5,
        },
    )

    assert detector.call_count == 1
    assert first_info["detection_method"] == "automatic_yolo"
    assert second_info["detection_method"] == "mask_tracking_reuse_last"


def test_ai_handler_reset_runtime_state_clears_temporal_tracking_between_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """跨任务 reset 后，新任务首帧必须重新检测，不能复用上一任务掩码。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _SequenceDetector([_create_detected_mask(), _create_shifted_detected_mask()])
    handler = _build_lightweight_ai_handler(detector, ai_handler_cls)
    handler.enable_mask_tracking = True
    handler.mask_tracking_interval = 3
    handler.mask_tracking_warmup_frames = 0

    params = {
        "auto_detect": True,
        "user_mask": None,
        "detection_sensitivity": 0.5,
    }

    _, first_info = handler.process_frame(_create_test_frame(), params)
    _, second_info = handler.process_frame(_create_test_frame(), params)

    assert first_info["detection_method"] == "automatic_yolo"
    assert second_info["detection_method"] == "mask_tracking_reuse_last"
    assert detector.call_count == 1

    handler.reset_runtime_state_for_new_task()

    assert handler._mask_tracking_next_frame_index == 0
    assert handler.temporal_coordinator.stable_hits == 0
    assert handler.temporal_coordinator.get_stored_mask_copy() is None

    _, third_info = handler.process_frame(_create_test_frame(), params)

    assert third_info["detection_method"] == "automatic_yolo"
    assert detector.call_count == 2


def test_ai_handler_forces_next_detection_after_large_temporal_shift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """关键帧检测到大位移后，下一帧应强制重检以避免直接复用旧时序状态。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _SequenceDetector(
        [
            _create_detected_mask(),
            _create_far_shifted_detected_mask(),
            _create_far_shifted_detected_mask(),
        ]
    )
    handler = _build_lightweight_ai_handler(detector, ai_handler_cls)
    handler.enable_mask_tracking = True
    handler.mask_tracking_interval = 3
    handler.mask_tracking_warmup_frames = 0
    handler.mask_tracking_motion_iou_threshold = 0.2

    params = {
        "auto_detect": True,
        "user_mask": None,
        "detection_sensitivity": 0.5,
    }

    detection_methods = []
    for _ in range(6):
        _, info = handler.process_frame(_create_test_frame(), params)
        detection_methods.append(info["detection_method"])

    assert detection_methods == [
        "automatic_yolo",
        "mask_tracking_reuse_last",
        "mask_tracking_reuse_last",
        "automatic_yolo",
        "automatic_yolo",
        "mask_tracking_reuse_last",
    ]
    assert detector.call_count == 3


def test_ai_handler_forces_redetection_after_large_mask_shift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """关键帧检测到大位移后，下一帧应立即重检，避免直接复用不稳定新掩码。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)
    detector = _SequenceDetector(
        [
            _create_detected_mask(),
            _create_far_shifted_detected_mask(),
            _create_far_shifted_detected_mask(),
        ]
    )
    handler = _build_lightweight_ai_handler(detector, ai_handler_cls)
    handler.enable_mask_tracking = True
    handler.mask_tracking_interval = 3
    handler.mask_tracking_warmup_frames = 0

    params = {
        "auto_detect": True,
        "user_mask": None,
        "detection_sensitivity": 0.5,
    }

    methods = []
    for _ in range(5):
        _, info = handler.process_frame(_create_test_frame(), params)
        methods.append(info["detection_method"])

    assert methods == [
        "automatic_yolo",
        "mask_tracking_reuse_last",
        "mask_tracking_reuse_last",
        "automatic_yolo",
        "automatic_yolo",
    ]
    assert detector.call_count == 3


def test_builder_passes_temporal_tracking_params_to_ai_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Builder 生成的时序参数应完整传递到 AIHandler 与 TemporalCoordinator。"""
    ai_handler_cls, ai_params_builder_cls = _load_test_targets(monkeypatch)
    builder = ai_params_builder_cls()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: False)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(auto_mode=True),
        advanced_params={
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "enable_mask_tracking": True,
            "mask_tracking_interval": 3,
            "mask_tracking_max_missing_detections": 2,
            "mask_tracking_motion_iou_threshold": 0.35,
            "mask_tracking_scene_shift_confirmation_frames": 4,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    handler = ai_handler_cls(
        config=None,
        ai_params=ai_params,
    )

    assert handler.mask_tracking_max_missing_detections == 2
    assert handler.mask_tracking_motion_iou_threshold == pytest.approx(0.35, rel=1e-6)
    assert handler.mask_tracking_scene_shift_confirmation_frames == 4
    assert handler.temporal_coordinator.max_missing_detections == 2
    assert handler.temporal_coordinator.motion_redetect_iou_threshold == pytest.approx(
        0.35, rel=1e-6
    )
    assert handler.temporal_coordinator.scene_shift_confirmation_frames == 4


def test_ai_handler_configures_temporal_coordinator_with_tracking_runtime_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AIHandler 初始化时应把新增时序参数下沉到 TemporalCoordinator。"""
    ai_handler_cls, _ = _load_test_targets(monkeypatch)

    handler = ai_handler_cls(
        config=None,
        ai_params={
            "use_gpu_inpainting": False,
            "device": "cpu",
            "enable_mask_tracking": True,
            "mask_tracking_interval": 5,
            "mask_tracking_warmup_frames": 1,
            "mask_tracking_max_missing_detections": 2,
            "mask_tracking_motion_iou_threshold": 0.27,
            "mask_tracking_scene_shift_confirmation_frames": 4,
        },
    )

    assert handler.mask_tracking_max_missing_detections == 2
    assert handler.mask_tracking_motion_iou_threshold == pytest.approx(0.27, rel=1e-6)
    assert handler.mask_tracking_scene_shift_confirmation_frames == 4
    assert handler.temporal_coordinator.max_missing_detections == 2
    assert handler.temporal_coordinator.motion_redetect_iou_threshold == pytest.approx(
        0.27,
        rel=1e-6,
    )
    assert handler.temporal_coordinator.scene_shift_confirmation_frames == 4
