#!/usr/bin/env python3
"""
YOLOWatermarkDetector bbox→mask 边界精修测试

目标：
- 自适应 padding 支持 x/y 方向独立扩展，避免长条检测框在短边方向被过度扩大
- 坐标 clamp 到图像边界（w-1/h-1），避免 off-by-one 越界导致的边缘偏移
"""

from __future__ import annotations

from configparser import ConfigParser

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


class _FakeTensor:
    """最小化张量适配层：满足 .detach().cpu().numpy() 链式调用。"""

    def __init__(self, arr):
        self._arr = np.asarray(arr, dtype=np.float32)

    def detach(self):  # noqa: D401
        return self

    def cpu(self):  # noqa: D401
        return self

    def numpy(self):  # noqa: D401
        return self._arr


class _FakeBoxes:
    """最小化 Boxes 适配层：满足 len(boxes) 与 boxes.xyxy 访问。"""

    def __init__(self, xyxy):
        self.xyxy = _FakeTensor(xyxy)

    def __len__(self):
        return int(self.xyxy.numpy().shape[0])


def _build_config(**yolo_overrides) -> ConfigParser:
    config = ConfigParser()
    config["Paths"] = {"default_model_dir": "./models"}
    config["YOLO"] = {
        "model_type": "yolo11x-watermark",
        "custom_model_path": "",
        # 关闭后处理，确保矩形边界可精确断言
        "mask_close_kernel": "0",
        "mask_erode_iterations": "0",
        "mask_dilate_iterations": "0",
    }
    for k, v in yolo_overrides.items():
        config["YOLO"][k] = str(v)
    return config


def _mask_bbox(mask) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask > 0)
    assert ys.size > 0 and xs.size > 0, "掩码应存在非零区域"
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _create_hollow_logo_mask():
    mask = np.zeros((64, 64), dtype=np.uint8)
    cv2.rectangle(mask, (18, 18), (46, 46), 255, 2)
    mask[18:22, 30:34] = 0
    return mask


def _create_small_hollow_logo_mask():
    mask = np.zeros((64, 64), dtype=np.uint8)
    cv2.rectangle(mask, (18, 18), (46, 46), 255, -1)
    cv2.rectangle(mask, (29, 29), (35, 35), 0, -1)
    mask[18:21, 31:34] = 0
    return mask


def test_boxes_to_mask_uses_anisotropic_padding():
    """
    长条检测框应在宽度方向扩张更明显，而不是用同一 padding 同时扩大宽/高。
    """
    from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: WPS433

    config = _build_config(
        mask_padding_px=1,
        mask_padding_ratio=0.1,
        mask_padding_max=100,
    )
    detector = YOLOWatermarkDetector(config=config, model_path="dummy.pt", device="cpu")

    # (x1, y1, x2, y2) 为浮点，内部会 floor/ceil
    boxes = _FakeBoxes([[10.2, 5.9, 110.1, 15.1]])
    mask = detector._boxes_to_mask(boxes, (50, 200, 3))

    # floor/ceil 后：x1=10,y1=5,x2=111,y2=16
    # pad_x=max(1, round(101*0.1)=10)=10, pad_y=max(1, round(11*0.1)=1)=1
    assert _mask_bbox(mask) == (0, 4, 121, 17)


def test_boxes_to_mask_clamps_to_image_bounds():
    """
    右/下边界应 clamp 到 w-1/h-1，避免 x2=w 或 y2=h 的 off-by-one。
    """
    from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: WPS433

    config = _build_config(
        mask_padding_px=0,
        mask_padding_ratio=0.0,
        mask_padding_max=0,
    )
    detector = YOLOWatermarkDetector(config=config, model_path="dummy.pt", device="cpu")

    boxes = _FakeBoxes([[55.3, 45.2, 59.9, 49.9]])
    mask = detector._boxes_to_mask(boxes, (50, 60, 3))

    # ceil(59.9)=60，但应 clamp 到 w-1=59；ceil(49.9)=50 clamp 到 h-1=49
    assert _mask_bbox(mask) == (55, 45, 59, 49)


