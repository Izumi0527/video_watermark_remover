#!/usr/bin/env python3
"""
处理中媒体类型文案回归测试

验证图片和视频在处理中阶段会显示各自正确的提示文案。
"""

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
    def __init__(self, *args, **kwargs):
        self.progress = _DummySignal()
        self.status = _DummySignal()
        self.finished = _DummySignal()
        self.error = _DummySignal()
        self.preview_update = _DummySignal()
        self.detailed_progress = _DummySignal()
        self.started = False

    def start(self):
        self.started = True

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
        self.updated = []

    def clear_queue(self):
        return None

    def update_file_status(self, *args, **kwargs):
        self.updated.append((args, kwargs))

    def get_queue(self):
        return []


class _DummyProcessingStatus:
    PROCESSING = "processing"


class _DummyAIParamsBuilder:
    def build_from_ui(self, **kwargs):
        return {"auto_detect": True}


class _DummyPreferences:
    def get_preference(self, section, key, default=None):
        return default

    def set_preference(self, section, key, value):
        return None


class _DummyPreviewPanel:
    def __init__(self):
        self.processing_messages = []

    def show_processing_progress(self, message=None):
        self.processing_messages.append(message)

    def update_processing_preview_from_bgr(self, frame):
        return None


class _DummyControlPanel:
    def __init__(self):
        self.processing_states = []

    def set_processing_state(self, value):
        self.processing_states.append(value)

    def get_advanced_parameters(self):
        return {}

    def update_progress(self, value):
        return None

    def update_detailed_progress(self, value):
        return None


class _DummyFilePanel:
    def __init__(self):
        self.export_enabled_values = []
        self.queue_display = []

    def set_export_enabled(self, value):
        self.export_enabled_values.append(value)

    def hide_queue(self):
        return None

    def show_queue(self):
        return None

    def update_queue_display(self, queue):
        self.queue_display = queue

    def is_manual_mode(self):
        return False


class _DummyLogPanel:
    def __init__(self):
        self.status_messages = []
        self.error_messages = []

    def add_status_message(self, message):
        self.status_messages.append(message)

    def add_error_message(self, message):
        self.error_messages.append(message)

    def add_warning_log(self, message):
        return None


class _DummyStyleManager:
    pass


def _build_signal_handler_module(monkeypatch: pytest.MonkeyPatch):
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


def _build_handler(signal_handler_module):
    SignalHandler = signal_handler_module.SignalHandler
    preview_panel = _DummyPreviewPanel()
    log_panel = _DummyLogPanel()
    handler = SignalHandler(
        file_panel=_DummyFilePanel(),
        preview_panel=preview_panel,
        control_panel=_DummyControlPanel(),
        log_panel=log_panel,
        preferences=_DummyPreferences(),
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    return handler, preview_panel, log_panel


def test_handle_start_processing_shows_image_specific_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """图片开始处理时应显示“正在处理图片”。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, preview_panel, _ = _build_handler(signal_handler_module)
    received_messages = []
    handler.status_updated.connect(received_messages.append)
    handler.input_file_path = "demo.jpg"

    handler.handle_start_processing()

    assert preview_panel.processing_messages[-1] == "⏳ 正在处理图片，请稍候..."
    # 开始消息之后还会追加"处理模式运行时摘要"，因此校验成员而非末位
    assert "开始处理图片..." in received_messages


def test_handle_start_processing_shows_video_specific_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """视频开始处理时应显示“正在处理视频”。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, preview_panel, _ = _build_handler(signal_handler_module)
    received_messages = []
    handler.status_updated.connect(received_messages.append)
    handler.input_file_path = "demo.mp4"

    handler.handle_start_processing()

    assert preview_panel.processing_messages[-1] == "⏳ 正在处理视频，请稍候..."
    # 开始消息之后还会追加"处理模式运行时摘要"，因此校验成员而非末位
    assert "开始处理视频..." in received_messages


def test_batch_file_changed_shows_video_specific_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """批处理当前文件切换到视频时也应显示视频文案。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, preview_panel, _ = _build_handler(signal_handler_module)
    received_messages = []
    handler.status_updated.connect(received_messages.append)

    handler._on_batch_file_changed(0, "episode.mp4")

    assert preview_panel.processing_messages[-1] == "⏳ 正在处理视频，请稍候..."
    assert received_messages[-1] == "正在处理视频: episode.mp4"
