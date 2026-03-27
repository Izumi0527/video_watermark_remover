#!/usr/bin/env python3
"""
单进程视频输出参数回归测试。
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
            return 1
        return 0

    def read(self):
        if self._reads > 0:
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


class _DummyFFmpegProcessor:
    def __init__(self) -> None:
        self.called = False

    def is_available(self) -> bool:
        return True

    def process_video_with_audio_preservation(self, **_kwargs) -> bool:
        self.called = True
        return True


class _ConfigurableFFmpegProcessor:
    def __init__(self, merge_result: bool, *, has_audio: bool = True) -> None:
        self.merge_result = merge_result
        self.has_audio = has_audio
        self.called = False

    def is_available(self) -> bool:
        return True

    def process_video_with_audio_preservation(self, **_kwargs) -> bool:
        self.called = True
        return self.merge_result

    def get_video_info(self, _video_path: str):
        return {"has_audio": self.has_audio}


class _DummyAIHandler:
    def process_frame(self, frame, _params):
        return frame, {"watermark_areas_found": 1}


def test_single_process_skips_audio_merge_when_preserve_audio_disabled(monkeypatch) -> None:
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

    ffmpeg_processor = _DummyFFmpegProcessor()
    processor = SimpleNamespace(
        input_path="C:/tmp/input.mp4",
        output_path="C:/tmp/output.mp4",
        ai_params={"preserve_audio": False},
        ai_handler=_DummyAIHandler(),
        ffmpeg_processor=ffmpeg_processor,
        _is_running=True,
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
    )

    single_process.process_video_singleprocess(processor)

    assert ffmpeg_processor.called is False


def test_single_process_reports_no_audio_when_merge_fails(monkeypatch) -> None:
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

    ffmpeg_processor = _ConfigurableFFmpegProcessor(merge_result=False, has_audio=True)
    processor = SimpleNamespace(
        input_path="C:/tmp/input.mp4",
        output_path="C:/tmp/output.mp4",
        ai_params={"preserve_audio": True},
        ai_handler=_DummyAIHandler(),
        ffmpeg_processor=ffmpeg_processor,
        _is_running=True,
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
    )

    single_process.process_video_singleprocess(processor)

    assert ffmpeg_processor.called is True
    assert processor.status.values
    assert "无音频" in str(processor.status.values[-1])
