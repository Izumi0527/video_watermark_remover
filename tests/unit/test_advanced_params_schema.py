#!/usr/bin/env python3
"""
统一高级参数模型测试。
"""

from __future__ import annotations


def test_advanced_params_defaults_are_single_source_of_truth() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot

    snapshot = AdvancedParamsSnapshot.defaults()

    assert snapshot.processing_mode == "single_process"
    assert snapshot.worker_count == 0
    assert snapshot.enable_gpu is True
    assert snapshot.gpu_memory_limit_mb == 2048
    assert snapshot.enable_cache is True
    assert snapshot.cache_size_mb == 512
    assert snapshot.batch_max_concurrent_files == 1
    assert snapshot.batch_auto_retry_failed is True
    assert snapshot.batch_max_retry_count == 3
    assert snapshot.output_format == "keep"
    assert snapshot.compression_quality == 85
    assert snapshot.add_suffix is True
    assert snapshot.add_timestamp is False
    assert snapshot.preserve_audio is True
    assert snapshot.mask_tracking_max_missing_detections == 1
    assert snapshot.mask_tracking_motion_iou_threshold == 0.2
    assert snapshot.mask_tracking_scene_shift_confirmation_frames == 1


def test_advanced_params_snapshot_ignores_legacy_output_aliases() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot

    snapshot = AdvancedParamsSnapshot.from_dict(
        {
            "output_quality": "low",
            "add_processed_suffix": False,
        }
    )

    assert snapshot.compression_quality == 85
    assert snapshot.add_suffix is True


def test_advanced_params_snapshot_accepts_tracking_aliases_and_clamps() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot

    snapshot = AdvancedParamsSnapshot.from_dict(
        {
            "mask_tracking_max_missed_detections": "3",
            "mask_tracking_scene_change_iou_threshold": "2.0",
            "mask_tracking_scene_shift_confirmation_frames": "0",
        }
    )

    assert snapshot.mask_tracking_max_missing_detections == 3
    assert snapshot.mask_tracking_motion_iou_threshold == 1.0
    assert snapshot.mask_tracking_scene_shift_confirmation_frames == 1


def test_advanced_params_snapshot_prefers_tracking_primary_fields() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot

    snapshot = AdvancedParamsSnapshot.from_dict(
        {
            "mask_tracking_max_missing_detections": 5,
            "mask_tracking_max_missed_detections": 2,
            "mask_tracking_motion_iou_threshold": 0.4,
            "mask_tracking_scene_change_iou_threshold": 0.8,
            "mask_tracking_scene_shift_confirmation_frames": 6,
        }
    )

    assert snapshot.mask_tracking_max_missing_detections == 5
    assert snapshot.mask_tracking_motion_iou_threshold == 0.4
    assert snapshot.mask_tracking_scene_shift_confirmation_frames == 6


def test_advanced_params_snapshot_reads_tracking_aliases_and_roundtrips() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot

    snapshot = AdvancedParamsSnapshot.from_dict(
        {
            "mask_tracking_max_missed_detections": 2,
            "mask_tracking_scene_change_iou_threshold": 0.35,
            "mask_tracking_scene_shift_confirmation_frames": 4,
        }
    )

    assert snapshot.mask_tracking_max_missing_detections == 2
    assert snapshot.mask_tracking_motion_iou_threshold == 0.35
    assert snapshot.mask_tracking_scene_shift_confirmation_frames == 4

    serialized = snapshot.to_dict()
    assert serialized["mask_tracking_max_missing_detections"] == 2
    assert serialized["mask_tracking_motion_iou_threshold"] == 0.35
    assert serialized["mask_tracking_scene_shift_confirmation_frames"] == 4
    assert "mask_tracking_max_missed_detections" not in serialized
    assert "mask_tracking_scene_change_iou_threshold" not in serialized


def test_advanced_params_snapshot_clamps_tracking_extreme_values_to_ui_ceiling() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot

    snapshot = AdvancedParamsSnapshot.from_dict(
        {
            "mask_tracking_max_missing_detections": 80,
            "mask_tracking_scene_shift_confirmation_frames": 60,
        }
    )

    assert snapshot.mask_tracking_max_missing_detections == 30
    assert snapshot.mask_tracking_scene_shift_confirmation_frames == 30
