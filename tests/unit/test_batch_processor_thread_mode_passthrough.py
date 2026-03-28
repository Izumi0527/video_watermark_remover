#!/usr/bin/env python3
"""
BatchProcessorThread 内部：VideoProcessorThread 模式参数透传回归测试。

目标：
- 批处理中每个文件创建 VideoProcessorThread 时也必须透传：
  runtime_performance（统一运行时快照）
否则批处理里的单个视频仍会静默走旧的散装模式参数。
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


class _DummySignal:
    def connect(self, _callback):
        return None


def test_batch_processor_thread_passes_video_mode_params_to_video_processor_thread(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_module = importlib.import_module("app.ui.widgets.batch.batch_processor_thread")
    BatchProcessorThread = batch_module.BatchProcessorThread
    ProcessingStatus = batch_module.ProcessingStatus

    captured: dict = {}

    class _DummyVideoProcessorThread:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)
            self.progress = _DummySignal()
            self.finished = _DummySignal()
            self.error = _DummySignal()
            batch.should_stop = True

        def stop(self):
            return None

        def run(self):
            raise AssertionError("命中取消分支后不应继续执行 run")

    batch = BatchProcessorThread(
        queue=[],
        ai_params={
            "processing_mode": "pipeline",
            "resolved_processing_mode": "single_process",
            "enable_multiprocess": False,
            "use_pipeline": False,
            "num_processes": 1,
            "mode_restriction_reason": "gpu_deep_backend_serial_only",
        },
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files=1,
        auto_retry_failed=False,
    )

    monkeypatch.setattr(batch_module, "VideoProcessorThread", _DummyVideoProcessorThread)

    input_path = tmp_path / "input.txt"
    input_path.write_text("demo", encoding="utf-8")
    output_path = tmp_path / "output.mp4"

    result = batch._process_single_file(str(input_path), str(output_path), 0)

    assert result[0] == ProcessingStatus.CANCELLED
    runtime_performance = captured.get("runtime_performance") or {}
    assert runtime_performance.get("requested_processing_mode") == "pipeline"
    assert runtime_performance.get("resolved_processing_mode") == "single_process"
    assert runtime_performance.get("worker_count") == 1
