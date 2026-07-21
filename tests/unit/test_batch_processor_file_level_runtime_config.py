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
    monkeypatch.setattr(
        batch_module.os.path, "exists", lambda path: _normalize(path) in existing_paths
    )
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


def test_batch_processor_remove_pending_file_marks_waiting_file_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_pyqt_core_stub(monkeypatch)
    placeholder_video_thread_module = types.ModuleType("app.core.video.thread")
    placeholder_video_thread_module.VideoProcessorThread = object
    monkeypatch.setitem(sys.modules, "app.core.video.thread", placeholder_video_thread_module)
    monkeypatch.delitem(sys.modules, "app.ui.widgets.batch.batch_processor_thread", raising=False)

    batch_module = importlib.import_module("app.ui.widgets.batch.batch_processor_thread")
    BatchProcessorThread = batch_module.BatchProcessorThread

    batch = BatchProcessorThread(
        queue=[
            {
                "file_id": "file-1",
                "input_path": "C:/tmp/a.jpg",
                "output_path": "C:/tmp/a_out.jpg",
                "status": batch_module.ProcessingStatus.WAITING,
                "progress": 0,
                "error_message": "",
            }
        ],
        ai_params={},
        file_ai_params_by_index={0: {}},
        file_ai_params_by_file_id={"file-1": {}},
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files=1,
        auto_retry_failed=False,
    )

    class _FakeFuture:
        def __init__(self):
            self.cancel_called = False

        def cancel(self):
            self.cancel_called = True
            return True

        def cancelled(self):
            return self.cancel_called

    future = _FakeFuture()
    batch._futures = {future: 0}
    batch._future_file_ids = {future: "file-1"}

    assert batch.remove_pending_file("file-1") is True
    assert future.cancel_called is True
    assert batch._is_file_removed("file-1") is True
