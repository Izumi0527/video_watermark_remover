#!/usr/bin/env python3
"""
取消请求下的视频模式回退行为测试。
"""

from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pytest


class _DummySignal:
    def connect(self, _callback):
        return None


class _DummyEmitter:
    def __init__(self) -> None:
        self.values = []

    def emit(self, value) -> None:
        self.values.append(value)


class _TimelineEmitter(_DummyEmitter):
    def __init__(self, timeline: list[str], label: str) -> None:
        super().__init__()
        self._timeline = timeline
        self._label = label

    def emit(self, value) -> None:
        self._timeline.append(self._label)
        super().emit(value)


class _DummyTimer:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        self.timeout = _DummySignal()

    def start(self, *_args, **_kwargs) -> None:
        return None

    def stop(self) -> None:
        return None


class _FakeEvent:
    def __init__(self) -> None:
        self._set = False

    def is_set(self) -> bool:
        return self._set

    def set(self) -> None:
        self._set = True


class _FakeQueue:
    def __init__(self) -> None:
        self._items = []

    def put(self, item, block=True, timeout=None):  # noqa: ARG002
        self._items.append(item)

    def get(self, timeout=None):  # noqa: ARG002
        raise TimeoutError("queue empty")

    def empty(self) -> bool:
        return len(self._items) == 0

    def get_nowait(self):
        if self._items:
            return self._items.pop(0)
        raise LookupError("empty")


class _FakeManager:
    def Queue(self, maxsize=None):  # noqa: ARG002
        return _FakeQueue()

    def Event(self):
        return _FakeEvent()


class _FakeVideoCapture:
    CAP_PROP_FRAME_COUNT = 7
    CAP_PROP_FPS = 5
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FOURCC = 6

    def __init__(self, _path: str) -> None:
        self._opened = True

    def isOpened(self) -> bool:
        return self._opened

    def get(self, prop_id):
        mapping = {
            self.CAP_PROP_FRAME_COUNT: 10,
            self.CAP_PROP_FPS: 25.0,
            self.CAP_PROP_FRAME_WIDTH: 16,
            self.CAP_PROP_FRAME_HEIGHT: 16,
            self.CAP_PROP_FOURCC: 0,
        }
        return mapping.get(prop_id, 0)

    def release(self) -> None:
        return None


class _FakeThread:
    def __init__(self, target, args=(), daemon=True):  # noqa: ARG002
        self._target = target
        self._args = args
        self._alive = False

    def start(self) -> None:
        self._alive = True
        self._target(*self._args)
        self._alive = False

    def join(self, timeout=None):  # noqa: ARG002
        return None

    def is_alive(self) -> bool:
        return self._alive


class _FakeFuture:
    def __init__(self, result_value=None, raises: Exception | None = None) -> None:
        self._result_value = result_value
        self._raises = raises

    def result(self):
        if self._raises is not None:
            raise self._raises
        return self._result_value


class _FakeLogger:
    def info(self, *args, **kwargs) -> None:  # noqa: ARG002
        return None

    def warning(self, *args, **kwargs) -> None:  # noqa: ARG002
        return None

    def error(self, *args, **kwargs) -> None:  # noqa: ARG002
        return None

    def debug(self, *args, **kwargs) -> None:  # noqa: ARG002
        return None


def _install_common_import_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")
    qtcore_module.QTimer = _DummyTimer
    monkeypatch.setitem(sys.modules, "PyQt6", pyqt6_module)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore_module)

    cv2_module = types.ModuleType("cv2")
    cv2_module.VideoCapture = _FakeVideoCapture
    cv2_module.CAP_PROP_FRAME_COUNT = _FakeVideoCapture.CAP_PROP_FRAME_COUNT
    cv2_module.CAP_PROP_FPS = _FakeVideoCapture.CAP_PROP_FPS
    cv2_module.CAP_PROP_FRAME_WIDTH = _FakeVideoCapture.CAP_PROP_FRAME_WIDTH
    cv2_module.CAP_PROP_FRAME_HEIGHT = _FakeVideoCapture.CAP_PROP_FRAME_HEIGHT
    cv2_module.CAP_PROP_FOURCC = _FakeVideoCapture.CAP_PROP_FOURCC
    monkeypatch.setitem(sys.modules, "cv2", cv2_module)


