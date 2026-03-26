#!/usr/bin/env python3
"""
SignalHandler 单文件入口：VideoProcessorThread 模式参数透传回归测试。

目标：
- 单文件开始处理时，SignalHandler 创建 VideoProcessorThread 必须透传：
  enable_multiprocess / use_pipeline / num_processes
否则 UI 的性能参数无法真正影响运行时策略。
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

    def stop(self):
        return None

    def wait(self, timeout=None):
        return True

    def isRunning(self):
        return False


class _DummyBatchProcessorThread:
    def __init__(self, *args, **kwargs):
        pass


class _DummyFileQueueManager:
    def __init__(self, *args, **kwargs):
        pass


class _DummyProcessingStatus:
    PROCESSING = "processing"


class _DummyAIParamsBuilder:
    def build_from_ui(self, **_kwargs):
        return {
            "auto_detect": True,
            "enable_multiprocess": True,
            "use_pipeline": True,
            "num_processes": 3,
        }


class _DummyPreferences:
    def get_preference(self, section, key, default=None):
        return default

    def set_preference(self, section, key, value):
        return None


class _DummyPreviewPanel:
    def show_processing_progress(self, message=None):
        return None

    def update_processing_preview_from_bgr(self, frame):
        return None


class _DummyControlPanel:
    def set_processing_state(self, value):
        return None

    def get_advanced_parameters(self):
        return {}

    def update_progress(self, value):
        return None

    def update_detailed_progress(self, value):
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

    def add_warning_log(self, message):
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


def test_signal_handler_passes_video_mode_params_to_video_processor_thread(
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
    handler.input_file_path = "demo.mp4"
    handler.handle_start_processing()

    kwargs = _DummyVideoProcessorThread.last_kwargs or {}
    assert kwargs.get("enable_multiprocess") is True
    assert kwargs.get("use_pipeline") is True
    assert kwargs.get("num_processes") == 3
