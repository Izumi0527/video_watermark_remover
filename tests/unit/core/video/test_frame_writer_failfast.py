#!/usr/bin/env python3
"""
写帧线程内存错误快速失败测试。
"""

from __future__ import annotations

from queue import Empty


class _FakeStopEvent:
    def __init__(self) -> None:
        self._set = False

    def is_set(self) -> bool:
        return self._set

    def set(self) -> None:
        self._set = True


class _FakeQueue:
    def get(self, timeout=None):  # noqa: ARG002
        raise MemoryError("Unable to allocate 10.5 MiB")


class _FakeProgressQueue:
    def put(self, item, block=True):  # noqa: ARG002
        return None


def test_frame_writer_returns_fatal_error_on_memory_exhaustion(monkeypatch) -> None:
    from app.core.video.workers import frame_writer as frame_writer_module

    class _FakeWriter:
        def isOpened(self) -> bool:
            return True

        def write(self, _frame) -> None:
            return None

        def release(self) -> None:
            return None

    monkeypatch.setattr(
        frame_writer_module,
        "create_video_writer",
        lambda *args, **kwargs: (_FakeWriter(), "mp4v"),
    )

    stop_event = _FakeStopEvent()
    success, error_msg = frame_writer_module.frame_writer_worker(
        result_queue=_FakeQueue(),
        output_path="out.mp4",
        video_params={
            "fps": 25.0,
            "width": 16,
            "height": 16,
            "writer_buffer_size": 2,
        },
        total_frames=10,
        stop_event=stop_event,
        progress_queue=_FakeProgressQueue(),
    )

    assert success is False
    assert error_msg is not None
    assert "memory" in error_msg.lower()
    assert stop_event.is_set() is True
