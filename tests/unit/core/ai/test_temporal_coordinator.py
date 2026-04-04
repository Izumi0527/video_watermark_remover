#!/usr/bin/env python3
"""
TemporalCoordinator 时序协调测试。
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")


def _create_mask() -> "np.ndarray":
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[8:16, 10:20] = 255
    return mask


def _create_shifted_mask(x_offset: int) -> "np.ndarray":
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[8:16, x_offset : x_offset + 10] = 255
    return mask


def _create_far_shifted_mask() -> "np.ndarray":
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[20:28, 20:30] = 255
    return mask


def test_temporal_coordinator_reuses_mask_between_keyframes() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    mask = _create_mask()
    coordinator = TemporalCoordinator(keyframe_interval=3, warmup_frames=0)

    first = coordinator.update(frame_index=0, detected_mask=mask)
    second = coordinator.update(frame_index=1, detected_mask=None)

    assert np.array_equal(first, second)
    assert first is not second


def test_temporal_coordinator_requires_detection_on_configured_keyframe() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    coordinator = TemporalCoordinator(keyframe_interval=3, warmup_frames=0)
    coordinator.update(frame_index=0, detected_mask=_create_mask())

    assert coordinator.should_detect(1) is False
    assert coordinator.should_detect(3) is True


def test_temporal_coordinator_resets_after_empty_detection() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    empty_mask = np.zeros((32, 32), dtype=np.uint8)
    coordinator = TemporalCoordinator(
        keyframe_interval=3,
        warmup_frames=0,
        max_missing_detections=0,
    )

    coordinator.update(frame_index=0, detected_mask=_create_mask())
    coordinator.update(frame_index=3, detected_mask=empty_mask)

    assert coordinator.update(frame_index=4, detected_mask=None) is None
    assert coordinator.should_detect(4) is True


def test_temporal_coordinator_tolerates_single_missing_detection_before_reset() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    empty_mask = np.zeros((32, 32), dtype=np.uint8)
    coordinator = TemporalCoordinator(
        keyframe_interval=3,
        warmup_frames=0,
        max_missing_detections=1,
    )

    expected = coordinator.update(frame_index=0, detected_mask=_create_mask())
    missing = coordinator.update(frame_index=3, detected_mask=empty_mask)
    second_missing = coordinator.update(frame_index=4, detected_mask=empty_mask)

    assert np.array_equal(expected, missing)
    assert coordinator.should_detect(4) is True
    assert second_missing is None
    assert coordinator.should_detect(5) is True


def test_temporal_coordinator_forces_confirmation_after_large_shift() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    coordinator = TemporalCoordinator(
        keyframe_interval=3,
        warmup_frames=0,
        scene_shift_iou_threshold=0.2,
        scene_shift_confirmation_frames=1,
    )

    coordinator.update(frame_index=0, detected_mask=_create_mask())
    shifted = coordinator.update(frame_index=3, detected_mask=_create_far_shifted_mask())

    assert shifted is not None
    assert coordinator.should_detect(4) is True
    assert coordinator.update(frame_index=4, detected_mask=None) is None


def test_temporal_coordinator_tolerates_single_missed_detection_but_forces_next_redetect() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    coordinator = TemporalCoordinator(
        keyframe_interval=3,
        warmup_frames=0,
        max_missed_detections=1,
    )
    mask = _create_mask()
    empty_mask = np.zeros((32, 32), dtype=np.uint8)

    coordinator.update(frame_index=0, detected_mask=mask)
    reused_on_miss = coordinator.update(frame_index=3, detected_mask=empty_mask)

    assert np.array_equal(reused_on_miss, mask)
    assert reused_on_miss is not mask
    assert coordinator.should_detect(4) is True


def test_temporal_coordinator_forces_next_detection_after_large_mask_shift() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    coordinator = TemporalCoordinator(
        keyframe_interval=3,
        warmup_frames=0,
        motion_redetect_iou_threshold=0.2,
    )

    coordinator.update(frame_index=0, detected_mask=_create_shifted_mask(4))
    coordinator.update(frame_index=3, detected_mask=_create_shifted_mask(18))

    assert coordinator.should_detect(4) is True


def test_temporal_coordinator_forces_next_frame_detection_after_large_shift() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    coordinator = TemporalCoordinator(keyframe_interval=3, warmup_frames=0)
    coordinator.update(frame_index=0, detected_mask=_create_mask())
    shifted = coordinator.update(frame_index=3, detected_mask=_create_far_shifted_mask())

    assert shifted is not None
    assert coordinator.should_detect(4) is True


def test_temporal_coordinator_reuses_last_mask_once_after_empty_keyframe_detection() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    coordinator = TemporalCoordinator(keyframe_interval=3, warmup_frames=0)
    first = coordinator.update(frame_index=0, detected_mask=_create_mask())
    fallback = coordinator.update(frame_index=3, detected_mask=np.zeros((32, 32), dtype=np.uint8))

    assert np.array_equal(first, fallback)
    assert coordinator.should_detect(4) is True


def test_temporal_coordinator_tolerates_one_missing_detection_before_reset() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    empty_mask = np.zeros((32, 32), dtype=np.uint8)
    coordinator = TemporalCoordinator(
        keyframe_interval=3,
        warmup_frames=0,
        max_missing_detections=1,
    )

    coordinator.update(frame_index=0, detected_mask=_create_mask())
    reused = coordinator.update(frame_index=3, detected_mask=empty_mask)

    assert reused is not None
    assert np.array_equal(reused, _create_mask())
    assert coordinator.should_detect(4) is True

    assert coordinator.update(frame_index=4, detected_mask=empty_mask) is None
    assert coordinator.get_stored_mask_copy() is None


def test_temporal_coordinator_forces_redetect_after_large_mask_jump() -> None:
    from app.core.ai.temporal_coordinator import TemporalCoordinator  # noqa: WPS433

    coordinator = TemporalCoordinator(
        keyframe_interval=3,
        warmup_frames=0,
        scene_change_iou_threshold=0.2,
    )

    coordinator.update(frame_index=0, detected_mask=_create_mask())
    jumped = coordinator.update(frame_index=3, detected_mask=_create_far_shifted_mask())

    assert np.array_equal(jumped, _create_far_shifted_mask())
    assert coordinator.should_detect(4) is True
