#!/usr/bin/env python3
"""
MaskRefiner 掩码细化回归测试。
"""

from __future__ import annotations

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


def _build_hollow_logo_mask() -> "np.ndarray":
    mask = np.zeros((64, 64), dtype=np.uint8)
    cv2.rectangle(mask, (14, 14), (50, 50), 255, thickness=2)
    # 刻意打断顶部边缘，模拟复杂 Logo 的断裂边。
    mask[14:16, 30:35] = 0
    return mask


def _build_small_hollow_logo_mask() -> "np.ndarray":
    mask = np.zeros((64, 64), dtype=np.uint8)
    cv2.rectangle(mask, (18, 18), (46, 46), 255, thickness=-1)
    cv2.rectangle(mask, (29, 29), (35, 35), 0, thickness=-1)
    # 刻意打断上边缘，模拟复杂 logo 的局部裂缝。
    mask[18:21, 31:34] = 0
    return mask


def _build_small_hole_logo_mask() -> "np.ndarray":
    mask = np.zeros((64, 64), dtype=np.uint8)
    cv2.rectangle(mask, (14, 14), (50, 50), 255, thickness=-1)
    cv2.rectangle(mask, (28, 28), (34, 34), 0, thickness=-1)
    # 打断外环顶部边缘，模拟需要桥接裂缝的复杂 logo。
    mask[14:17, 29:35] = 0
    return mask


def _build_solid_logo_with_small_hole() -> "np.ndarray":
    mask = np.zeros((64, 64), dtype=np.uint8)
    cv2.rectangle(mask, (16, 16), (48, 48), 255, thickness=-1)
    mask[29:35, 29:35] = 0
    return mask


def _build_broken_horizontal_stroke() -> "np.ndarray":
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[30:33, 8:24] = 255
    mask[30:33, 34:56] = 255
    return mask


def _build_complex_logo_with_speckles() -> "np.ndarray":
    mask = _build_hollow_logo_mask()
    mask[6, 6] = 255
    mask[57, 53] = 255
    return mask


def test_mask_refiner_preserves_hollow_logo_center() -> None:
    """保守细化应连接断裂边缘，但不能把中空 Logo 的中心完全填死。"""
    from app.core.ai.mask_refiner import MaskRefiner  # noqa: WPS433

    refiner = MaskRefiner(profile="complex_logo", close_kernel=5)
    raw_mask = _build_hollow_logo_mask()

    refined = refiner.refine(raw_mask, frame_shape=(64, 64, 3))

    assert refined.dtype == np.uint8
    assert int(refined.sum()) >= int(raw_mask.sum())
    assert int(refined[32, 32]) == 0


def test_mask_refiner_returns_empty_mask_unchanged() -> None:
    """空掩码不应被细化逻辑误改成非空区域。"""
    from app.core.ai.mask_refiner import MaskRefiner  # noqa: WPS433

    refiner = MaskRefiner(close_kernel=5, erode_iterations=1, dilate_iterations=1)
    raw_mask = np.zeros((32, 32), dtype=np.uint8)

    refined = refiner.refine(raw_mask, frame_shape=(32, 32, 3))

    assert refined.shape == raw_mask.shape
    assert not np.any(refined)


def test_mask_refiner_repairs_crack_without_filling_small_hollow_center() -> None:
    """复杂 logo 出现局部裂缝时，应补边但不能误填较小镂空中心。"""
    from app.core.ai.mask_refiner import MaskRefiner  # noqa: WPS433

    refiner = MaskRefiner(profile="complex_logo", close_kernel=9)
    raw_mask = _build_small_hollow_logo_mask()

    refined = refiner.refine(raw_mask, frame_shape=(64, 64, 3))

    assert int(refined[19, 32]) == 255
    assert int(refined[32, 32]) == 0


def test_mask_refiner_preserves_small_hole_while_bridging_outer_crack() -> None:
    """复杂 logo 的小型镂空中心不能因为桥接外环裂缝被误填死。"""
    from app.core.ai.mask_refiner import MaskRefiner  # noqa: WPS433

    refiner = MaskRefiner(profile="complex_logo", close_kernel=5)
    raw_mask = _build_small_hole_logo_mask()

    refined = refiner.refine(raw_mask, frame_shape=(64, 64, 3))

    assert int(refined[15, 31]) == 255
    assert int(refined[31, 31]) == 0


def test_mask_refiner_preserves_small_inner_hole_for_complex_logo() -> None:
    """复杂 logo 的小型镂空结构不应在闭运算后被误填死。"""
    from app.core.ai.mask_refiner import MaskRefiner  # noqa: WPS433

    refiner = MaskRefiner(profile="complex_logo", close_kernel=5)
    raw_mask = _build_solid_logo_with_small_hole()

    refined = refiner.refine(raw_mask, frame_shape=(64, 64, 3))

    assert int(refined[32, 32]) == 0
    assert int(refined.sum()) >= int(raw_mask.sum())


def test_mask_refiner_bridges_long_horizontal_gap_for_complex_logo() -> None:
    """复杂 logo 的细长断边应能通过定向桥接补齐。"""
    from app.core.ai.mask_refiner import MaskRefiner  # noqa: WPS433

    refiner = MaskRefiner(profile="complex_logo", close_kernel=5)
    raw_mask = _build_broken_horizontal_stroke()

    refined = refiner.refine(raw_mask, frame_shape=(64, 64, 3))

    assert int(refined[31, 29]) == 255
    assert int(refined[31, 32]) == 255


def test_mask_refiner_removes_isolated_speckles_for_complex_logo() -> None:
    """复杂 logo 周围的离散小噪点应被清理，避免修复区域误扩散。"""
    from app.core.ai.mask_refiner import MaskRefiner  # noqa: WPS433

    refiner = MaskRefiner(profile="complex_logo", close_kernel=5)
    raw_mask = _build_complex_logo_with_speckles()

    refined = refiner.refine(raw_mask, frame_shape=(64, 64, 3))

    assert int(refined[6, 6]) == 0
    assert int(refined[57, 53]) == 0
    assert int(refined[15, 20]) == 255
    assert int(refined[32, 32]) == 0
