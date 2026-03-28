#!/usr/bin/env python3
"""
单进程视频处理可观测性回归测试。
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace


class _FakeCapture:
    def __init__(self, _path: str) -> None:
        self._frame = {"shape": (8, 8, 3)}
        self._reads = 0

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
            return 3
        return 0

    def read(self):
        if self._reads >= 3:
            return False, None
        self._reads += 1
        return True, self._frame.copy()

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


class _DummyAIHandler:
    def process_frame(self, frame, _params):
        return frame, {"watermark_areas_found": 1}


def test_single_process_emits_runtime_heartbeat_log(monkeypatch) -> None:
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

    info_logs = []

    def _log_info(message, *args):
        info_logs.append(message % args if args else message)

    monkeypatch.setattr(single_process.time, "time", lambda: 100.0)

    processor = SimpleNamespace(
        input_path="C:/tmp/input.mp4",
        output_path="C:/tmp/output.mp4",
        ai_params={"preserve_audio": False},
        ai_handler=_DummyAIHandler(),
        ffmpeg_processor=None,
        _is_running=True,
        _start_time=0.0,
        progress=_DummySignal(),
        status=_DummySignal(),
        finished=_DummySignal(),
        error=_DummySignal(),
        preview_update=_DummySignal(),
        logger=SimpleNamespace(
            info=_log_info,
            warning=lambda *_args, **_kwargs: None,
            error=lambda *_args, **_kwargs: None,
        ),
        _emit_detailed_progress=lambda *_args, **_kwargs: None,
        last_processing_info=None,
        last_effective_processing_info=None,
        last_processing_summary=None,
        runtime_processing_mode="single_process",
        requested_runtime_processing_mode="multiprocess",
        runtime_processing_guard_reason="gpu_deep_backend_serial_only",
    )

    single_process.process_video_singleprocess(processor)

    assert any(
        "单进程处理心跳" in log and "请求多进程分块，实际单进程" in log and "GPU 深度修复仅支持串行" in log for log in info_logs
    )
