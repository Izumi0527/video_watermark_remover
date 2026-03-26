#!/usr/bin/env python3
"""
BatchProcessingWidget 运行时配置来源测试。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")


def test_batch_processing_widget_no_longer_reads_config_manager_batch_fields(
    qtbot,
) -> None:
    from app.ui.widgets.batch.batch_processing_widget import BatchProcessingWidget

    widget = BatchProcessingWidget()
    qtbot.addWidget(widget)

    widget.max_concurrent_files = 6
    widget.auto_retry_failed = True
    widget.max_retry_count = 2
    widget.set_config(object())
    widget.set_advanced_params(
        {
            "batch_max_concurrent_files": 12,
            "batch_auto_retry_failed": False,
            "batch_max_retry_count": 5,
        }
    )

    assert widget.max_concurrent_files == 12
    assert widget.auto_retry_failed is False
    assert widget.max_retry_count == 5
