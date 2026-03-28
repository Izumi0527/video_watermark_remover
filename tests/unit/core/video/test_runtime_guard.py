#!/usr/bin/env python3
"""
视频运行模式安全护栏测试。
"""

from __future__ import annotations


def test_guard_forces_single_process_for_gpu_deep_inpainting() -> None:
    from app.core.video.runtime_guard import resolve_video_runtime_mode

    decision = resolve_video_runtime_mode(
        {
            "processing_mode": "pipeline",
            "resolved_processing_mode": "pipeline",
            "enable_multiprocess": True,
            "use_pipeline": True,
            "num_processes": 4,
            "requested_inpainting_backend": "lama",
            "use_gpu_inpainting": True,
        }
    )

    assert decision.requested_mode == "pipeline"
    assert decision.effective_mode == "single_process"
    assert decision.enable_multiprocess is False
    assert decision.use_pipeline is False
    assert decision.worker_count == 1
    assert decision.reason == "gpu_deep_backend_serial_only"


def test_guard_keeps_pipeline_for_opencv_backend() -> None:
    from app.core.video.runtime_guard import resolve_video_runtime_mode

    decision = resolve_video_runtime_mode(
        {
            "processing_mode": "pipeline",
            "resolved_processing_mode": "pipeline",
            "enable_multiprocess": True,
            "use_pipeline": True,
            "num_processes": 4,
            "requested_inpainting_backend": "opencv",
            "use_gpu_inpainting": False,
        }
    )

    assert decision.requested_mode == "pipeline"
    assert decision.effective_mode == "pipeline"
    assert decision.enable_multiprocess is True
    assert decision.use_pipeline is True
    assert decision.worker_count == 4
    assert decision.reason is None


def test_resource_exhaustion_detection_matches_memory_signatures() -> None:
    from app.core.video.runtime_guard import is_resource_exhaustion_error

    assert is_resource_exhaustion_error(MemoryError("Unable to allocate 10.5 MiB")) is True
    assert is_resource_exhaustion_error(RuntimeError("ptxas fatal   : Memory allocation failure"))
    assert (
        is_resource_exhaustion_error(
            RuntimeError(
                "OpenCV(4.13.0) error: (-4:Insufficient memory) Failed to allocate 2764800 bytes"
            )
        )
        is True
    )
    assert is_resource_exhaustion_error(RuntimeError("boom")) is False
