#!/usr/bin/env python3
"""
SignalHandler 批处理配置透传回归测试。
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


class _DummyVideoProcessorThread:
    def __init__(self, *args, **kwargs):
        pass


class _DummyFileQueueManager:
    def __init__(self, *args, **kwargs):
        self.queue = []

    def add_file(self, input_path, output_path=None):
        self.queue.append({"input_path": input_path, "output_path": output_path})
        return self.queue[-1]

    def get_queue(self):
        return list(self.queue)


class _DummyProcessingStatus:
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class _DummyAIParamsBuilder:
    last_build_from_ui_kwargs = None

    def build_from_ui(self, **_kwargs):
        type(self).last_build_from_ui_kwargs = dict(_kwargs)
        return {
            "auto_detect": True,
            "enable_multiprocess": True,
            "use_pipeline": False,
            "num_processes": 2,
        }

    def build_batch_config(self, _advanced_params, **_kwargs):
        return {
            "max_concurrent_files": 2,
            "auto_retry_failed": False,
            "max_retry_count": 1,
        }


class _DummyPreferences:
    def get_preference(self, section, key, default=None):
        return default

    def set_preference(self, section, key, value):
        return None


class _DummyPreviewPanel:
    def show_processing_progress(self, message=None):
        return None


class _DummyControlPanel:
    def set_processing_state(self, value):
        return None

    def get_advanced_parameters(self):
        return {"batch_max_concurrent_files": 2, "batch_auto_retry_failed": False}

    def update_progress(self, value):
        return None


class _DummyFilePanel:
    def set_export_enabled(self, value):
        return None

    def hide_queue(self):
        return None

    def show_queue(self):
        return None

    def update_queue_display(self, queue):
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


class _DummyStyleManager:
    pass


def _import_signal_handler_with_patches(monkeypatch: pytest.MonkeyPatch):
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
    signal_handler_module = importlib.import_module("app.ui.signal_handler")
    monkeypatch.setattr(signal_handler_module, "AIParamsBuilder", _DummyAIParamsBuilder)
    return signal_handler_module


def test_signal_handler_uses_snapshot_batch_config_instead_of_hardcoded_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _import_signal_handler_with_patches(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    handler = SignalHandler(
        file_panel=_DummyFilePanel(),
        preview_panel=_DummyPreviewPanel(),
        control_panel=_DummyControlPanel(),
        log_panel=_DummyLogPanel(),
        preferences=_DummyPreferences(),
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    handler.file_queue_manager.add_file("first.mp4", "first_processed.mp4")

    handler._start_batch_processing()

    kwargs = _DummyBatchProcessorThread.last_kwargs or {}
    assert kwargs["max_concurrent_files"] == 2
    assert kwargs["auto_retry_failed"] is False
    assert kwargs["max_retry_count"] == 1
    assert _DummyAIParamsBuilder.last_build_from_ui_kwargs["input_file_path"] == "first.mp4"