def test_boxes_to_mask_filters_boxes_below_min_area():
    """
    面积小于 min_area_pixels 的检测框应被忽略，避免微小噪点进入修复掩码。
    """
    from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: WPS433

    config = _build_config(
        min_area_pixels=100,
        mask_padding_px=0,
        mask_padding_ratio=0.0,
        mask_padding_max=0,
    )
    detector = YOLOWatermarkDetector(config=config, model_path="dummy.pt", device="cpu")

    boxes = _FakeBoxes(
        [
            [10.2, 10.2, 14.8, 14.8],  # floor/ceil 后面积 25，应被过滤
            [20.2, 20.2, 40.0, 30.0],  # floor/ceil 后面积 200，应保留
        ]
    )
    mask = detector._boxes_to_mask(boxes, (60, 80, 3))

    assert _mask_bbox(mask) == (20, 20, 40, 30)


def test_boxes_to_mask_filters_by_raw_area_before_padding():
    """
    最小面积过滤应基于原始检测框，而不是 padding 后放大的区域。
    """
    from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: WPS433

    config = _build_config(
        min_area_pixels=40,
        mask_padding_px=10,
        mask_padding_ratio=0.0,
        mask_padding_max=10,
    )
    detector = YOLOWatermarkDetector(config=config, model_path="dummy.pt", device="cpu")

    boxes = _FakeBoxes([[10.1, 10.2, 15.0, 15.0]])  # floor/ceil 后面积 25，小于阈值
    mask = detector._boxes_to_mask(boxes, (60, 80, 3))

    assert not np.any(mask)


def test_postprocess_mask_preserves_hollow_logo_center():
    """
    掩码细化应能补齐镂空 logo 的断裂边缘，但不能把中空区域直接填死。
    """
    from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: WPS433

    config = _build_config(
        mask_padding_px=0,
        mask_padding_ratio=0.0,
        mask_padding_max=0,
        mask_close_kernel=5,
        mask_erode_iterations=0,
        mask_dilate_iterations=0,
    )
    detector = YOLOWatermarkDetector(config=config, model_path="dummy.pt", device="cpu")

    refined = detector._postprocess_mask(_create_hollow_logo_mask())

    assert int(refined[19, 31]) == 255
    assert int(refined[32, 32]) == 0


def test_postprocess_mask_delegates_to_mask_refiner(monkeypatch: pytest.MonkeyPatch) -> None:
    """YOLO 检测器应把掩码后处理委托给独立的 MaskRefiner。"""
    from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: WPS433

    detector = YOLOWatermarkDetector(
        config=_build_config(mask_close_kernel=5),
        model_path="dummy.pt",
        device="cpu",
    )
    raw_mask = np.zeros((20, 20), dtype=np.uint8)
    raw_mask[4:10, 5:11] = 255
    sentinel = np.full((20, 20), 255, dtype=np.uint8)
    captured = {}

    class _FakeRefiner:
        def refine(self, mask, frame_shape=None):
            captured["mask_shape"] = tuple(mask.shape)
            captured["frame_shape"] = tuple(frame_shape) if frame_shape is not None else None
            return sentinel

    detector.mask_refiner = _FakeRefiner()

    refined = detector._postprocess_mask(raw_mask, frame_shape=(20, 20, 3))

    assert refined is sentinel
    assert captured == {
        "mask_shape": (20, 20),
        "frame_shape": (20, 20, 3),
    }


def test_postprocess_mask_preserves_small_hollow_center_under_stronger_close_kernel():
    """
    更强闭运算下仍应保住复杂 logo 的小镂空中心，避免整块实心化。
    """
    from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: WPS433

    config = _build_config(
        mask_padding_px=0,
        mask_padding_ratio=0.0,
        mask_padding_max=0,
        mask_close_kernel=9,
        mask_erode_iterations=0,
        mask_dilate_iterations=0,
    )
    detector = YOLOWatermarkDetector(config=config, model_path="dummy.pt", device="cpu")

    refined = detector._postprocess_mask(_create_small_hollow_logo_mask())

    assert int(refined[19, 32]) == 255
    assert int(refined[32, 32]) == 0
