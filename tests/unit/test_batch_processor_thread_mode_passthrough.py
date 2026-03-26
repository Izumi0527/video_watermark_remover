#!/usr/bin/env python3
"""
BatchProcessorThread 内部：VideoProcessorThread 模式参数透传回归测试。

目标：
- 批处理中每个文件创建 VideoProcessorThread 时也必须透传：
  enable_multiprocess / use_pipeline / num_processes
否则批处理里的单个视频仍会静默走默认 single-process 慢路径。
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
            "enable_multiprocess": True,
            "use_pipeline": True,
            "num_processes": 2,
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
    assert captured.get("enable_multiprocess") is True
    assert captured.get("use_pipeline") is True
    assert captured.get("num_processes") == 2
