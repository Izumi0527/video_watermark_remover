#!/usr/bin/env python3
"""
高级参数界面运行时模型测试。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")


def test_widget_reads_and_writes_unified_performance_params(qtbot) -> None:
    from app.ui.widgets.advanced.advanced_parameters_widget import AdvancedParametersWidget

    widget = AdvancedParametersWidget()
    qtbot.addWidget(widget)

    widget.set_parameters(
        {
            "processing_mode": "pipeline",
            "worker_count": 0,
            "batch_max_concurrent_files": 3,
            "batch_auto_retry_failed": True,
            "batch_max_retry_count": 2,
        }
    )

    params = widget.get_parameters()

    assert params["processing_mode"] == "pipeline"
    assert params["worker_count"] == 0
    assert params["batch_max_concurrent_files"] == 3
    assert params["batch_auto_retry_failed"] is True
    assert params["batch_max_retry_count"] == 2
    assert widget.worker_count_spin is not None
    assert widget.worker_count_spin.minimum() == 0

    assert widget.processing_mode_combo is not None
    mode_values = {
        widget.processing_mode_combo.itemData(index)
        for index in range(widget.processing_mode_combo.count())
    }
    assert "single_process" in mode_values
    assert "multiprocess" in mode_values
    assert "pipeline" in mode_values
    assert "auto" not in mode_values


def test_widget_falls_back_to_single_process_when_loading_legacy_auto_mode(qtbot) -> None:
    from app.ui.widgets.advanced.advanced_parameters_widget import AdvancedParametersWidget

    widget = AdvancedParametersWidget()
    qtbot.addWidget(widget)

    widget.set_parameters({"processing_mode": "auto"})

    params = widget.get_parameters()
    assert params["processing_mode"] == "single_process"


def test_widget_reads_and_writes_mask_tracking_runtime_params(qtbot) -> None:
    from app.ui.widgets.advanced.advanced_parameters_widget import AdvancedParametersWidget

    widget = AdvancedParametersWidget()
    qtbot.addWidget(widget)

    widget.set_parameters(
        {
            "enable_mask_tracking": True,
            "mask_tracking_interval": 6,
            "mask_tracking_max_missing_detections": 2,
            "mask_tracking_motion_iou_threshold": 0.31,
            "mask_tracking_scene_shift_confirmation_frames": 3,
        }
    )

    params = widget.get_parameters()

    assert params["enable_mask_tracking"] is True
    assert params["mask_tracking_interval"] == 6
    assert params["mask_tracking_max_missing_detections"] == 2
    assert params["mask_tracking_motion_iou_threshold"] == pytest.approx(0.31, rel=1e-6)
    assert params["mask_tracking_scene_shift_confirmation_frames"] == 3


def test_widget_disables_blend_postprocess_by_default(qtbot) -> None:
    from app.ui.widgets.advanced.advanced_parameters_widget import AdvancedParametersWidget

    widget = AdvancedParametersWidget()
    qtbot.addWidget(widget)

    assert widget.enable_blend_check is not None
    assert widget.enable_blend_check.isChecked() is False

    params = widget.get_parameters()
    assert params["enable_blend_postprocess"] is False
