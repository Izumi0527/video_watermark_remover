#!/usr/bin/env python3
"""
SignalHandler 自动模式切换回归测试

验证切换到自动模式时，界面历史手动框和内存中的手动选择都会被清空。
"""

import importlib
import sys
import types

import pytest


def _build_signal_handler_module(monkeypatch: pytest.MonkeyPatch):
    """按测试范围注入轻量依赖，避免污染其他测试。"""
    video_thread_module = types.ModuleType("app.core.video.thread")

    class _DummyVideoProcessorThread:
        def __init__(self, *args, **kwargs):
            pass

    video_thread_module.VideoProcessorThread = _DummyVideoProcessorThread
    monkeypatch.setitem(sys.modules, "app.core.video.thread", video_thread_module)

    frame_reader_module = types.ModuleType("app.core.video.workers.frame_reader")
    frame_reader_module.extract_video_first_frame = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_reader", frame_reader_module)

    batch_module = types.ModuleType("app.ui.widgets.batch.batch_processor_thread")

    class _DummyBatchProcessorThread:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyFileQueueManager:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyProcessingStatus:
        PROCESSING = "processing"

    batch_module.BatchProcessorThread = _DummyBatchProcessorThread
    batch_module.FileQueueManager = _DummyFileQueueManager
    batch_module.ProcessingStatus = _DummyProcessingStatus
    monkeypatch.setitem(sys.modules, "app.ui.widgets.batch.batch_processor_thread", batch_module)

    if "app.ui.signal_handler" in sys.modules:
        monkeypatch.delitem(sys.modules, "app.ui.signal_handler", raising=False)

    return importlib.import_module("app.ui.signal_handler")


class _DummyPreferences:
    def __init__(self):
        self.values = {}

    def set_preference(self, section, key, value):
        self.values[(section, key)] = value


class _DummyPreviewPanel:
    def __init__(self):
        self.clear_count = 0
        self.switch_count = 0

    def clear_manual_selections(self):
        self.clear_count += 1

    def switch_to_manual_tab(self):
        self.switch_count += 1


class _DummyLogPanel:
    def __init__(self):
        self.status_messages = []

    def add_status_message(self, message):
        self.status_messages.append(message)

    def add_error_message(self, message):
        return None


class _DummyStyleManager:
    pass


def test_handle_auto_mode_changed_clears_manual_selections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """切到自动模式时应清空预览手动框和内存中的手动选择。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    preferences = _DummyPreferences()
    preview_panel = _DummyPreviewPanel()

    handler = SignalHandler(
        file_panel=object(),
        preview_panel=preview_panel,
        control_panel=object(),
        log_panel=_DummyLogPanel(),
        preferences=preferences,
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    handler.manual_selections = [(10, 10, 40, 20)]

    handler.handle_auto_mode_changed(True)

    assert preferences.values[("processing", "auto_mode")] is True
    assert preview_panel.clear_count == 1
    assert handler.manual_selections == []


def test_switching_back_to_manual_mode_keeps_selection_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """方案 A：从自动切回手动时不恢复历史框选，保持空白。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    preferences = _DummyPreferences()
    preview_panel = _DummyPreviewPanel()

    handler = SignalHandler(
        file_panel=object(),
        preview_panel=preview_panel,
        control_panel=object(),
        log_panel=_DummyLogPanel(),
        preferences=preferences,
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    handler.input_file_path = "demo.png"
    handler.manual_selections = [(10, 10, 40, 20)]

    handler.handle_auto_mode_changed(True)
    handler.handle_manual_mode_changed(True)

    assert preferences.values[("processing", "auto_mode")] is False
    assert preview_panel.clear_count == 1
    assert preview_panel.switch_count == 1
    assert handler.manual_selections == []


def test_switching_back_to_manual_mode_shows_guidance_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """切回手动模式时应给出重新框选提示。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    preferences = _DummyPreferences()
    preview_panel = _DummyPreviewPanel()
    received_messages = []

    handler = SignalHandler(
        file_panel=object(),
        preview_panel=preview_panel,
        control_panel=object(),
        log_panel=_DummyLogPanel(),
        preferences=preferences,
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    handler.input_file_path = "demo.png"
    handler.status_updated.connect(received_messages.append)

    handler.handle_manual_mode_changed(True)

    assert received_messages[-1] == "已进入手动模式，请重新框选水印区域"


def test_switching_back_to_manual_mode_syncs_message_to_log_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """切回手动模式时，状态栏提示应与日志面板提示保持一致。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    preferences = _DummyPreferences()
    preview_panel = _DummyPreviewPanel()
    log_panel = _DummyLogPanel()
    received_messages = []

    handler = SignalHandler(
        file_panel=object(),
        preview_panel=preview_panel,
        control_panel=object(),
        log_panel=log_panel,
        preferences=preferences,
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    handler.input_file_path = "demo.png"
    handler.status_updated.connect(received_messages.append)
    handler.status_updated.connect(log_panel.add_status_message)

    handler.handle_manual_mode_changed(True)

    assert received_messages[-1] == "已进入手动模式，请重新框选水印区域"
    assert log_panel.status_messages[-1] == received_messages[-1]
