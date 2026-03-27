#!/usr/bin/env python3
"""
SignalHandler 输出参数链路回归测试。
"""

from __future__ import annotations

import importlib
import sys
import types

import pytest


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


class _DummySignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in self._callbacks:
            callback(*args, **kwargs)


class _DummyVideoProcessorThread:
    last_kwargs = None

    def __init__(self, *args, **kwargs):
        type(self).last_kwargs = dict(kwargs)
        self.progress = _DummySignal()
        self.status = _DummySignal()
        self.finished = _DummySignal()
        self.error = _DummySignal()
        self.preview_update = _DummySignal()
        self.detailed_progress = _DummySignal()

    def start(self):
        return None


class _DummyBatchProcessorThread:
    last_kwargs = None

    def __init__(self, *args, **kwargs):
        type(self).last_kwargs = dict(kwargs)
        self.current_file_changed = _DummySignal()
        self.file_progress = _DummySignal()
        self.overall_progress = _DummySignal()
        self.file_completed = _DummySignal()
        self.batch_completed = _DummySignal()
        self.status_message = _DummySignal()
        self.should_stop = False

    def start(self):
        return None


class _DummyPreferences:
    def get_preference(self, _section, _key, default=None):
        return default

    def set_preference(self, _section, _key, _value):
        return None


class _DummyPreviewPanel:
    def show_processing_progress(self, _message=None):
        return None

    def update_processing_preview_from_bgr(self, _image):
        return None

    def set_image(self, _path):
        return None

    def set_manual_selection_image(self, _path):
        return None

    def set_image_from_array(self, _image):
        return None

    def set_manual_selection_image_from_array(self, _image):
        return None


class _DummyControlPanel:
    def __init__(self):
        self.processing_states = []

    def set_processing_state(self, value):
        self.processing_states.append(value)

    def get_advanced_parameters(self):
        return {
            "output_format": "JPG",
            "compression_quality": 88,
            "add_suffix": True,
            "add_timestamp": False,
            "preserve_audio": False,
        }

    def update_progress(self, _value):
        return None

    def update_detailed_progress(self, _value):
        return None

    def set_start_button_enabled(self, _value):
        return None


class _DummyFilePanel:
    def set_export_enabled(self, _value):
        return None

    def hide_queue(self):
        return None

    def show_queue(self):
        return None

    def update_queue_display(self, _queue):
        return None

    def is_manual_mode(self):
        return False


class _DummyLogPanel:
    def add_status_message(self, _message):
        return None

    def add_error_message(self, _message):
        return None

    def add_warning_log(self, _message):
        return None

    def add_success_message(self, _message):
        return None


class _DummyStyleManager:
    pass


class _DummyAIParamsBuilder:
    def build_from_ui(self, **kwargs):
        input_file_path = kwargs.get("input_file_path")
        if str(input_file_path).lower().endswith(".mp4"):
            return {
                "output_format": "jpg",
                "compression_quality": 88,
                "add_processed_suffix": True,
                "add_timestamp": False,
                "preserve_audio": False,
                "enable_multiprocess": False,
                "use_pipeline": False,
                "num_processes": 1,
            }
        return {
            "output_format": "jpg",
            "compression_quality": 88,
            "add_processed_suffix": True,
            "add_timestamp": False,
            "preserve_audio": True,
            "enable_multiprocess": False,
            "use_pipeline": False,
            "num_processes": 1,
        }

    def build_batch_config(self, _advanced_params, **_kwargs):
        return {
            "max_concurrent_files": 1,
            "auto_retry_failed": True,
            "max_retry_count": 0,
        }


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
    qtcore_module.QThread = _QObject
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

    monkeypatch.delitem(sys.modules, "app.ui.signal_handler", raising=False)
    signal_handler_module = importlib.import_module("app.ui.signal_handler")
    monkeypatch.setattr(signal_handler_module, "BatchProcessorThread", _DummyBatchProcessorThread)
    return signal_handler_module


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


def test_signal_handler_single_file_uses_resolved_output_path(monkeypatch: pytest.MonkeyPatch) -> None:
    signal_handler_module = _import_signal_handler(monkeypatch)
    handler = _build_handler(signal_handler_module)
    handler.input_file_path = "C:/tmp/source.png"
    handler.is_batch_mode = False

    handler.handle_start_processing()

    assert _normalize(_DummyVideoProcessorThread.last_kwargs["output_path"]) == "C:/tmp/source_processed.jpg"


def test_signal_handler_batch_processing_rewrites_queue_output_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    signal_handler_module = _import_signal_handler(monkeypatch)
    handler = _build_handler(signal_handler_module)
    handler.file_queue_manager.add_file("C:/tmp/video.mp4")

    handler._start_batch_processing()

    queue = handler.file_queue_manager.get_queue()
    assert _normalize(queue[0]["output_path"]) == "C:/tmp/video_processed.mp4"
