"""DeepLearningInpainter 的 GPU batch 吞吐单元测试。"""

import importlib
import sys
import types

import pytest

pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


def _load_dl_inpainter_module(monkeypatch: pytest.MonkeyPatch):
    """注入轻量 torch 依赖后导入 dl_inpainter，避免真实 GPU / DLL 依赖。"""
    torch_module = types.ModuleType("torch")
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.device = lambda name: types.SimpleNamespace(type=name)
    torch_module.Tensor = object

    class _NoGrad:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    torch_module.no_grad = lambda: _NoGrad()
    torch_module.cat = lambda tensors, dim=0: np.concatenate(tensors, axis=dim)
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


class _CountingModel:
    """记录前向次数的轻量模型桩。"""

    def __init__(self) -> None:
        self.forward_call_count = 0

    def __call__(self, tensor):
        self.forward_call_count += 1
        batch_size = tensor.shape[0]
        height = tensor.shape[2]
        width = tensor.shape[3]
        return np.zeros((batch_size, 3, height, width), dtype=np.float32)


class _FailingBatchModel(_CountingModel):
    """仅在 batch 大于 1 时模拟前向失败。"""

    def __call__(self, tensor):
        self.forward_call_count += 1
        if tensor.shape[0] > 1:
            raise RuntimeError("batch forward failed")
        return np.zeros((1, 3, tensor.shape[2], tensor.shape[3]), dtype=np.float32)


class _SelectiveFailingGroupModel(_CountingModel):
    """只让指定推理尺寸的 batch 组失败，便于验证逐组回退。"""

    def __init__(self, failing_height: int) -> None:
        super().__init__()
        self.failing_height = failing_height

    def __call__(self, tensor):
        self.forward_call_count += 1
        batch_size = tensor.shape[0]
        height = tensor.shape[2]
        width = tensor.shape[3]
        if batch_size > 1 and height == self.failing_height:
            raise RuntimeError("group batch forward failed")
        return np.zeros((batch_size, 3, height, width), dtype=np.float32)


class _OOMRetryGroupModel(_CountingModel):
    """指定高度的分组首次抛 OOM，第二次成功。"""

    def __init__(self, failing_height: int) -> None:
        super().__init__()
        self.failing_height = failing_height
        self.failed_heights: set[int] = set()

    def __call__(self, tensor):
        self.forward_call_count += 1
        batch_size = tensor.shape[0]
        height = tensor.shape[2]
        width = tensor.shape[3]
        if batch_size > 1 and height == self.failing_height and height not in self.failed_heights:
            self.failed_heights.add(height)
            raise RuntimeError("CUDA out of memory during grouped batch inference")
        return np.zeros((batch_size, 3, height, width), dtype=np.float32)


def _create_frame(height: int, width: int, fill_value: int = 127) -> "np.ndarray":
    return np.full((height, width, 3), fill_value, dtype=np.uint8)


