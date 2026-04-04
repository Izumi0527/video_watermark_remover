#!/usr/bin/env python3
"""
P1：混合修复 + 掩码收缩/跟踪 的参数构建回归测试。

目标：
1. 确保 UI 侧开关能被 AIParamsBuilder 正确映射到 ai_params
2. 混合修复阈值从“百分比(%)”正确转换为“面积比例(0-1)”
"""

from __future__ import annotations

import pytest


class _DummyPreferences:
    def get_preference(self, _section, _key, default=None):
        return default


def test_builder_maps_mask_shrink_and_tracking_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: False)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "enable_mask_shrink": True,
            "mask_shrink_pixels": 2,
            "enable_mask_tracking": True,
            "mask_tracking_interval": 5,
            "mask_tracking_max_missing_detections": 2,
            "mask_tracking_motion_iou_threshold": 0.35,
            "mask_tracking_scene_shift_confirmation_frames": 3,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["enable_mask_shrink"] is True
    assert ai_params["mask_shrink_pixels"] == 2
    assert ai_params["enable_mask_tracking"] is True
    assert ai_params["mask_tracking_interval"] == 5
    assert ai_params["mask_tracking_max_missing_detections"] == 2
    assert ai_params["mask_tracking_motion_iou_threshold"] == pytest.approx(0.35, rel=1e-6)
    assert ai_params["mask_tracking_scene_shift_confirmation_frames"] == 3


def test_builder_uses_tracking_defaults_when_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: False)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "enable_mask_tracking": True,
            "mask_tracking_interval": 3,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["mask_tracking_max_missing_detections"] == 1
    assert ai_params["mask_tracking_motion_iou_threshold"] == pytest.approx(0.2, rel=1e-6)
    assert ai_params["mask_tracking_scene_shift_confirmation_frames"] == 1


def test_builder_converts_mixed_inpainting_percent_to_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: False)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "enable_mixed_inpainting": True,
            "mixed_inpainting_area_percent": 0.30,
            "mixed_inpainting_opencv_method": "navier_stokes",
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["enable_mixed_inpainting"] is True
    assert ai_params["mixed_inpainting_opencv_method"] == "navier_stokes"
    assert ai_params["mixed_inpainting_area_ratio_threshold"] == pytest.approx(0.003, rel=1e-6)


def test_builder_maps_mask_tracking_advanced_params(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: False)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "enable_mask_tracking": True,
            "mask_tracking_interval": 5,
            "mask_tracking_max_missing_detections": 2,
            "mask_tracking_motion_iou_threshold": 0.33,
            "mask_tracking_scene_shift_confirmation_frames": 4,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["mask_tracking_interval"] == 5
    assert ai_params["mask_tracking_max_missing_detections"] == 2
    assert ai_params["mask_tracking_motion_iou_threshold"] == pytest.approx(0.33, rel=1e-6)
    assert ai_params["mask_tracking_scene_shift_confirmation_frames"] == 4


def test_builder_accepts_mask_tracking_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: False)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "enable_mask_tracking": True,
            "mask_tracking_max_missed_detections": 3,
            "mask_tracking_scene_change_iou_threshold": 0.28,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["mask_tracking_max_missing_detections"] == 3
    assert ai_params["mask_tracking_motion_iou_threshold"] == pytest.approx(0.28, rel=1e-6)
    assert "mask_tracking_max_missed_detections" not in ai_params
    assert "mask_tracking_scene_change_iou_threshold" not in ai_params


def test_builder_supplies_mask_tracking_defaults_when_fields_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: False)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "inpainting_method": "LaMa 深度学习修复（推荐）",
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["mask_tracking_max_missing_detections"] == 1
    assert ai_params["mask_tracking_motion_iou_threshold"] == pytest.approx(0.2, rel=1e-6)
    assert ai_params["mask_tracking_scene_shift_confirmation_frames"] == 1
