#!/usr/bin/env python3
"""
流水线帧写入完整性测试。
"""

from __future__ import annotations

import importlib
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


class _FakeStopEvent:
    def is_set(self) -> bool:
        return False


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
