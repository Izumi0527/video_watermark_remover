"""DeepLearningInpainter 的 GPU profile 单元测试。"""

import importlib
import sys
import types

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


def _load_dl_inpainter_module(monkeypatch: pytest.MonkeyPatch):
    """注入轻量 torch 依赖后再导入 dl_inpainter，避免真实 DLL 依赖。"""
    torch_module = types.ModuleType("torch")
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.device = lambda name: types.SimpleNamespace(type=name)
    torch_module.Tensor = object
    monkeypatch.setitem(sys.modules, "torch", torch_module)

    nn_module = types.ModuleType("torch.nn")

    class _DummyModule:
        def __init__(self, *args, **kwargs):
            pass

    nn_module.Module = _DummyModule
    nn_module.Sequential = lambda *args, **kwargs: None
    nn_module.Conv2d = _DummyModule
    nn_module.BatchNorm2d = _DummyModule
    nn_module.ReLU = _DummyModule
    nn_module.ConvTranspose2d = _DummyModule
    nn_module.MaxPool2d = _DummyModule
    monkeypatch.setitem(sys.modules, "torch.nn", nn_module)
    torch_module.nn = nn_module

    monkeypatch.delitem(sys.modules, "app.core.ai.dl_inpainter", raising=False)
    return importlib.import_module("app.core.ai.dl_inpainter")


def _create_mask() -> "np.ndarray":
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[28:36, 28:36] = 255
    return mask


def test_build_gpu_profile_quality_level_affects_resize_limit_and_blend_ratio(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module = _load_dl_inpainter_module(monkeypatch)
    inpainter = dl_module.DeepLearningInpainter(device="cpu")

    low_profile = inpainter._build_inpainting_profile((1080, 1920, 3), radius=3, quality_level=1)
    high_profile = inpainter._build_inpainting_profile((1080, 1920, 3), radius=3, quality_level=5)

    assert low_profile.resize_limit < high_profile.resize_limit
    assert low_profile.blend_ratio < high_profile.blend_ratio
    assert low_profile.mask_feather_px < high_profile.mask_feather_px


def test_build_gpu_profile_radius_affects_mask_expand_and_feather(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module = _load_dl_inpainter_module(monkeypatch)
    inpainter = dl_module.DeepLearningInpainter(device="cpu")

    small_radius = inpainter._build_inpainting_profile((720, 1280, 3), radius=2, quality_level=3)
    large_radius = inpainter._build_inpainting_profile((720, 1280, 3), radius=8, quality_level=3)

    assert small_radius.mask_expand_px < large_radius.mask_expand_px
    assert small_radius.mask_feather_px < large_radius.mask_feather_px


def test_prepare_mask_uses_profile_to_expand_mask_context(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module = _load_dl_inpainter_module(monkeypatch)
    inpainter = dl_module.DeepLearningInpainter(device="cpu")
    mask = _create_mask()

    conservative_profile = inpainter._build_inpainting_profile(
        (64, 64, 3), radius=1, quality_level=1
    )
    aggressive_profile = inpainter._build_inpainting_profile((64, 64, 3), radius=8, quality_level=5)

    conservative_mask = inpainter._prepare_mask(mask, conservative_profile)
    aggressive_mask = inpainter._prepare_mask(mask, aggressive_profile)

    assert np.count_nonzero(aggressive_mask) > np.count_nonzero(conservative_mask)


def test_blend_with_original_respects_profile_blend_ratio(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module = _load_dl_inpainter_module(monkeypatch)
    inpainter = dl_module.DeepLearningInpainter(device="cpu")
    original = np.zeros((16, 16, 3), dtype=np.uint8)
    generated = np.full((16, 16, 3), 255, dtype=np.uint8)
    prepared_mask = np.full((16, 16), 255, dtype=np.uint8)

    low_profile = inpainter._build_inpainting_profile((16, 16, 3), radius=2, quality_level=1)
    high_profile = inpainter._build_inpainting_profile((16, 16, 3), radius=2, quality_level=5)

    low_result = inpainter._blend_with_original(generated, original, prepared_mask, low_profile)
    high_result = inpainter._blend_with_original(generated, original, prepared_mask, high_profile)

    assert int(low_result.mean()) < int(high_result.mean())
