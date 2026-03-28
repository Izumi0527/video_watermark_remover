#!/usr/bin/env python3
"""
帧读取线程在取消/背压场景下的退出行为测试。
"""

from __future__ import annotations

import importlib
import queue
import sys


class _FakeCapture:
    def __init__(self) -> None:
        self._read_count = 0

    def isOpened(self) -> bool:
        return True

    def read(self):
        self._read_count += 1
        if self._read_count == 1:
            return True, {"frame": 0}
        return False, None

    def release(self) -> None:
        return None


class _FakeCv2:
    @staticmethod
    def VideoCapture(_path: str) -> _FakeCapture:
        return _FakeCapture()


class _FullQueue:
    def __init__(self) -> None:
        self.put_items = []

    def put(self, item, timeout=None):
        self.put_items.append((item, timeout))
        if item is None:
            raise RuntimeError("queue closed")
        raise queue.Full()


class _StopEventAfterRetry:
    def __init__(self) -> None:
        self._calls = 0

    def is_set(self) -> bool:
        self._calls += 1
        return self._calls >= 3


def test_frame_reader_exits_quickly_when_queue_full_and_stop_requested(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "cv2", _FakeCv2())
    monkeypatch.delitem(sys.modules, "app.core.video.workers.frame_reader", raising=False)
    frame_reader = importlib.import_module("app.core.video.workers.frame_reader")

    fake_queue = _FullQueue()
    stop_event = _StopEventAfterRetry()

    frame_reader.frame_reader_worker(
        video_path="C:/tmp/in.mp4",
        frame_queue=fake_queue,
        total_frames=5,
        stop_event=stop_event,
    )

    assert any(item is None for item, _ in fake_queue.put_items)
