#!/usr/bin/env python3
"""
SignalHandler 批处理清单追溯回归测试

覆盖两个高风险边界：
1. 批处理结束后导出 manifest 仍应保留最近一次运行配置。
2. 清空或替换队列后，不应继续复用旧批次快照。
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

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
    def __init__(
        self,
        queue=None,
        ai_params=None,
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files=4,
        auto_retry_failed=True,
        max_retry_count=3,
        parent=None,
    ):
        self.queue = queue or []
        self.ai_params = ai_params or {}
        self.config = config
        self.preloaded_ai_handler = preloaded_ai_handler
        self.max_concurrent_files = max_concurrent_files
        self.auto_retry_failed = auto_retry_failed
        self.max_retry_count = max_retry_count
        self.parent = parent
        self.should_stop = False
        self.current_file_changed = _DummySignal()
        self.file_progress = _DummySignal()
        self.overall_progress = _DummySignal()
        self.file_completed = _DummySignal()
        self.batch_completed = _DummySignal()
        self.status_message = _DummySignal()
        self.started = False

    def start(self) -> None:
        self.started = True


class _DummyVideoProcessorThread:
    def __init__(self, *args, **kwargs):
        pass


class _DummyPreferences:
    def __init__(self):
        self.values = {}

    def get_preference(self, section, key, default=None):
        return self.values.get((section, key), default)

    def set_preference(self, section, key, value):
        self.values[(section, key)] = value


class _DummyFilePanel:
    def __init__(self):
        self.export_enabled_values = []
        self.queue_display = []
        self.hide_count = 0
        self.show_count = 0

    def set_export_enabled(self, value):
        self.export_enabled_values.append(value)

    def update_queue_display(self, queue):
        self.queue_display = queue

    def hide_queue(self):
        self.hide_count += 1

    def show_queue(self):
        self.show_count += 1

    def is_manual_mode(self):
        return False


class _DummyPreviewPanel:
    def __init__(self):
        self.images = []

    def set_image(self, path):
        self.images.append(path)

    def set_manual_selection_image(self, path):
        self.images.append(path)

    def set_image_from_array(self, image):
        self.images.append(image)


class _DummyControlPanel:
    def __init__(self):
        self.processing_states = []
        self.start_button_enabled = []

    def set_processing_state(self, value):
        self.processing_states.append(value)

    def get_advanced_parameters(self):
        return {}

    def set_start_button_enabled(self, value):
        self.start_button_enabled.append(value)

    def update_progress(self, value):
        return None


class _DummyLogPanel:
    def __init__(self):
        self.status_messages = []
        self.success_messages = []
        self.warning_messages = []
        self.error_messages = []

    def add_status_message(self, message):
        self.status_messages.append(message)

    def add_success_message(self, message):
        self.success_messages.append(message)

    def add_warning_log(self, message):
        self.warning_messages.append(message)

    def add_error_message(self, message):
        self.error_messages.append(message)


class _DummyStyleManager:
    pass


def _build_signal_handler_module(monkeypatch: pytest.MonkeyPatch):
    video_thread_module = types.ModuleType("app.core.video.thread")
    video_thread_module.VideoProcessorThread = _DummyVideoProcessorThread
    monkeypatch.setitem(sys.modules, "app.core.video.thread", video_thread_module)

    frame_reader_module = types.ModuleType("app.core.video.workers.frame_reader")
    frame_reader_module.extract_video_first_frame = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_reader", frame_reader_module)

    monkeypatch.delitem(sys.modules, "app.ui.widgets.batch.batch_processor_thread", raising=False)
    monkeypatch.delitem(sys.modules, "app.ui.signal_handler", raising=False)
    signal_handler_module = importlib.import_module("app.ui.signal_handler")
    monkeypatch.setattr(signal_handler_module, "BatchProcessorThread", _DummyBatchProcessorThread)
    return signal_handler_module


def _build_handler(signal_handler_module):
    preferences = _DummyPreferences()
    file_panel = _DummyFilePanel()
    preview_panel = _DummyPreviewPanel()
    control_panel = _DummyControlPanel()
    log_panel = _DummyLogPanel()
    handler = signal_handler_module.SignalHandler(
        file_panel=file_panel,
        preview_panel=preview_panel,
        control_panel=control_panel,
        log_panel=log_panel,
        preferences=preferences,
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    return handler, preferences, file_panel, preview_panel, control_panel, log_panel


def _read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_export_manifest_keeps_last_batch_runtime_config_after_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)

    builder_result = {"auto_detect": True, "quality_level": 3}

    class _DummyAIParamsBuilder:
        def build_from_ui(self, **kwargs):
            return dict(builder_result)

    monkeypatch.setattr(signal_handler_module, "AIParamsBuilder", _DummyAIParamsBuilder)

    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["first.jpg", "second.jpg"])
    handler._start_batch_processing()
    handler._on_batch_completed()

    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setattr(
        handler,
        "_show_save_dialog",
        lambda *args, **kwargs: (str(manifest_path), "JSON文件 (*.json)"),
    )

    handler.handle_export_batch_manifest(parent_widget=None)
    manifest = _read_manifest(manifest_path)

    assert manifest["run"]["ai_params_source"] == "last_batch"
    assert manifest["run"]["ai_params"] == builder_result
    assert manifest["batch"]["max_concurrent_files"] == 4
    assert manifest["batch"]["auto_retry_failed"] is True
    assert manifest["batch"]["max_retry_count"] == 3


def test_handle_queue_clear_clears_last_batch_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, *_ = _build_handler(signal_handler_module)

    handler._last_batch_ai_params = {"stale": True}
    handler._last_batch_ai_params_generated_at = "2026-03-24 10:00:00"
    handler._last_batch_config = {"max_concurrent_files": 4}

    handler.handle_queue_clear()

    assert handler._last_batch_ai_params is None
    assert handler._last_batch_ai_params_generated_at is None
    assert handler._last_batch_config is None


def test_switching_to_single_file_clears_last_batch_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, *_ = _build_handler(signal_handler_module)

    handler._last_batch_ai_params = {"stale": True}
    handler._last_batch_ai_params_generated_at = "2026-03-24 10:00:00"
    handler._last_batch_config = {"max_concurrent_files": 4}

    handler._handle_single_file("demo.jpg")

    assert handler._last_batch_ai_params is None
    assert handler._last_batch_ai_params_generated_at is None
    assert handler._last_batch_config is None


def test_replacing_queue_invalidates_stale_batch_snapshot_before_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)

    builder_result = {"stale": True}

    class _DummyAIParamsBuilder:
        def build_from_ui(self, **kwargs):
            return dict(builder_result)

    monkeypatch.setattr(signal_handler_module, "AIParamsBuilder", _DummyAIParamsBuilder)

    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["old.jpg", "old2.jpg"])
    handler._start_batch_processing()
    handler._on_batch_completed()

    builder_result = {"fresh": True, "auto_detect": True}
    handler._handle_multiple_files(["new.jpg", "new2.jpg"])

    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setattr(
        handler,
        "_show_save_dialog",
        lambda *args, **kwargs: (str(manifest_path), "JSON文件 (*.json)"),
    )

    handler.handle_export_batch_manifest(parent_widget=None)
    manifest = _read_manifest(manifest_path)

    assert manifest["run"]["ai_params_source"] == "computed_at_export"
    assert manifest["run"]["ai_params"] == builder_result
