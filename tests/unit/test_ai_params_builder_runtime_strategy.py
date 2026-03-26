#!/usr/bin/env python3
"""
统一运行时参数导出测试。
"""

from __future__ import annotations


def test_snapshot_exports_runtime_flags_and_batch_config() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot

    snapshot = AdvancedParamsSnapshot.defaults().replace(
        processing_mode="pipeline",
        worker_count=4,
        batch_max_concurrent_files=2,
    )

    ai_params = snapshot.to_ai_params()
    batch_config = snapshot.to_batch_config()

    assert ai_params["enable_multiprocess"] is True
    assert ai_params["use_pipeline"] is True
    assert ai_params["num_processes"] == 4
    assert ai_params["gpu_memory_mb"] == 2048
    assert ai_params["cache_size_mb"] == 512
    assert ai_params["enable_cache"] is True
    assert batch_config["max_concurrent_files"] == 2
    assert batch_config["auto_retry_failed"] is True
    assert batch_config["max_retry_count"] == 3


def test_builder_resolves_auto_video_mode_to_pipeline() -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    class _DummyPreferences:
        def get_preference(self, _section, _key, default=None):
            return default

    builder = AIParamsBuilder()

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={"processing_mode": "auto", "worker_count": 0},
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["resolved_processing_mode"] == "pipeline"
    assert ai_params["enable_multiprocess"] is True
    assert ai_params["use_pipeline"] is True
    assert ai_params["num_processes"] >= 2
