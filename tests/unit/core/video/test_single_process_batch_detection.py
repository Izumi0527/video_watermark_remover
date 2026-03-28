#!/usr/bin/env python3
"""
单进程视频模式批量检测回归测试。
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import numpy as np


class _FakeCapture:
    def __init__(self, _path: str) -> None:
        self._frames = [
            self._build_frame(1),
            self._build_frame(2),
            self._build_frame(3),
        ]

    @staticmethod
    def _build_frame(frame_id: int):
        frame = np.zeros((8, 8, 3), dtype=np.uint8)
        frame[0, 0, 0] = frame_id
        return frame

    def isOpened(self) -> bool:
        return True

    def get(self, prop):
        from app.core.video.modes import single_process

        if prop == single_process.cv2.CAP_PROP_FPS:
            return 5
        if prop == single_process.cv2.CAP_PROP_FRAME_WIDTH:
            return 8
        if prop == single_process.cv2.CAP_PROP_FRAME_HEIGHT:
            return 8
        if prop == single_process.cv2.CAP_PROP_FRAME_COUNT:
            return len(self._frames)
        return 0

    def read(self):
        if not self._frames:
            return False, None
        return True, self._frames.pop(0)

    def release(self) -> None:
        return None


class _FakeWriter:
    def __init__(self, path, fourcc, fps, size) -> None:
        self.path = path
        self.frames = []
        self._opened = True

    def isOpened(self) -> bool:
        return self._opened

    def write(self, frame) -> None:
        self.frames.append(frame)

    def release(self) -> None:
        return None


class _DummySignal:
    def __init__(self) -> None:
        self.values = []

    def emit(self, value=None) -> None:
        self.values.append(value)


class _BatchOnlyAIHandler:
    def __init__(self) -> None:
        self.batch_calls: list[list[int]] = []
        self.process_frame_called = False
        self.watermark_detector = SimpleNamespace(batch_size=2)

    def process_frames_batch(self, frames, _params):
        self.batch_calls.append([int(frame[0, 0, 0]) for frame in frames])
        return [
            (
                {
                    "frame_id": int(frame[0, 0, 0]),
                    "processed_by": "batch",
                },
                {
                    "watermark_areas_found": 1,
                    "processing_time": 0.01,
                },
            )
            for frame in frames
        ]

    def process_frame(self, frame, _params):
        self.process_frame_called = True
        return frame, {"watermark_areas_found": 1, "processing_time": 0.01}


def test_single_process_auto_detect_prefers_batch_detection(monkeypatch) -> None:
    fake_cv2 = SimpleNamespace(
        VideoCapture=_FakeCapture,
        VideoWriter=_FakeWriter,
        VideoWriter_fourcc=lambda *args: 0,
        CAP_PROP_FPS=1,
        CAP_PROP_FRAME_WIDTH=2,
        CAP_PROP_FRAME_HEIGHT=3,
        CAP_PROP_FRAME_COUNT=4,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.delitem(sys.modules, "app.core.video.modes.single_process", raising=False)
    single_process = importlib.import_module("app.core.video.modes.single_process")

    ai_handler = _BatchOnlyAIHandler()
    processor = SimpleNamespace(
        input_path="C:/tmp/input.mp4",
        output_path="C:/tmp/output.mp4",
        ai_params={
            "preserve_audio": False,
            "auto_detect": True,
            "user_mask": None,
        },
        ai_handler=ai_handler,
        ffmpeg_processor=None,
        _is_running=True,
        _start_time=0.0,
        progress=_DummySignal(),
        status=_DummySignal(),
        finished=_DummySignal(),
        error=_DummySignal(),
        preview_update=_DummySignal(),
        logger=SimpleNamespace(
            info=lambda *_args, **_kwargs: None,
            warning=lambda *_args, **_kwargs: None,
            error=lambda *_args, **_kwargs: None,
        ),
        _emit_detailed_progress=lambda *_args, **_kwargs: None,
        last_processing_info=None,
        last_effective_processing_info=None,
        last_processing_summary=None,
        runtime_processing_mode="single_process",
        requested_runtime_processing_mode="single_process",
        runtime_processing_guard_reason=None,
    )

    single_process.process_video_singleprocess(processor)

    assert ai_handler.process_frame_called is False
    assert ai_handler.batch_calls == [[1, 2], [3]]
    assert processor.finished.values == ["C:/tmp/output.mp4"]