def test_pipeline_cancelled_does_not_fallback_to_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_common_import_stubs(monkeypatch)

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
    frame_writer_module.frame_writer_worker = lambda *args, **kwargs: (
        False,
        "Warning: Only 4/10 frames written",
    )
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_writer", frame_writer_module)

    monkeypatch.delitem(sys.modules, "app.core.video.modes.pipeline", raising=False)
    pipeline_module = importlib.import_module("app.core.video.modes.pipeline")

    class _FakePipelineExecutor:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            return None

        def submit(self, *args, **kwargs):  # noqa: ARG002
            return _FakeFuture()

        def shutdown(self, wait=False):  # noqa: ARG002
            return None

    monkeypatch.setattr(pipeline_module.multiprocessing, "Manager", lambda: _FakeManager())
    monkeypatch.setattr(pipeline_module, "ProcessPoolExecutor", _FakePipelineExecutor)
    monkeypatch.setattr(pipeline_module.threading, "Thread", _FakeThread)
    monkeypatch.setattr(pipeline_module, "should_preserve_audio", lambda _params: False)
    monkeypatch.setattr(
        pipeline_module,
        "_calculate_queue_budget",
        lambda _processor, _shape: SimpleNamespace(
            pipeline_viable=True,
            frame_queue_size=2,
            result_queue_size=2,
            writer_buffer_size=2,
            effective_worker_count=1,
            requested_worker_count=1,
            estimated_total_memory_mb=1.0,
            minimum_viable_memory_mb=1.0,
        ),
    )

    class _DummyProcessor:
        def __init__(self) -> None:
            self.input_path = "input.mp4"
            self.output_path = "output.mp4"
            self.ai_params = {}
            self.config = None
            self.num_processes = 1
            self._is_running = False
            self._progress_timer = None
            self._stop_event = None
            self._reader_thread = None
            self._writer_thread = None
            self._processor_pool = None
            self.ffmpeg_processor = SimpleNamespace(is_available=lambda: False)
            self.logger = _FakeLogger()
            self.status = _DummyEmitter()
            self.progress = _DummyEmitter()
            self.finished = _DummyEmitter()
            self._chunk_fallback_called = False

        def _emit_detailed_progress(self, *args, **kwargs) -> None:  # noqa: ARG002
            return None

        def _process_video_singleprocess(self) -> None:
            return None

        def _process_video_multiprocess(self) -> None:
            self._chunk_fallback_called = True

    processor = _DummyProcessor()
    pipeline_module.process_video_pipeline(processor)

    assert processor._chunk_fallback_called is False
    assert processor.finished.values == [""]
    assert any("处理已取消" in item for item in processor.status.values)


