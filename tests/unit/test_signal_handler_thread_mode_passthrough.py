#!/usr/bin/env python3
"""
SignalHandler 单文件入口：VideoProcessorThread 模式参数透传回归测试。

目标：
- 单文件开始处理时，SignalHandler 创建 VideoProcessorThread 必须透传：
  runtime_performance（统一运行时快照）
否则 UI 的性能参数虽然在界面中是单值模式，运行时仍会退回分散布尔字段。
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
        self._running = False
        self.stop_called = False
        self.wait_calls = []
        self.progress = _DummySignal()
        self.status = _DummySignal()
        self.finished = _DummySignal()
        self.error = _DummySignal()
        self.preview_update = _DummySignal()
        self.detailed_progress = _DummySignal()

    def start(self):
        self._running = True
        return None

    def stop(self):
        self.stop_called = True
        return None

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        return not self._running

    def isRunning(self):
        return self._running


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
            "processing_mode": "pipeline",
            "resolved_processing_mode": "single_process",
            "enable_multiprocess": False,
            "use_pipeline": False,
            "num_processes": 1,
            "mode_restriction_reason": "gpu_deep_backend_serial_only",
        }

    def build_resolved_performance_config(self, **_kwargs):
        class _ResolvedConfig:
            def to_manifest_dict(self):
                return {
                    "requested_processing_mode": "pipeline",
                    "resolved_processing_mode": "single_process",
                    "worker_count": 1,
                    "enable_multiprocess": False,
                    "use_pipeline": False,
                    "gpu_memory_budget_mb": 2048,
                    "enable_cache": True,
                    "cache_size_mb": 512,
                    "batch_max_concurrent_files": 1,
                    "batch_auto_retry_failed": True,
                    "batch_max_retry_count": 3,
                    "mode_restriction_reason": "gpu_deep_backend_serial_only",
                }

        return _ResolvedConfig()


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

    def set_image(self, path):
        return None

    def set_manual_selection_image(self, path):
        return None


class _DummyControlPanel:
    def __init__(self):
        self.processing_states = []
        self.reset_progress_calls = 0

    def set_processing_state(self, value):
        self.processing_states.append(value)

    def get_advanced_parameters(self):
        return {}

    def update_progress(self, value):
        return None

    def update_detailed_progress(self, value):
        return None

    def reset_progress(self):
        self.reset_progress_calls += 1


class _DummyFilePanel:
    def __init__(self):
        self.export_enabled_values = []

    def set_export_enabled(self, value):
        self.export_enabled_values.append(value)

    def hide_queue(self):
        return None

    def show_queue(self):
        return None

    def update_queue_display(self, queue):
        return None

    def is_manual_mode(self):
        return False


class _DummyLogPanel:
    def __init__(self):
        self.warning_logs = []
        self.error_messages = []
        self.status_messages = []
        self.success_messages = []

    def add_status_message(self, _message):
        self.status_messages.append(_message)

    def add_error_message(self, _message):
        self.error_messages.append(_message)

    def add_warning_log(self, message):
        self.warning_logs.append(message)

    def add_success_message(self, message):
        self.success_messages.append(message)


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


def test_signal_handler_passes_runtime_performance_to_video_processor_thread(
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
    runtime_performance = kwargs.get("runtime_performance") or {}
    assert runtime_performance.get("requested_processing_mode") == "pipeline"
    assert runtime_performance.get("resolved_processing_mode") == "single_process"
    assert runtime_performance.get("worker_count") == 1
    assert runtime_performance.get("mode_restriction_reason") == "gpu_deep_backend_serial_only"


def test_handle_stop_processing_does_not_block_when_thread_still_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _import_signal_handler_with_patches(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    control_panel = _DummyControlPanel()
    file_panel = _DummyFilePanel()
    handler = SignalHandler(
        file_panel=file_panel,
        preview_panel=_DummyPreviewPanel(),
        control_panel=control_panel,
        log_panel=_DummyLogPanel(),
        preferences=_DummyPreferences(),
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    status_messages = []
    handler.status_updated.connect(lambda msg: status_messages.append(msg))

    handler.input_file_path = "demo.mp4"
    handler.handle_start_processing()

    thread = handler.video_processor_thread
    assert thread is not None
    thread._running = True

    handler.handle_stop_processing()

    assert thread.stop_called is True
    assert thread.wait_calls == []
    assert handler.video_processor_thread is thread
    assert status_messages[-1] == "停止请求已发送，等待线程安全退出"
    assert control_panel.processing_states[-1] is True
    assert control_panel.reset_progress_calls == 0
    assert file_panel.export_enabled_values[-1] is False


def test_handle_stop_processing_cleans_up_when_thread_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _import_signal_handler_with_patches(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    control_panel = _DummyControlPanel()
    handler = SignalHandler(
        file_panel=_DummyFilePanel(),
        preview_panel=_DummyPreviewPanel(),
        control_panel=control_panel,
        log_panel=_DummyLogPanel(),
        preferences=_DummyPreferences(),
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    status_messages = []
    handler.status_updated.connect(lambda msg: status_messages.append(msg))

    handler.input_file_path = "demo.mp4"
    handler.handle_start_processing()

    thread = handler.video_processor_thread
    assert thread is not None
    thread._running = False

    handler.handle_stop_processing()

    assert thread.stop_called is True
    assert handler.video_processor_thread is None
    assert status_messages[-1] == "处理已停止"
    assert control_panel.processing_states[-1] is False
    assert control_panel.reset_progress_calls == 1


def test_stale_finished_callback_does_not_override_active_thread(
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

    active_thread = _DummyVideoProcessorThread()
    stale_thread = _DummyVideoProcessorThread()
    handler.video_processor_thread = active_thread

    handler._on_processing_finished_with_thread("", stale_thread)

    assert handler.video_processor_thread is active_thread
