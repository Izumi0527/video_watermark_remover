#!/usr/bin/env python3
"""
BatchProcessorThread 预加载 AIHandler 复用策略测试

目的：
- 并发批处理时不应跨线程复用同一个 preloaded_ai_handler，避免竞态与状态污染。
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_batch_processor_disables_preloaded_ai_handler_when_concurrent_gt_one() -> None:
    from app.ui.widgets.batch.batch_processor_thread import BatchProcessorThread

    dummy_handler = object()
    batch = BatchProcessorThread(
        queue=[],
        ai_params={},
        config=None,
        preloaded_ai_handler=dummy_handler,
        max_concurrent_files=2,
        auto_retry_failed=False,
    )

    assert batch.preloaded_ai_handler is None


def test_batch_processor_keeps_preloaded_ai_handler_when_concurrent_is_one() -> None:
    from app.ui.widgets.batch.batch_processor_thread import BatchProcessorThread

    dummy_handler = object()
    batch = BatchProcessorThread(
        queue=[],
        ai_params={},
        config=None,
        preloaded_ai_handler=dummy_handler,
        max_concurrent_files=1,
        auto_retry_failed=False,
    )

    assert batch.preloaded_ai_handler is dummy_handler


class _DummySignal:
    def connect(self, callback):
        return None


def test_batch_processor_returns_cancelled_tuple_when_stop_happens_after_processor_created(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_module = importlib.import_module("app.ui.widgets.batch.batch_processor_thread")
    BatchProcessorThread = batch_module.BatchProcessorThread
    ProcessingStatus = batch_module.ProcessingStatus

    batch = BatchProcessorThread(
        queue=[],
        ai_params={},
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files=1,
        auto_retry_failed=False,
    )

    class _DummyVideoProcessorThread:
        def __init__(self, *args, **kwargs):
            self.progress = _DummySignal()
            self.finished = _DummySignal()
            self.error = _DummySignal()
            batch.should_stop = True

        def stop(self) -> None:
            return None

        def run(self) -> None:
            raise AssertionError("命中取消分支后不应继续执行 run")

    monkeypatch.setattr(batch_module, "VideoProcessorThread", _DummyVideoProcessorThread)

    input_path = tmp_path / "input.txt"
    input_path.write_text("demo", encoding="utf-8")
    output_path = tmp_path / "output.mp4"

    result = batch._process_single_file(str(input_path), str(output_path), 0)

    assert result == (ProcessingStatus.CANCELLED, "用户取消", None)


def test_batch_processor_wrapper_marks_retry_wait_cancel_as_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_module = importlib.import_module("app.ui.widgets.batch.batch_processor_thread")
    BatchProcessorThread = batch_module.BatchProcessorThread
    ProcessingStatus = batch_module.ProcessingStatus

    batch = BatchProcessorThread(
        queue=[],
        ai_params={},
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files=1,
        auto_retry_failed=True,
        max_retry_count=3,
    )

    attempts = {"count": 0}

    def _fake_process_single_file(input_path: str, output_path: str, file_index: int):
        attempts["count"] += 1
        return (ProcessingStatus.FAILED, "首次失败", {"attempt": attempts["count"]})

    def _fake_sleep(seconds: float) -> None:
        batch.should_stop = True

    monkeypatch.setattr(batch, "_process_single_file", _fake_process_single_file)
    monkeypatch.setattr(batch_module.time, "sleep", _fake_sleep)

    result = batch._process_single_file_wrapper(0, "demo.mp4", "demo_out.mp4", 1)

    assert result == ("", ProcessingStatus.CANCELLED, "用户取消", {"attempt": 1})
