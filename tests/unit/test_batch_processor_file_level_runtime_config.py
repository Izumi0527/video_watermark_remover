#!/usr/bin/env python3
"""
BatchProcessorThread 文件级运行时配置测试。
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


class _DummySignal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in self._callbacks:
            callback(*args, **kwargs)


class _QtSignalDescriptor:
    def __set_name__(self, owner, name):
        self._storage_name = f"__signal_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        signal = getattr(instance, self._storage_name, None)
        if signal is None:
            signal = _DummySignal()
            setattr(instance, self._storage_name, signal)
        return signal


class _QObject:
    def __init__(self, *args, **kwargs):
        super().__init__()


def _normalize(path: str | Path) -> str:
    return str(Path(path)).replace("\\", "/")


def _install_pyqt_core_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")
    qtcore_module.QObject = _QObject
    qtcore_module.QThread = _QObject
    qtcore_module.pyqtSignal = lambda *args, **kwargs: _QtSignalDescriptor()
    monkeypatch.setitem(sys.modules, "PyQt6", pyqt6_module)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore_module)


def test_batch_processor_uses_file_level_ai_params_when_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_pyqt_core_stub(monkeypatch)

    placeholder_video_thread_module = types.ModuleType("app.core.video.thread")
    placeholder_video_thread_module.VideoProcessorThread = object
    monkeypatch.setitem(sys.modules, "app.core.video.thread", placeholder_video_thread_module)
    monkeypatch.delitem(sys.modules, "app.ui.widgets.batch.batch_processor_thread", raising=False)

    batch_module = importlib.import_module("app.ui.widgets.batch.batch_processor_thread")
    BatchProcessorThread = batch_module.BatchProcessorThread
    ProcessingStatus = batch_module.ProcessingStatus

    captured_by_input: dict[str, dict] = {}
    existing_paths: set[str] = set()

    class _DummyVideoProcessorThread:
        def __init__(self, *args, **kwargs):
            self.input_path = kwargs["input_path"]
            self.output_path = kwargs["output_path"]
            captured_by_input[self.input_path] = dict(kwargs)
            self.progress = _DummySignal()
            self.finished = _DummySignal()
            self.error = _DummySignal()

        def stop(self):
            return None

        def run(self):
            existing_paths.add(_normalize(self.output_path))
            self.finished.emit(self.output_path)

    monkeypatch.setattr(batch_module, "VideoProcessorThread", _DummyVideoProcessorThread)
    monkeypatch.setattr(batch_module.os.path, "exists", lambda path: _normalize(path) in existing_paths)
    monkeypatch.setattr(
        batch_module.os,
        "makedirs",
        lambda path, exist_ok=False: existing_paths.add(_normalize(path)),
    )

    base_path = Path("virtual_batch_processor")
    first_input = base_path / "first.jpg"
    second_input = base_path / "second.mp4"
    existing_paths.update(
        {
            _normalize(base_path),
            _normalize(first_input),
            _normalize(second_input),
        }
    )

    batch = BatchProcessorThread(
        queue=[],
        ai_params={
            "enable_multiprocess": False,
            "use_pipeline": False,
            "num_processes": 1,
        },
        file_ai_params_by_index={
            0: {
                "enable_multiprocess": False,
                "use_pipeline": False,
                "num_processes": 1,
            },
            1: {
                "enable_multiprocess": True,
                "use_pipeline": True,
                "num_processes": 4,
            },
        },
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files=1,
        auto_retry_failed=False,
    )

    first_result = batch._process_single_file(
        str(first_input),
        str(base_path / "first_out.jpg"),
        0,
    )
    second_result = batch._process_single_file(
        str(second_input),
        str(base_path / "second_out.mp4"),
        1,
    )

    assert first_result[0] == ProcessingStatus.COMPLETED
    assert second_result[0] == ProcessingStatus.COMPLETED
    assert captured_by_input[str(first_input)]["use_pipeline"] is False
    assert captured_by_input[str(first_input)]["num_processes"] == 1
    assert captured_by_input[str(second_input)]["use_pipeline"] is True
    assert captured_by_input[str(second_input)]["enable_multiprocess"] is True
    assert captured_by_input[str(second_input)]["num_processes"] == 4


def test_batch_processing_widget_keeps_existing_file_level_output_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_pyqt_core_stub(monkeypatch)

    qtwidgets_module = types.ModuleType("PyQt6.QtWidgets")

    class _QWidget:
        def __init__(self, *args, **kwargs):
            super().__init__()

    class _MessageBox:
        @staticmethod
        def information(*args, **kwargs):
            return None

        @staticmethod
        def warning(*args, **kwargs):
            return None

    qtwidgets_module.QWidget = _QWidget
    qtwidgets_module.QMessageBox = _MessageBox
    monkeypatch.setitem(sys.modules, "PyQt6.QtWidgets", qtwidgets_module)

    placeholder_file_manager_module = types.ModuleType("app.ui.widgets.batch.batch_file_manager")
    placeholder_file_manager_module.BatchFileManager = object
    monkeypatch.setitem(
        sys.modules,
        "app.ui.widgets.batch.batch_file_manager",
        placeholder_file_manager_module,
    )

    placeholder_batch_ui_module = types.ModuleType("app.ui.widgets.batch.batch_ui_components")
    placeholder_batch_ui_module.BatchUIComponents = object
    monkeypatch.setitem(
        sys.modules,
        "app.ui.widgets.batch.batch_ui_components",
        placeholder_batch_ui_module,
    )

    placeholder_batch_thread_module = types.ModuleType("app.ui.widgets.batch.batch_processor_thread")

    class _PlaceholderBatchProcessorThread:
        def __init__(self, *args, **kwargs):
            self.current_file_changed = _DummySignal()
            self.file_progress = _DummySignal()
            self.overall_progress = _DummySignal()
            self.file_completed = _DummySignal()
            self.batch_completed = _DummySignal()
            self.status_message = _DummySignal()

        def start(self):
            return None

        def isRunning(self):
            return False

    class _PlaceholderProcessingStatus:
        WAITING = "waiting"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    placeholder_batch_thread_module.BatchProcessorThread = _PlaceholderBatchProcessorThread
    placeholder_batch_thread_module.ProcessingStatus = _PlaceholderProcessingStatus
    monkeypatch.setitem(
        sys.modules,
        "app.ui.widgets.batch.batch_processor_thread",
        placeholder_batch_thread_module,
    )

    monkeypatch.delitem(sys.modules, "app.ui.widgets.batch.batch_processing_widget", raising=False)
    widget_module = importlib.import_module("app.ui.widgets.batch.batch_processing_widget")

    class _DummyQueueManager:
        def __init__(self):
            self.queue = [
                {
                    "input_path": "C:/tmp/a.jpg",
                    "output_path": "C:/tmp/a_custom.jpg",
                },
                {
                    "input_path": "C:/tmp/b.mp4",
                    "output_path": "C:/tmp/b_custom.mp4",
                },
            ]
            self.update_calls: list[tuple[int, str]] = []

        def get_queue(self):
            return self.queue

        def update_file_output_path(self, index: int, output_path: str) -> None:
            self.update_calls.append((index, output_path))
            self.queue[index]["output_path"] = output_path

    class _DummyFileManager:
        def __init__(self, queue_manager):
            self._queue_manager = queue_manager
            self.reset_count = 0

        def get_queue_manager(self):
            return self._queue_manager

        def reset_all_files_to_waiting(self):
            self.reset_count += 1

    class _DummyBatchThread:
        last_kwargs = None

        def __init__(self, *args, **kwargs):
            type(self).last_kwargs = dict(kwargs)
            self.current_file_changed = _DummySignal()
            self.file_progress = _DummySignal()
            self.overall_progress = _DummySignal()
            self.file_completed = _DummySignal()
            self.batch_completed = _DummySignal()
            self.status_message = _DummySignal()

        def start(self):
            return None

        def isRunning(self):
            return False

    monkeypatch.setattr(widget_module, "BatchProcessorThread", _DummyBatchThread)

    class _DummyEmitter:
        def __init__(self):
            self.count = 0

        def emit(self):
            self.count += 1

    queue_manager = _DummyQueueManager()

    class _FakeWidget:
        pass

    fake = _FakeWidget()
    fake._stop_requested = False
    fake.file_manager = _DummyFileManager(queue_manager)
    fake.batch_processor = None
    fake.ai_params = {"add_processed_suffix": True}
    fake.config = None
    fake.preloaded_ai_handler = None
    fake.max_concurrent_files = 1
    fake.auto_retry_failed = True
    fake.max_retry_count = 0
    fake.processing_started = _DummyEmitter()
    fake._set_processing_ui_state = lambda processing: None
    fake._on_current_file_changed = lambda *args, **kwargs: None
    fake._on_file_progress = lambda *args, **kwargs: None
    fake._on_overall_progress = lambda *args, **kwargs: None
    fake._on_file_completed = lambda *args, **kwargs: None
    fake._on_batch_completed = lambda *args, **kwargs: None
    fake._on_status_message = lambda *args, **kwargs: None

    widget_module.BatchProcessingWidget.start_batch_processing(fake)

    assert queue_manager.update_calls == []
    assert queue_manager.queue[0]["output_path"] == "C:/tmp/a_custom.jpg"
    assert queue_manager.queue[1]["output_path"] == "C:/tmp/b_custom.mp4"
