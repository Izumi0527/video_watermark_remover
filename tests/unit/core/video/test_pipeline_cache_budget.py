#!/usr/bin/env python3
"""
流水线缓存预算测试。
"""

from __future__ import annotations

import importlib
import sys
import types
from concurrent.futures import TimeoutError as FuturesTimeoutError

import pytest


class _DummySignal:
    def connect(self, callback):
        return None


class _DummyTimer:
    def __init__(self, *args, **kwargs):
        self.timeout = _DummySignal()


class _DummyCv2(types.ModuleType):
    pass


def _install_pipeline_import_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")
    qtcore_module.QTimer = _DummyTimer
    monkeypatch.setitem(sys.modules, "PyQt6", pyqt6_module)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore_module)
    monkeypatch.setitem(sys.modules, "cv2", _DummyCv2("cv2"))

    audio_module = types.ModuleType("app.core.video.workers.audio")
    audio_module.async_audio_extractor = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.audio", audio_module)

    frame_processor_module = types.ModuleType("app.core.video.workers.frame_processor")
    frame_processor_module.frame_processor_worker = lambda *args, **kwargs: None
    frame_processor_module.init_worker_ai_handler = lambda *args, **kwargs: None
    monkeypatch.setitem(
        sys.modules, "app.core.video.workers.frame_processor", frame_processor_module
    )

    frame_reader_module = types.ModuleType("app.core.video.workers.frame_reader")
    frame_reader_module.frame_reader_worker = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_reader", frame_reader_module)

    frame_writer_module = types.ModuleType("app.core.video.workers.frame_writer")
    frame_writer_module.frame_writer_worker = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_writer", frame_writer_module)


def test_pipeline_queue_sizes_follow_cache_budget() -> None:
    from app.core.video.utils.backpressure import calculate_runtime_queue_budget

    small = calculate_runtime_queue_budget(
        enable_cache=False,
        cache_size_mb=128,
        frame_shape=(1080, 1920),
        requested_worker_count=4,
    )
    large = calculate_runtime_queue_budget(
        enable_cache=True,
        cache_size_mb=1024,
        frame_shape=(1080, 1920),
        requested_worker_count=4,
    )

    assert large.frame_queue_size > small.frame_queue_size
    assert large.result_queue_size > small.result_queue_size
    assert large.writer_buffer_size > small.writer_buffer_size


def test_pipeline_queue_budget_does_not_grossly_exceed_small_cache_budget() -> None:
    from app.core.video.utils.backpressure import calculate_runtime_queue_budget

    frame_shape = (2160, 3840)
    budget = calculate_runtime_queue_budget(
        enable_cache=True,
        cache_size_mb=64,
        frame_shape=frame_shape,
        requested_worker_count=4,
    )

    assert budget.pipeline_viable is False
    assert budget.effective_worker_count == 0


def test_pipeline_queue_budget_caps_worker_count_within_cache_budget() -> None:
    from app.core.video.utils.backpressure import calculate_runtime_queue_budget

    budget = calculate_runtime_queue_budget(
        enable_cache=True,
        cache_size_mb=256,
        frame_shape=(2160, 3840),
        requested_worker_count=4,
    )

    assert budget.pipeline_viable is True
    assert budget.effective_worker_count == 3
    assert budget.estimated_total_memory_mb <= 256


def test_pipeline_runtime_budget_applies_effective_worker_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_pipeline_import_stubs(monkeypatch)
    monkeypatch.delitem(sys.modules, "app.core.video.modes.pipeline", raising=False)
    from app.core.video.modes import pipeline as pipeline_module

    class _DummyLogger:
        def info(self, *args, **kwargs) -> None:
            return None

        def warning(self, *args, **kwargs) -> None:
            return None

    class _DummyProcessor:
        def __init__(self) -> None:
            self.ai_params = {
                "enable_cache": True,
                "cache_size_mb": 256,
            }
            self.num_processes = 4
            self.logger = _DummyLogger()

    processor = _DummyProcessor()
    budget = pipeline_module._calculate_queue_budget(processor, (2160, 3840))

    assert budget.pipeline_viable is True
    assert budget.effective_worker_count == 3
    assert processor.num_processes == 3


def test_wait_processor_futures_returns_early_when_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_pipeline_import_stubs(monkeypatch)
    monkeypatch.delitem(sys.modules, "app.core.video.modes.pipeline", raising=False)
    from app.core.video.modes import pipeline as pipeline_module

    class _FakeFuture:
        def __init__(self) -> None:
            self.calls = 0

        def result(self, timeout=None):  # noqa: ARG002
            self.calls += 1
            raise FuturesTimeoutError()

    class _FakeProcessor:
        _is_running = False
        _stop_event = None

    future = _FakeFuture()
    pipeline_module._wait_processor_futures(_FakeProcessor(), [future])

    assert future.calls == 1
