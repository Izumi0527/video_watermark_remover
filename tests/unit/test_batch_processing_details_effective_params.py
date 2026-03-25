#!/usr/bin/env python3
"""BatchProcessorThread 追溯字段透传回归测试。"""

from __future__ import annotations

import pytest


def test_build_processing_details_keeps_effective_params_and_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ui.widgets.batch.batch_processor_thread import BatchProcessorThread

    batch_thread = BatchProcessorThread(queue=[], ai_params={}, config=None)

    class _FakeProcessor:
        pass

    fake_processor = _FakeProcessor()
    fake_processor.last_effective_processing_info = {
        "quality_level": 999,
        "effective_quality_level": 5,
        "effective_inpaint_radius": 9,
        "requested_inpainting_backend": "lama",
        "actual_inpainting_backend": "opencv",
        "inpainting_fallback_reason": "lama_runtime_exception",
        "gpu_inpainting_runtime_error": "gpu runtime exploded",
        "device": "cuda",
    }
    fake_processor.last_processing_info = None
    fake_processor.last_processing_summary = None
    fake_processor.ai_handler = None

    details = batch_thread._build_processing_details(fake_processor)

    assert details["quality_level"] == 999
    assert details["effective_quality_level"] == 5
    assert details["effective_inpaint_radius"] == 9
    assert details["requested_inpainting_backend"] == "lama"
    assert details["actual_inpainting_backend"] == "opencv"
    assert details["inpainting_fallback_reason"] == "lama_runtime_exception"
    assert details["gpu_inpainting_runtime_error"] == "gpu runtime exploded"
