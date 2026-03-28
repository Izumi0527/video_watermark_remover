#!/usr/bin/env python3
"""
详细进度组件运行模式提示测试。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")


def test_widget_shows_runtime_mode_summary_and_hint(qtbot) -> None:
    from app.ui.components.detailed_progress_widget import DetailedProgressWidget

    widget = DetailedProgressWidget()
    qtbot.addWidget(widget)

    widget.update_progress(
        {
            "phase": "processing_frames",
            "current_frame": 12,
            "total_frames": 460,
            "processing_speed": 0.6,
            "time_elapsed": 18.0,
            "eta": 600.0,
            "percentage": 3,
            "requested_processing_mode": "multiprocess",
            "resolved_processing_mode": "single_process",
            "mode_restriction_reason": "gpu_deep_backend_serial_only",
        }
    )

    assert widget.runtime_summary_label.text() == "运行模式：请求多进程分块，实际单进程"
    assert widget.runtime_hint_label.text() == "提示：GPU 深度修复仅支持串行，已自动切换为单进程"