def test_multiprocess_cancelled_does_not_fallback_to_singleprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_common_import_stubs(monkeypatch)

    chunk_module = types.ModuleType("app.core.video.workers.chunk")
    chunk_module.process_video_chunk = lambda *args, **kwargs: ("chunk.mp4", True, None)
    chunk_module.init_chunk_worker_ai_handler = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.chunk", chunk_module)

    monkeypatch.delitem(sys.modules, "app.core.video.modes.multiprocess", raising=False)
    multiprocess_module = importlib.import_module("app.core.video.modes.multiprocess")

    class _FakeMultiprocessExecutor:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            self._future = _FakeFuture(raises=RuntimeError("cancelled"))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ARG002
            return False

        def submit(self, *args, **kwargs):  # noqa: ARG002
            return self._future

    monkeypatch.setattr(multiprocess_module.multiprocessing, "Manager", lambda: _FakeManager())
    monkeypatch.setattr(multiprocess_module, "ProcessPoolExecutor", _FakeMultiprocessExecutor)
    monkeypatch.setattr(multiprocess_module, "as_completed", lambda futures: futures)
    monkeypatch.setattr(multiprocess_module, "QTimer", _DummyTimer)
    monkeypatch.setattr(
        multiprocess_module,
        "_calculate_chunks",
        lambda _processor, _total_frames, _num_processes, output_path="": [(0, 10, "chunk.mp4")],
    )
    monkeypatch.setattr(multiprocess_module, "should_preserve_audio", lambda _params: False)

    class _DummyProcessor:
        def __init__(self) -> None:
            self.input_path = "input.mp4"
            self.output_path = "output.mp4"
            self.ai_params = {}
            self.config = None
            self.num_processes = 1
            self._is_running = False
            self._progress_timer = None
            self._stop_event = None
            self.logger = _FakeLogger()
            self.status = _DummyEmitter()
            self.progress = _DummyEmitter()
            self.finished = _DummyEmitter()
            self._singleprocess_fallback_called = False
            self.ffmpeg_processor = SimpleNamespace(is_available=lambda: False)

        def _emit_detailed_progress(self, *args, **kwargs) -> None:  # noqa: ARG002
            return None

        def _process_video_singleprocess(self) -> None:
            self._singleprocess_fallback_called = True

    processor = _DummyProcessor()
    multiprocess_module.process_video_multiprocess(processor)

    assert processor._singleprocess_fallback_called is False
    assert processor.finished.values == [""]
    assert any("处理已取消" in item for item in processor.status.values)


def test_pipeline_cancel_finishes_after_timer_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_common_import_stubs(monkeypatch)

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
    frame_writer_module.frame_writer_worker = lambda *args, **kwargs: (
        False,
        "Warning: Only 4/10 frames written",
    )
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_writer", frame_writer_module)

    monkeypatch.delitem(sys.modules, "app.core.video.modes.pipeline", raising=False)
    pipeline_module = importlib.import_module("app.core.video.modes.pipeline")

    timeline: list[str] = []

    class _TimelineTimer(_DummyTimer):
        def stop(self) -> None:
            timeline.append("timer_stop")

    class _FakePipelineExecutor:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            return None

        def submit(self, *args, **kwargs):  # noqa: ARG002
            return _FakeFuture()

        def shutdown(self, wait=False):  # noqa: ARG002
            return None

    monkeypatch.setattr(pipeline_module, "QTimer", _TimelineTimer)
    monkeypatch.setattr(pipeline_module.multiprocessing, "Manager", lambda: _FakeManager())
    monkeypatch.setattr(pipeline_module, "ProcessPoolExecutor", _FakePipelineExecutor)
    monkeypatch.setattr(pipeline_module.threading, "Thread", _FakeThread)
    monkeypatch.setattr(pipeline_module, "should_preserve_audio", lambda _params: False)
    monkeypatch.setattr(
        pipeline_module,
        "_calculate_queue_budget",
        lambda _processor, _shape: SimpleNamespace(
            pipeline_viable=True,
            frame_queue_size=2,
            result_queue_size=2,
            writer_buffer_size=2,
            effective_worker_count=1,
            requested_worker_count=1,
            estimated_total_memory_mb=1.0,
            minimum_viable_memory_mb=1.0,
        ),
    )

    class _DummyProcessor:
        def __init__(self) -> None:
            self.input_path = "input.mp4"
            self.output_path = "output.mp4"
            self.ai_params = {}
            self.config = None
            self.num_processes = 1
            self._is_running = False
            self._progress_timer = None
            self._stop_event = None
            self._reader_thread = None
            self._writer_thread = None
            self._processor_pool = None
            self.ffmpeg_processor = SimpleNamespace(is_available=lambda: False)
            self.logger = _FakeLogger()
            self.status = _DummyEmitter()
            self.progress = _DummyEmitter()
            self.finished = _TimelineEmitter(timeline, "finished")

        def _emit_detailed_progress(self, *args, **kwargs) -> None:  # noqa: ARG002
            return None

        def _process_video_singleprocess(self) -> None:
            return None

        def _process_video_multiprocess(self) -> None:
            raise AssertionError("取消路径不应回退到分块模式")

    processor = _DummyProcessor()
    pipeline_module.process_video_pipeline(processor)

    assert timeline.index("timer_stop") < timeline.index("finished")


