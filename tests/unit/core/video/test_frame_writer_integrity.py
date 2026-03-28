#!/usr/bin/env python3
"""
流水线帧写入完整性测试。
"""

from __future__ import annotations

import importlib
import logging
import queue
import sys


class _FakeWriter:
    def __init__(self) -> None:
        self.frames = []

    def isOpened(self) -> bool:
        return True

    def write(self, frame) -> None:
        self.frames.append(frame)

    def release(self) -> None:
        return None


class _FakeResultQueue:
    def __init__(self, items) -> None:
        self.items = list(items)

    def get(self, timeout=None):  # noqa: ARG002
        if not self.items:
            raise TimeoutError("queue empty")
        return self.items.pop(0)


class _FakeResultQueueWithEmpty:
    def __init__(self) -> None:
        self._calls = 0

    def get(self, timeout=None):  # noqa: ARG002
        self._calls += 1
        if self._calls == 1:
            raise queue.Empty()
        if self._calls == 2:
            return (0, {"frame": 0})
        return None


class _FakeStopEvent:
    def is_set(self) -> bool:
        return False


class _FakeStoppedEvent:
    def is_set(self) -> bool:
        return True


class _FakeProgressQueue:
    def put(self, *_args, **_kwargs) -> None:
        return None


def test_frame_writer_returns_failure_when_frames_missing(monkeypatch) -> None:
    fake_cv2 = type(
        "_FakeCV2",
        (),
        {
            "VideoWriter": object,
            "VideoWriter_fourcc": staticmethod(lambda *_args: 0),
        },
    )()
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.delitem(sys.modules, "app.core.video.workers.frame_writer", raising=False)
    frame_writer = importlib.import_module("app.core.video.workers.frame_writer")

    monkeypatch.setattr(
        frame_writer,
        "create_video_writer",
        lambda *_args, **_kwargs: (_FakeWriter(), "mp4v"),
    )

    result_queue = _FakeResultQueue(
        [
            (1, {"frame": 1}),
            None,
        ]
    )
    success, error_message = frame_writer.frame_writer_worker(
        result_queue=result_queue,
        output_path="C:/tmp/out.mp4",
        video_params={"fps": 25, "width": 16, "height": 16},
        total_frames=2,
        stop_event=_FakeStopEvent(),
        progress_queue=_FakeProgressQueue(),
    )

    assert success is False
    assert error_message is not None
    assert "Only 0/2 frames written" in error_message


def test_frame_writer_skips_empty_queue_timeout_warning(monkeypatch, caplog) -> None:
    fake_cv2 = type(
        "_FakeCV2",
        (),
        {
            "VideoWriter": object,
            "VideoWriter_fourcc": staticmethod(lambda *_args: 0),
        },
    )()
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.delitem(sys.modules, "app.core.video.workers.frame_writer", raising=False)
    frame_writer = importlib.import_module("app.core.video.workers.frame_writer")

    monkeypatch.setattr(
        frame_writer,
        "create_video_writer",
        lambda *_args, **_kwargs: (_FakeWriter(), "mp4v"),
    )

    caplog.set_level(logging.WARNING)
    success, error_message = frame_writer.frame_writer_worker(
        result_queue=_FakeResultQueueWithEmpty(),
        output_path="C:/tmp/out.mp4",
        video_params={"fps": 25, "width": 16, "height": 16},
        total_frames=1,
        stop_event=_FakeStopEvent(),
        progress_queue=_FakeProgressQueue(),
    )

    assert success is True
    assert error_message is None
    assert "Frame writer error" not in caplog.text


def test_frame_writer_returns_cancelled_when_stop_event_is_set(monkeypatch) -> None:
    fake_cv2 = type(
        "_FakeCV2",
        (),
        {
            "VideoWriter": object,
            "VideoWriter_fourcc": staticmethod(lambda *_args: 0),
        },
    )()
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.delitem(sys.modules, "app.core.video.workers.frame_writer", raising=False)
    frame_writer = importlib.import_module("app.core.video.workers.frame_writer")

    monkeypatch.setattr(
        frame_writer,
        "create_video_writer",
        lambda *_args, **_kwargs: (_FakeWriter(), "mp4v"),
    )

    success, error_message = frame_writer.frame_writer_worker(
        result_queue=_FakeResultQueue([]),
        output_path="C:/tmp/out.mp4",
        video_params={"fps": 25, "width": 16, "height": 16},
        total_frames=1,
        stop_event=_FakeStoppedEvent(),
        progress_queue=_FakeProgressQueue(),
    )

    assert success is False
    assert error_message == "cancelled"
