#!/usr/bin/env python3
"""
统一运行时参数导出测试。
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", exc_type=ImportError)


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


def test_builder_resolves_auto_video_mode_to_pipeline_when_cuda_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    class _DummyPreferences:
        def get_preference(self, _section, _key, default=None):
            return default

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: False)

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


def test_builder_forces_single_process_when_parallel_mode_uses_cuda_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    class _DummyPreferences:
        def get_preference(self, _section, _key, default=None):
            return default

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: True)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "processing_mode": "pipeline",
            "worker_count": 4,
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "enable_gpu": True,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["processing_mode"] == "pipeline"
    assert ai_params["resolved_processing_mode"] == "single_process"
    assert ai_params["enable_multiprocess"] is False
    assert ai_params["use_pipeline"] is False
    assert ai_params["num_processes"] == 1


def test_builder_keeps_pipeline_when_cpu_detection_and_opencv_are_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    class _DummyPreferences:
        def get_preference(self, _section, _key, default=None):
            return default

    builder = AIParamsBuilder()
    monkeypatch.setattr(builder, "_is_cuda_available", lambda: True)

    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "processing_mode": "pipeline",
            "worker_count": 3,
            "detection_method": "YOLO v11x CPU 模式",
            "inpainting_method": "TELEA 快速修复 (OpenCV)",
            "enable_gpu": False,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["processing_mode"] == "pipeline"
    assert ai_params["resolved_processing_mode"] == "pipeline"
    assert ai_params["enable_multiprocess"] is True
    assert ai_params["use_pipeline"] is True
    assert ai_params["num_processes"] == 3


def test_builder_output_params_do_not_export_legacy_output_fields() -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    class _DummyPreferences:
        def get_preference(self, _section, _key, default=None):
            return default

    builder = AIParamsBuilder()
    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "add_processed_suffix": False,
            "output_quality": "low",
            "add_suffix": True,
            "compression_quality": 73,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert "add_suffix" in ai_params
    assert ai_params["add_suffix"] is True
    assert ai_params["compression_quality"] == 73
    assert "add_processed_suffix" not in ai_params
    assert "output_quality" not in ai_params


def test_builder_forces_gpu_deep_video_mode_to_single_process() -> None:
    from app.ui.utils.ai_params_builder import AIParamsBuilder

    class _DummyPreferences:
        def get_preference(self, _section, _key, default=None):
            return default

    builder = AIParamsBuilder()
    builder._is_cuda_available = lambda: True  # type: ignore[method-assign]
    ai_params = builder.build_from_ui(
        preferences=_DummyPreferences(),
        advanced_params={
            "processing_mode": "pipeline",
            "worker_count": 4,
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "enable_gpu": True,
        },
        manual_selections=None,
        input_file_path="demo.mp4",
    )

    assert ai_params["processing_mode"] == "pipeline"
    assert ai_params["resolved_processing_mode"] == "single_process"
    assert ai_params["enable_multiprocess"] is False
    assert ai_params["use_pipeline"] is False
    assert ai_params["num_processes"] == 1
    assert ai_params["mode_restriction_reason"] == "gpu_deep_backend_serial_only"