def test_pipeline_fallback_starts_after_timer_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_common_import_stubs(monkeypatch)

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
    frame_writer_module.frame_writer_worker = lambda *args, **kwargs: (False, "fatal failure")
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_writer", frame_writer_module)

    monkeypatch.delitem(sys.modules, "app.core.video.modes.pipeline", raising=False)
    pipeline_module = importlib.import_module("app.core.video.modes.pipeline")

    timeline: list[str] = []

    class _TimelineTimer(_DummyTimer):
        def stop(self) -> None:
            timeline.append("timer_stop")

    class _FakePipelineExecutor:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            return None

        def submit(self, *args, **kwargs):  # noqa: ARG002
            return _FakeFuture()

        def shutdown(self, wait=False):  # noqa: ARG002
            return None

    monkeypatch.setattr(pipeline_module, "QTimer", _TimelineTimer)
    monkeypatch.setattr(pipeline_module.multiprocessing, "Manager", lambda: _FakeManager())
    monkeypatch.setattr(pipeline_module, "ProcessPoolExecutor", _FakePipelineExecutor)
    monkeypatch.setattr(pipeline_module.threading, "Thread", _FakeThread)
    monkeypatch.setattr(pipeline_module, "should_preserve_audio", lambda _params: False)
    monkeypatch.setattr(
        pipeline_module,
        "_calculate_queue_budget",
        lambda _processor, _shape: SimpleNamespace(
            pipeline_viable=True,
            frame_queue_size=2,
            result_queue_size=2,
            writer_buffer_size=2,
            effective_worker_count=1,
            requested_worker_count=1,
            estimated_total_memory_mb=1.0,
            minimum_viable_memory_mb=1.0,
        ),
    )

    class _DummyProcessor:
        def __init__(self) -> None:
            self.input_path = "input.mp4"
            self.output_path = "output.mp4"
            self.ai_params = {}
            self.config = None
            self.num_processes = 1
            self._is_running = True
            self._progress_timer = None
            self._stop_event = None
            self._reader_thread = None
            self._writer_thread = None
            self._processor_pool = None
            self.ffmpeg_processor = SimpleNamespace(is_available=lambda: False)
            self.logger = _FakeLogger()
            self.status = _DummyEmitter()
            self.progress = _DummyEmitter()
            self.finished = _DummyEmitter()

        def _emit_detailed_progress(self, *args, **kwargs) -> None:  # noqa: ARG002
            return None

        def _process_video_singleprocess(self) -> None:
            return None

        def _process_video_multiprocess(self) -> None:
            timeline.append("fallback")

    processor = _DummyProcessor()
    pipeline_module.process_video_pipeline(processor)

    assert timeline.index("timer_stop") < timeline.index("fallback")


