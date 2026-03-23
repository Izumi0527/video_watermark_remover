#!/usr/bin/env python3
"""
导入文件对话框过滤器回归测试

验证主导入入口与批量导入入口默认都先显示图片和视频联合过滤。
"""

import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

EXPECTED_IMPORT_FILTER = (
    "支持的文件 (*.mp4 *.avi *.mkv *.mov *.jpg *.jpeg *.png *.bmp);;"
    "视频文件 (*.mp4 *.avi *.mkv *.mov);;"
    "图片文件 (*.jpg *.jpeg *.png *.bmp);;"
    "所有文件 (*)"
)


def _install_signal_handler_stubs(monkeypatch: pytest.MonkeyPatch):
    """注入 SignalHandler 所需的最小依赖。"""
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

        def clear_queue(self):
            return None

    class _DummyProcessingStatus:
        PROCESSING = "processing"

    batch_module.BatchProcessorThread = _DummyBatchProcessorThread
    batch_module.FileQueueManager = _DummyFileQueueManager
    batch_module.ProcessingStatus = _DummyProcessingStatus
    monkeypatch.setitem(sys.modules, "app.ui.widgets.batch.batch_processor_thread", batch_module)


def _build_signal_handler_module(monkeypatch: pytest.MonkeyPatch):
    _install_signal_handler_stubs(monkeypatch)
    monkeypatch.delitem(sys.modules, "app.ui.signal_handler", raising=False)
    return importlib.import_module("app.ui.signal_handler")


def _build_batch_file_manager_module(monkeypatch: pytest.MonkeyPatch):
    batch_thread_module = types.ModuleType("app.ui.widgets.batch.batch_processor_thread")

    class _DummyFileQueueManager:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyProcessingStatus:
        PROCESSING = "processing"

    batch_thread_module.FileQueueManager = _DummyFileQueueManager
    batch_thread_module.ProcessingStatus = _DummyProcessingStatus
    monkeypatch.setitem(
        sys.modules,
        "app.ui.widgets.batch.batch_processor_thread",
        batch_thread_module,
    )
    module_name = "app.ui.widgets.batch.batch_file_manager"
    monkeypatch.delitem(sys.modules, module_name, raising=False)

    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "app"
        / "ui"
        / "widgets"
        / "batch"
        / "batch_file_manager.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _DummyPreferences:
    def get_preference(self, section, key, default=None):
        return default

    def set_preference(self, section, key, value):
        return None


class _DummyLogPanel:
    def add_error_message(self, message):
        return None


class _DummyStyleManager:
    pass


def test_signal_handler_import_dialog_uses_combined_media_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """主导入入口默认应先显示图片和视频联合过滤。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    captured = {}

    def _fake_get_open_file_names(parent, title, last_dir, filters):
        captured["filters"] = filters
        return [], ""

    from PyQt6.QtWidgets import QFileDialog

    monkeypatch.setattr(QFileDialog, "getOpenFileNames", staticmethod(_fake_get_open_file_names))

    handler = SignalHandler(
        file_panel=object(),
        preview_panel=object(),
        control_panel=object(),
        log_panel=_DummyLogPanel(),
        preferences=_DummyPreferences(),
        style_manager=_DummyStyleManager(),
        main_window=None,
    )

    handler.handle_import_file(parent_widget=None)

    assert captured["filters"] == EXPECTED_IMPORT_FILTER


def test_batch_file_manager_uses_same_combined_media_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """批量导入入口应与主导入入口使用相同的默认过滤器。"""
    batch_file_manager_module = _build_batch_file_manager_module(monkeypatch)
    BatchFileManager = batch_file_manager_module.BatchFileManager

    captured = {}

    class _FakeDialog:
        class FileMode:
            ExistingFiles = object()

        class DialogCode:
            Accepted = 1

        def __init__(self, parent):
            self.parent = parent

        def setFileMode(self, mode):
            captured["mode"] = mode

        def setNameFilter(self, filters):
            captured["filters"] = filters

        def exec(self):
            return 0

        def selectedFiles(self):
            return []

    monkeypatch.setattr(batch_file_manager_module, "QFileDialog", _FakeDialog)

    manager = BatchFileManager(parent_widget=None)
    selected_files = manager.show_add_files_dialog()

    assert selected_files == []
    assert captured["filters"] == EXPECTED_IMPORT_FILTER


def test_supported_media_extensions_match_real_processing_capabilities() -> None:
    """统一扩展名常量应只包含当前真正可处理的 4+4 格式。"""
    from app.utils.media_formats import IMAGE_FILE_EXTENSIONS, VIDEO_FILE_EXTENSIONS

    assert IMAGE_FILE_EXTENSIONS == (".jpg", ".jpeg", ".png", ".bmp")
    assert VIDEO_FILE_EXTENSIONS == (".mp4", ".avi", ".mkv", ".mov")


def test_signal_handler_rejects_gif_import_as_unsupported_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`.gif` 不应再被 UI 当作可导入处理格式。"""
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    SignalHandler = signal_handler_module.SignalHandler

    class _DummyFilePanel:
        def hide_queue(self):
            return None

        def set_export_enabled(self, enabled):
            return None

    class _DummyPreviewPanel:
        def set_image(self, path):
            raise AssertionError("不应把 GIF 当作支持图片直接加载")

        def set_manual_selection_image(self, path):
            raise AssertionError("不应把 GIF 当作支持图片进入手动框选")

        def set_image_from_array(self, image):
            raise AssertionError("不应把 GIF 当作视频帧加载")

        def set_manual_selection_image_from_array(self, image):
            raise AssertionError("不应把 GIF 当作视频首帧进入手动框选")

        def switch_to_manual_tab(self):
            return None

    class _DummyControlPanel:
        def __init__(self):
            self.enabled_values = []

        def set_start_button_enabled(self, enabled):
            self.enabled_values.append(enabled)

    class _DummyLogPanelWithWarning(_DummyLogPanel):
        def __init__(self):
            self.warning_messages = []

        def add_warning_log(self, message):
            self.warning_messages.append(message)

    log_panel = _DummyLogPanelWithWarning()
    control_panel = _DummyControlPanel()
    received_messages = []

    handler = SignalHandler(
        file_panel=_DummyFilePanel(),
        preview_panel=_DummyPreviewPanel(),
        control_panel=control_panel,
        log_panel=log_panel,
        preferences=_DummyPreferences(),
        style_manager=_DummyStyleManager(),
        main_window=None,
    )
    handler.status_updated.connect(received_messages.append)

    handler._handle_single_file("demo.gif")

    assert received_messages == []
    assert control_panel.enabled_values == []
    assert log_panel.warning_messages[-1] == "⚠️ 不支持的文件格式: .gif"
