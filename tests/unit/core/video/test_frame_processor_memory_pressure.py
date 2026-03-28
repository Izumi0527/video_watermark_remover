#!/usr/bin/env python3
"""
帧处理进程在内存压力场景下的停机行为测试。
"""

from __future__ import annotations

import importlib
import sys
import types


class _FakeStopEvent:
    def __init__(self) -> None:
        self._set = False
        self.set_called = False

    def is_set(self) -> bool:
        return self._set

    def set(self) -> None:
        self._set = True
        self.set_called = True


class _FakeFrameQueue:
    def __init__(self) -> None:
        self._items = [(0, {"frame": 0})]

    def get(self, timeout=None):  # noqa: ARG002
        if self._items:
            return self._items.pop(0)
        raise TimeoutError("queue empty")

    def put(self, item):  # noqa: ARG002
        return None


class _FakeResultQueue:
    def put(self, item, timeout=None):  # noqa: ARG002
        return None


class _FakeProgressQueue:
    def put(self, *_args, **_kwargs) -> None:
        return None


class _RaisingHandler:
    def process_frame(self, *_args, **_kwargs):
        raise MemoryError("Unable to allocate frame buffer")


def test_frame_processor_sets_stop_event_when_memory_pressure_occurs(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "app.core.video.workers.frame_processor", raising=False)
    frame_processor = importlib.import_module("app.core.video.workers.frame_processor")
    frame_processor._worker_ai_handler = _RaisingHandler()
    frame_processor.AIHandler = types.SimpleNamespace

    stop_event = _FakeStopEvent()
    frame_processor.frame_processor_worker(
        frame_queue=_FakeFrameQueue(),
        result_queue=_FakeResultQueue(),
        ai_params={},
        config_dict=None,
        stop_event=stop_event,
        progress_queue=_FakeProgressQueue(),
        worker_id=0,
    )

    assert stop_event.set_called is True