def test_multiprocess_cancel_finishes_after_timer_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_common_import_stubs(monkeypatch)

    chunk_module = types.ModuleType("app.core.video.workers.chunk")
    chunk_module.process_video_chunk = lambda *args, **kwargs: ("chunk.mp4", True, None)
    chunk_module.init_chunk_worker_ai_handler = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.chunk", chunk_module)

    monkeypatch.delitem(sys.modules, "app.core.video.modes.multiprocess", raising=False)
    multiprocess_module = importlib.import_module("app.core.video.modes.multiprocess")

    timeline: list[str] = []

    class _TimelineTimer(_DummyTimer):
        def stop(self) -> None:
            timeline.append("timer_stop")

    class _FakeMultiprocessExecutor:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            self._future = _FakeFuture(result_value=("chunk.mp4", True, None))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ARG002
            return False

        def submit(self, *args, **kwargs):  # noqa: ARG002
            return self._future

    monkeypatch.setattr(multiprocess_module, "QTimer", _TimelineTimer)
    monkeypatch.setattr(multiprocess_module.multiprocessing, "Manager", lambda: _FakeManager())
    monkeypatch.setattr(multiprocess_module, "ProcessPoolExecutor", _FakeMultiprocessExecutor)
    monkeypatch.setattr(multiprocess_module, "as_completed", lambda futures: futures)
    monkeypatch.setattr(
        multiprocess_module,
        "_calculate_chunks",
        lambda _processor, _total_frames, _num_processes, output_path="": [(0, 10, "chunk.mp4")],
    )
    monkeypatch.setattr(multiprocess_module, "should_preserve_audio", lambda _params: False)

    class _DummyProcessor:
        def __init__(self) -> None:
            self.input_path = "input.mp4"
            self.output_path = "output.mp4"
            self.ai_params = {}
            self.config = None
            self.num_processes = 1
            self._is_running = False
            self._progress_timer = None
            self._stop_event = None
            self.logger = _FakeLogger()
            self.status = _DummyEmitter()
            self.progress = _DummyEmitter()
            self.finished = _TimelineEmitter(timeline, "finished")
            self.ffmpeg_processor = SimpleNamespace(is_available=lambda: False)

        def _emit_detailed_progress(self, *args, **kwargs) -> None:  # noqa: ARG002
            return None

        def _process_video_singleprocess(self) -> None:
            raise AssertionError("取消路径不应回退到单进程")

    processor = _DummyProcessor()
    multiprocess_module.process_video_multiprocess(processor)

    assert timeline.index("timer_stop") < timeline.index("finished")


def test_multiprocess_fallback_starts_after_timer_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_common_import_stubs(monkeypatch)

    chunk_module = types.ModuleType("app.core.video.workers.chunk")
    chunk_module.process_video_chunk = lambda *args, **kwargs: ("chunk.mp4", True, None)
    chunk_module.init_chunk_worker_ai_handler = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.chunk", chunk_module)

    monkeypatch.delitem(sys.modules, "app.core.video.modes.multiprocess", raising=False)
    multiprocess_module = importlib.import_module("app.core.video.modes.multiprocess")

    timeline: list[str] = []

    class _TimelineTimer(_DummyTimer):
        def stop(self) -> None:
            timeline.append("timer_stop")

    class _FakeMultiprocessExecutor:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            self._future = _FakeFuture(raises=RuntimeError("boom"))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ARG002
            return False

        def submit(self, *args, **kwargs):  # noqa: ARG002
            return self._future

    monkeypatch.setattr(multiprocess_module, "QTimer", _TimelineTimer)
    monkeypatch.setattr(multiprocess_module.multiprocessing, "Manager", lambda: _FakeManager())
    monkeypatch.setattr(multiprocess_module, "ProcessPoolExecutor", _FakeMultiprocessExecutor)
    monkeypatch.setattr(multiprocess_module, "as_completed", lambda futures: futures)
    monkeypatch.setattr(
        multiprocess_module,
        "_calculate_chunks",
        lambda _processor, _total_frames, _num_processes, output_path="": [(0, 10, "chunk.mp4")],
    )
    monkeypatch.setattr(multiprocess_module, "should_preserve_audio", lambda _params: False)

    class _DummyProcessor:
        def __init__(self) -> None:
            self.input_path = "input.mp4"
            self.output_path = "output.mp4"
            self.ai_params = {}
            self.config = None
            self.num_processes = 1
            self._is_running = True
            self._progress_timer = None
            self._stop_event = None
            self.logger = _FakeLogger()
            self.status = _DummyEmitter()
            self.progress = _DummyEmitter()
            self.finished = _DummyEmitter()
            self.ffmpeg_processor = SimpleNamespace(is_available=lambda: False)

        def _emit_detailed_progress(self, *args, **kwargs) -> None:  # noqa: ARG002
            return None

        def _process_video_singleprocess(self) -> None:
            timeline.append("fallback")

    processor = _DummyProcessor()
    multiprocess_module.process_video_multiprocess(processor)

    assert timeline.index("timer_stop") < timeline.index("fallback")
