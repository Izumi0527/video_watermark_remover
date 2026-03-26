#!/usr/bin/env python3
"""
统一运行时性能配置解析测试。
"""

from __future__ import annotations


def test_auto_mode_for_video_resolves_to_pipeline_when_cpu_is_sufficient() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot, ProcessingContext

    snapshot = AdvancedParamsSnapshot.defaults()
    context = ProcessingContext(
        input_file_path="demo.mp4",
        is_batch=False,
        prefer_pipeline=True,
        cpu_count=8,
        gpu_enabled=True,
    )

    resolved = snapshot.resolve(context)

    assert resolved.requested_processing_mode == "auto"
    assert resolved.resolved_processing_mode == "pipeline"
    assert resolved.enable_multiprocess is True
    assert resolved.use_pipeline is True
    assert resolved.worker_count >= 2


def test_snapshot_resolve_returns_runtime_config_with_budget_and_batch_policy() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot, ProcessingContext

    snapshot = AdvancedParamsSnapshot.defaults().replace(
        processing_mode="pipeline",
        worker_count=4,
        gpu_memory_limit_mb=1536,
        batch_max_concurrent_files=3,
    )
    resolved = snapshot.resolve(
        ProcessingContext(
            input_file_path="demo.mp4",
            is_batch=True,
            prefer_pipeline=True,
            cpu_count=8,
            gpu_enabled=True,
        )
    )

    assert resolved.requested_processing_mode == "pipeline"
    assert resolved.resolved_processing_mode == "pipeline"
    assert resolved.worker_count == 4
    assert resolved.gpu_memory_budget_mb == 1536
    assert resolved.batch_max_concurrent_files == 3