def _create_mask(height: int, width: int) -> "np.ndarray":
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[height // 4 : height // 2, width // 4 : width // 2] = 255
    return mask


def _create_empty_mask(height: int, width: int) -> "np.ndarray":
    return np.zeros((height, width), dtype=np.uint8)


def _build_inpainter(monkeypatch: pytest.MonkeyPatch):
    dl_module = _load_dl_inpainter_module(monkeypatch)
    model = _CountingModel()
    inpainter = dl_module.DeepLearningInpainter(device="cpu")
    inpainter.model = model

    monkeypatch.setattr(
        inpainter,
        "_preprocess",
        lambda frame_rgb, mask: np.zeros(
            (1, 4, frame_rgb.shape[0], frame_rgb.shape[1]),
            dtype=np.float32,
        ),
    )
    monkeypatch.setattr(
        inpainter,
        "_postprocess",
        lambda output_tensor, original_rgb, prepared_mask, profile: original_rgb.copy(),
    )
    return dl_module, inpainter, model


def test_inpaint_batch_uses_single_model_forward_for_same_shape_and_profile(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module, inpainter, model = _build_inpainter(monkeypatch)

    frames = [_create_frame(64, 64), _create_frame(64, 64)]
    masks = [_create_mask(64, 64), _create_mask(64, 64)]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 2
    assert all(result.shape == frame.shape for result, frame in zip(results, frames))
    assert model.forward_call_count == 1
    assert inpainter.last_batch_execution_mode == "true_batch"


def test_inpaint_batch_falls_back_when_input_shapes_differ(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module, inpainter, model = _build_inpainter(monkeypatch)

    frames = [_create_frame(64, 64), _create_frame(32, 32)]
    masks = [_create_mask(64, 64), _create_mask(32, 32)]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 2
    assert model.forward_call_count == 2
    assert inpainter.last_batch_execution_mode == "fallback_sequential"


def test_inpaint_batch_falls_back_when_profiles_differ(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module, inpainter, model = _build_inpainter(monkeypatch)

    frames = [_create_frame(64, 64), _create_frame(64, 64)]
    masks = [_create_mask(64, 64), _create_mask(64, 64)]
    different_profile = dl_module.GPUInpaintingProfile(
        requested_radius=7,
        quality_level=5,
        mask_expand_px=11,
        mask_feather_px=8,
        blend_ratio=0.92,
        resize_limit=1152,
    )

    results = inpainter.inpaint_batch(
        frames,
        masks,
        radius=3,
        quality_level=4,
        profiles=[None, different_profile],
    )

    assert len(results) == 2
    assert model.forward_call_count == 2
    assert inpainter.last_batch_execution_mode == "fallback_sequential"


def test_inpaint_batch_falls_back_when_true_batch_forward_raises(
    monkeypatch: pytest.MonkeyPatch,
):
    _, inpainter, _ = _build_inpainter(monkeypatch)
    failing_model = _FailingBatchModel()
    inpainter.model = failing_model

    frames = [_create_frame(64, 64), _create_frame(64, 64)]
    masks = [_create_mask(64, 64), _create_mask(64, 64)]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 2
    assert failing_model.forward_call_count == 3
    assert inpainter.last_batch_execution_mode == "fallback_sequential"


def test_inpaint_batch_keeps_original_output_shapes_after_true_batch(
    monkeypatch: pytest.MonkeyPatch,
):
    _, inpainter, model = _build_inpainter(monkeypatch)
    frames = [_create_frame(720, 1280), _create_frame(1080, 1920)]
    masks = [_create_mask(720, 1280), _create_mask(1080, 1920)]

    monkeypatch.setattr(
        inpainter,
        "_resize_for_inference",
        lambda frame_rgb, prepared_mask, profile: (
            np.zeros((540, 960, 3), dtype=np.uint8),
            np.zeros((540, 960), dtype=np.uint8),
        ),
    )
    monkeypatch.setattr(
        inpainter,
        "_postprocess",
        lambda output_tensor, original_rgb, prepared_mask, profile: original_rgb,
    )

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert model.forward_call_count == 1
    assert results[0].shape == frames[0].shape
    assert results[1].shape == frames[1].shape


def test_inpaint_batch_groups_compatible_items_by_inference_shape(
    monkeypatch: pytest.MonkeyPatch,
):
    _, inpainter, model = _build_inpainter(monkeypatch)
    frames = [
        _create_frame(64, 64, fill_value=10),
        _create_frame(64, 64, fill_value=20),
        _create_frame(32, 32, fill_value=30),
        _create_frame(32, 32, fill_value=40),
    ]
    masks = [
        _create_mask(64, 64),
        _create_mask(64, 64),
        _create_mask(32, 32),
        _create_mask(32, 32),
    ]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 4
    assert model.forward_call_count == 2
    assert [int(result[0, 0, 0]) for result in results] == [10, 20, 30, 40]
    assert inpainter.last_batch_execution_mode == "grouped_true_batch"


def test_inpaint_batch_groups_compatible_items_by_effective_profile(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module, inpainter, model = _build_inpainter(monkeypatch)
    frames = [
        _create_frame(64, 64, fill_value=10),
        _create_frame(64, 64, fill_value=20),
        _create_frame(64, 64, fill_value=30),
        _create_frame(64, 64, fill_value=40),
    ]
    masks = [
        _create_mask(64, 64),
        _create_mask(64, 64),
        _create_mask(64, 64),
        _create_mask(64, 64),
    ]
    higher_profile = dl_module.GPUInpaintingProfile(
        requested_radius=7,
        quality_level=5,
        mask_expand_px=11,
        mask_feather_px=8,
        blend_ratio=0.92,
        resize_limit=1152,
    )

    results = inpainter.inpaint_batch(
        frames,
        masks,
        radius=3,
        quality_level=4,
        profiles=[None, None, higher_profile, higher_profile],
    )

    assert len(results) == 4
    assert model.forward_call_count == 2
    assert [int(result[0, 0, 0]) for result in results] == [10, 20, 30, 40]
    assert inpainter.last_batch_execution_mode == "grouped_true_batch"


def test_inpaint_batch_uses_mixed_mode_when_empty_mask_blocks_one_group(
    monkeypatch: pytest.MonkeyPatch,
):
    _, inpainter, model = _build_inpainter(monkeypatch)
    frames = [
        _create_frame(64, 64, fill_value=10),
        _create_frame(64, 64, fill_value=20),
        _create_frame(64, 64, fill_value=30),
    ]
    masks = [
        _create_mask(64, 64),
        _create_empty_mask(64, 64),
        _create_mask(64, 64),
    ]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 3
    assert model.forward_call_count == 1
    assert [int(result[0, 0, 0]) for result in results] == [10, 20, 30]
    assert inpainter.last_batch_execution_mode == "mixed_grouped_batch"


def test_inpaint_batch_falls_back_only_for_failed_group(
    monkeypatch: pytest.MonkeyPatch,
):
    _, inpainter, _ = _build_inpainter(monkeypatch)
    model = _SelectiveFailingGroupModel(failing_height=64)
    inpainter.model = model
    frames = [
        _create_frame(64, 64, fill_value=10),
        _create_frame(64, 64, fill_value=20),
        _create_frame(32, 32, fill_value=30),
        _create_frame(32, 32, fill_value=40),
    ]
    masks = [
        _create_mask(64, 64),
        _create_mask(64, 64),
        _create_mask(32, 32),
        _create_mask(32, 32),
    ]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 4
    assert model.forward_call_count == 4
    assert [int(result[0, 0, 0]) for result in results] == [10, 20, 30, 40]
    assert inpainter.last_batch_execution_mode == "mixed_grouped_batch"


def test_inpaint_batch_reports_last_valid_input_profile_in_grouped_mode(
    monkeypatch: pytest.MonkeyPatch,
):
    dl_module, inpainter, model = _build_inpainter(monkeypatch)
    later_profile = dl_module.GPUInpaintingProfile(
        requested_radius=7,
        quality_level=5,
        mask_expand_px=11,
        mask_feather_px=8,
        blend_ratio=0.92,
        resize_limit=1152,
    )
    frames = [
        _create_frame(64, 64, fill_value=10),
        _create_frame(32, 32, fill_value=20),
        _create_frame(64, 64, fill_value=30),
    ]
    masks = [
        _create_mask(64, 64),
        _create_mask(32, 32),
        _create_mask(64, 64),
    ]

    results = inpainter.inpaint_batch(
        frames,
        masks,
        radius=3,
        quality_level=4,
        profiles=[None, later_profile, None],
    )

    expected_profile = inpainter._resolve_profile(
        (64, 64, 3), radius=3, quality_level=4, profile=None
    )

    assert len(results) == 3
    assert model.forward_call_count == 2
    assert inpainter.last_batch_execution_mode == "mixed_grouped_batch"
    assert inpainter.last_profile_used == expected_profile.to_dict()


def test_inpaint_batch_retries_group_with_conservative_profile_after_oom(
    monkeypatch: pytest.MonkeyPatch,
):
    _, inpainter, _ = _build_inpainter(monkeypatch)
    model = _OOMRetryGroupModel(failing_height=64)
    inpainter.model = model
    frames = [
        _create_frame(64, 64, fill_value=10),
        _create_frame(64, 64, fill_value=20),
        _create_frame(32, 32, fill_value=30),
        _create_frame(32, 32, fill_value=40),
    ]
    masks = [
        _create_mask(64, 64),
        _create_mask(64, 64),
        _create_mask(32, 32),
        _create_mask(32, 32),
    ]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=5)

    assert len(results) == 4
    assert model.forward_call_count == 3
    assert [int(result[0, 0, 0]) for result in results] == [10, 20, 30, 40]
    assert inpainter.last_batch_execution_mode == "grouped_true_batch"
    assert inpainter.last_retry_info == {"applied": True, "count": 1, "reason": "oom"}


def test_inpaint_batch_skips_true_batch_for_group_requiring_tile(
    monkeypatch: pytest.MonkeyPatch,
):
    _, inpainter, model = _build_inpainter(monkeypatch)
    frames = [_create_frame(64, 64, fill_value=10), _create_frame(64, 64, fill_value=20)]
    masks = [_create_mask(64, 64), _create_mask(64, 64)]
    true_batch_calls: list[int] = []

    monkeypatch.setattr(inpainter, "_requires_tiled_execution", lambda item: True)
    monkeypatch.setattr(
        inpainter,
        "_run_true_batch",
        lambda batch_items: true_batch_calls.append(len(batch_items)) or [],
    )

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=5)

    assert len(results) == 2
    assert model.forward_call_count == 2
    assert true_batch_calls == []
    assert inpainter.last_batch_execution_mode == "fallback_sequential"


def test_inpaint_batch_uses_mixed_mode_when_large_group_requires_tile(
    monkeypatch: pytest.MonkeyPatch,
):
    _, inpainter, model = _build_inpainter(monkeypatch)
    frames = [
        _create_frame(64, 64, fill_value=10),
        _create_frame(64, 64, fill_value=20),
        _create_frame(128, 128, fill_value=30),
        _create_frame(128, 128, fill_value=40),
    ]
    masks = [
        _create_mask(64, 64),
        _create_mask(64, 64),
        _create_mask(128, 128),
        _create_mask(128, 128),
    ]

    monkeypatch.setattr(
        inpainter,
        "_requires_tiled_execution",
        lambda item: item.inference_shape[0] == 128,
    )

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=5)

    assert len(results) == 4
    assert model.forward_call_count == 3
    assert [int(result[0, 0, 0]) for result in results] == [10, 20, 30, 40]
    assert inpainter.last_batch_execution_mode == "mixed_grouped_batch"
