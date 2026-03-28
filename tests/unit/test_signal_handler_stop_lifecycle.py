#!/usr/bin/env python3
"""
SignalHandler 停止流程与线程生命周期回归测试。
"""

from __future__ import annotations

import importlib
import sys
import types

import pytest


class _DummySignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in self._callbacks:
            callback(*args, **kwargs)


class _DummyVideoProcessorThread:
    init_count = 0

    def __init__(self, *args, **kwargs):
        type(self).init_count += 1
        self._running = False
        self.stop_calls = 0
        self.wait_calls = 0
        self.progress = _DummySignal()
        self.status = _DummySignal()
        self.finished = _DummySignal()
        self.error = _DummySignal()
        self.preview_update = _DummySignal()
        self.detailed_progress = _DummySignal()

    def set_running(self, value: bool):
        self._running = bool(value)

    def start(self):
        self._running = True

    def stop(self):
        self.stop_calls += 1

    def wait(self, timeout=None):  # noqa: ARG002
        self.wait_calls += 1
        return not self._running

    def isRunning(self):
        return self._running


class _DummyBatchProcessorThread:
    def __init__(self, *args, **kwargs):
        self._running = False

    def isRunning(self):
        return self._running

    def stop(self):
        return None


class _DummyFileQueueManager:
    def __init__(self, *args, **kwargs):
        pass


class _DummyProcessingStatus:
    PROCESSING = "processing"


class _DummyAIParamsBuilder:
    def build_from_ui(self, **_kwargs):
        return {
            "enable_multiprocess": False,
            "use_pipeline": False,
            "num_processes": 1,
        }


class _DummyPreferences:
    def get_preference(self, _section, _key, default=None):
        return default

    def set_preference(self, _section, _key, _value):
        return None


class _DummyPreviewPanel:
    def show_processing_progress(self, _message=None):
        return None

    def update_processing_preview_from_bgr(self, _frame):
        return None


class _DummyControlPanel:
    def __init__(self):
        self.processing_states = []
        self.reset_calls = 0

    def set_processing_state(self, value):
        self.processing_states.append(value)

    def reset_progress(self):
        self.reset_calls += 1

    def get_advanced_parameters(self):
        return {}

    def update_progress(self, _value):
        return None

    def update_detailed_progress(self, _value):
        return None


class _DummyFilePanel:
    def __init__(self):
        self.export_enabled_values = []

    def set_export_enabled(self, value):
        self.export_enabled_values.append(value)

    def is_manual_mode(self):
        return False


class _DummyLogPanel:
    def __init__(self):
        self.warning_logs = []
        self.error_logs = []
        self.status_logs = []

    def add_warning_log(self, message):
        self.warning_logs.append(message)

    def add_error_message(self, message):
        self.error_logs.append(message)

    def add_status_message(self, message):
        self.status_logs.append(message)

    def add_success_message(self, _message):
        return None


class _DummyStyleManager:
    pass


def _import_signal_handler(monkeypatch: pytest.MonkeyPatch):
    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")

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

    qtcore_module.QObject = _QObject
    qtcore_module.pyqtSignal = lambda *args, **kwargs: _QtSignalDescriptor()
    monkeypatch.setitem(sys.modules, "PyQt6", pyqt6_module)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore_module)

    ui_utils_module = types.ModuleType("app.ui.utils")
    ui_utils_module.MEDIA_IMPORT_FILTER = "all files (*)"
    ui_utils_module.AIParamsBuilder = _DummyAIParamsBuilder
    monkeypatch.setitem(sys.modules, "app.ui.utils", ui_utils_module)

    video_thread_module = types.ModuleType("app.core.video.thread")
    video_thread_module.VideoProcessorThread = _DummyVideoProcessorThread
    monkeypatch.setitem(sys.modules, "app.core.video.thread", video_thread_module)

    frame_reader_module = types.ModuleType("app.core.video.workers.frame_reader")
    frame_reader_module.extract_video_first_frame = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_reader", frame_reader_module)

    batch_module = types.ModuleType("app.ui.widgets.batch.batch_processor_thread")
    batch_module.BatchProcessorThread = _DummyBatchProcessorThread
    batch_module.FileQueueManager = _DummyFileQueueManager
    batch_module.ProcessingStatus = _DummyProcessingStatus
    monkeypatch.setitem(sys.modules, "app.ui.widgets.batch.batch_processor_thread", batch_module)

    monkeypatch.delitem(sys.modules, "app.ui.signal_handler", raising=False)
    return importlib.import_module("app.ui.signal_handler")


def _build_handler(signal_handler_module):
    return signal_handler_module.SignalHandler(
        file_panel=_DummyFilePanel(),
        preview_panel=_DummyPreviewPanel(),
        control_panel=_DummyControlPanel(),
        log_panel=_DummyLogPanel(),
        preferences=_DummyPreferences(),
        style_manager=_DummyStyleManager(),
        main_window=None,
    )


def test_handle_stop_processing_is_async_for_running_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _import_signal_handler(monkeypatch)
    handler = _build_handler(signal_handler_module)
    status_messages = []
    handler.status_updated.connect(status_messages.append)

    thread = _DummyVideoProcessorThread()
    thread.set_running(True)
    handler.video_processor_thread = thread

    handler.handle_stop_processing()

    assert thread.stop_calls == 1
    assert thread.wait_calls == 0
    assert handler.video_processor_thread is thread
    assert handler._single_stop_requested is True
    assert status_messages[-1] == "停止请求已发送，等待线程安全退出"


def test_processing_error_defers_thread_release_until_stopped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _import_signal_handler(monkeypatch)
    handler = _build_handler(signal_handler_module)

    thread = _DummyVideoProcessorThread()
    thread.set_running(True)
    handler.video_processor_thread = thread

    handler._on_processing_error_with_thread("boom", thread)
    assert handler.video_processor_thread is thread
    assert handler.control_panel.reset_calls == 1

    thread.set_running(False)
    handler._on_processing_error_with_thread("boom-again", thread)
    assert handler.video_processor_thread is None


def test_start_processing_rejects_while_previous_thread_still_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _import_signal_handler(monkeypatch)
    handler = _build_handler(signal_handler_module)
    handler.input_file_path = "demo.mp4"

    thread = _DummyVideoProcessorThread()
    thread.set_running(True)
    handler.video_processor_thread = thread
    init_count_before = _DummyVideoProcessorThread.init_count

    handler.handle_start_processing()

    assert _DummyVideoProcessorThread.init_count == init_count_before
    assert any("尚未完全结束" in msg for msg in handler.log_panel.warning_logs)
