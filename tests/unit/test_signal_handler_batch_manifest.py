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
        file_ai_params_by_index=None,
        file_ai_params_by_file_id=None,
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files=4,
        auto_retry_failed=True,
        max_retry_count=3,
        parent=None,
    ):
        self.queue = queue or []
        self.ai_params = ai_params or {}
        self.file_ai_params_by_index = file_ai_params_by_index or {}
        self.file_ai_params_by_file_id = file_ai_params_by_file_id or {}
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


class _PlaceholderAIParamsBuilder:
    def build_from_ui(self, **kwargs):
        return {}

    def build_batch_config(self, _advanced_params, **_kwargs):
        return {}


class _ManifestStore:
    def __init__(self) -> None:
        self.contents: dict[str, str] = {}

    @staticmethod
    def normalize(path: str | Path) -> str:
        return str(Path(path)).replace("\\", "/")

    def write_text(self, path: str | Path, content: str) -> int:
        self.contents[self.normalize(path)] = content
        return len(content)

    def read_json(self, path: str | Path) -> dict:
        return json.loads(self.contents[self.normalize(path)])


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


def _install_pyqt_core_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")
    qtcore_module.QObject = _QObject
    qtcore_module.QThread = _QObject
    qtcore_module.pyqtSignal = lambda *args, **kwargs: _QtSignalDescriptor()
    monkeypatch.setitem(sys.modules, "PyQt6", pyqt6_module)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore_module)


def _install_import_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_pyqt_core_stub(monkeypatch)

    ui_utils_module = types.ModuleType("app.ui.utils")
    ui_utils_module.MEDIA_IMPORT_FILTER = "all files (*)"
    ui_utils_module.AIParamsBuilder = _PlaceholderAIParamsBuilder
    monkeypatch.setitem(sys.modules, "app.ui.utils", ui_utils_module)

    video_thread_module = types.ModuleType("app.core.video.thread")
    video_thread_module.VideoProcessorThread = _DummyVideoProcessorThread
    monkeypatch.setitem(sys.modules, "app.core.video.thread", video_thread_module)

    frame_reader_module = types.ModuleType("app.core.video.workers.frame_reader")
    frame_reader_module.extract_video_first_frame = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "app.core.video.workers.frame_reader", frame_reader_module)


def _build_signal_handler_module(monkeypatch: pytest.MonkeyPatch):
    _install_import_stubs(monkeypatch)
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


def _build_real_batch_processing_details(
    monkeypatch: pytest.MonkeyPatch,
    raw_quality_level: object,
    effective_quality_level: object | None = None,
) -> dict:
    """
    构造真实 BatchProcessorThread._build_processing_details() 的输出，
    用于验证批处理追溯字段在导出 manifest 时不会丢失。
    """
    _install_import_stubs(monkeypatch)
    monkeypatch.delitem(sys.modules, "app.ui.widgets.batch.batch_processor_thread", raising=False)
    batch_module = importlib.import_module("app.ui.widgets.batch.batch_processor_thread")

    batch_thread = batch_module.BatchProcessorThread(
        queue=[],
        ai_params={},
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files=1,
    )

    class _FakeProcessor:
        pass

    fake_processor = _FakeProcessor()
    fake_processor.last_effective_processing_info = None
    fake_processor.last_processing_info = {
        "quality_level": raw_quality_level,
        "requested_quality_level": raw_quality_level,
        "effective_quality_level": (
            raw_quality_level if effective_quality_level is None else effective_quality_level
        ),
    }
    fake_processor.last_processing_summary = None
    fake_processor.ai_handler = None

    return batch_thread._build_processing_details(fake_processor)


def _install_manifest_store(
    monkeypatch: pytest.MonkeyPatch, signal_handler_module, store: _ManifestStore
) -> None:
    monkeypatch.setattr(
        signal_handler_module.Path,
        "write_text",
        lambda self, text, encoding=None: store.write_text(self, text),
        raising=False,
    )


def test_batch_processing_details_includes_effective_quality_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    details = _build_real_batch_processing_details(
        monkeypatch, raw_quality_level=999, effective_quality_level=5
    )
    assert details["quality_level"] == 999
    assert details["requested_quality_level"] == 999
    assert details["effective_quality_level"] == 5


def test_batch_processing_details_keeps_backend_trace_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    details = _build_real_batch_processing_details(
        monkeypatch, raw_quality_level=3, effective_quality_level=3
    )
    details.update(
        {
            "requested_inpainting_backend": "lama",
            "actual_inpainting_backend": "opencv",
            "inpainting_fallback_reason": "lama_runtime_exception",
        }
    )

    assert details["requested_inpainting_backend"] == "lama"
    assert details["actual_inpainting_backend"] == "opencv"
    assert details["inpainting_fallback_reason"] == "lama_runtime_exception"


def test_export_manifest_keeps_last_batch_runtime_config_after_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)

    builder_result = {
        "auto_detect": True,
        "quality_level": 3,
        "requested_inpainting_backend": "lama",
        "processing_mode": "auto",
        "resolved_processing_mode": "pipeline",
        "enable_multiprocess": True,
        "use_pipeline": True,
        "num_processes": 3,
        "gpu_memory_mb": 1536,
        "enable_cache": True,
        "cache_size_mb": 256,
        "output_format": "keep",
        "compression_quality": 85,
        "add_suffix": True,
        "add_timestamp": False,
        "preserve_audio": True,
    }

    class _DummyAIParamsBuilder:
        def build_from_ui(self, **kwargs):
            return dict(builder_result)

        def build_batch_config(self, _advanced_params, **_kwargs):
            return {
                "max_concurrent_files": 1,
                "auto_retry_failed": True,
                "max_retry_count": 3,
            }

    monkeypatch.setattr(signal_handler_module, "AIParamsBuilder", _DummyAIParamsBuilder)

    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["first.jpg", "second.jpg"])
    handler._start_batch_processing()

    details = _build_real_batch_processing_details(monkeypatch, raw_quality_level=3)
    details.update(
        {
            "requested_inpainting_backend": "lama",
            "actual_inpainting_backend": "opencv",
            "inpainting_fallback_reason": "lama_runtime_exception",
        }
    )
    handler._on_batch_file_completed(
        0, "first_out.jpg", signal_handler_module.ProcessingStatus.COMPLETED, "", details
    )
    handler._on_batch_completed()

    manifest_store = _ManifestStore()
    _install_manifest_store(monkeypatch, signal_handler_module, manifest_store)
    manifest_path = Path("virtual_manifest") / "manifest.json"
    monkeypatch.setattr(
        handler,
        "_show_save_dialog",
        lambda *args, **kwargs: (str(manifest_path), "JSON文件 (*.json)"),
    )

    handler.handle_export_batch_manifest(parent_widget=None)
    manifest = manifest_store.read_json(manifest_path)
    run_manifest = manifest["run"]

    assert manifest["run"]["ai_params_source"] == "last_batch"
    expected_ai_params = dict(builder_result)
    assert run_manifest["ai_params"] == expected_ai_params
    assert run_manifest["runtime_performance"]["requested_processing_mode"] == "auto"
    assert run_manifest["runtime_performance"]["resolved_processing_mode"] == "pipeline"
    assert run_manifest["runtime_performance"]["worker_count"] == 3
    assert run_manifest["runtime_performance"]["enable_multiprocess"] is True
    assert run_manifest["runtime_performance"]["use_pipeline"] is True
    assert run_manifest["runtime_performance"]["gpu_memory_budget_mb"] == 1536
    assert run_manifest["runtime_performance"]["enable_cache"] is True
    assert run_manifest["runtime_performance"]["cache_size_mb"] == 256
    assert manifest["batch"]["max_concurrent_files"] == 1
    assert manifest["batch"]["auto_retry_failed"] is True
    assert manifest["batch"]["max_retry_count"] == 3
    assert run_manifest["runtime_performance"]["batch_max_concurrent_files"] == 1
    assert run_manifest["runtime_performance"]["batch_auto_retry_failed"] is True
    assert run_manifest["runtime_performance"]["batch_max_retry_count"] == 3

    first_item = manifest["items"][0]
    assert first_item["output_config"] == {
        "output_format": "keep",
        "compression_quality": 85,
        "add_suffix": True,
        "add_timestamp": False,
        "preserve_audio": True,
    }
    assert isinstance(first_item.get("processing_details"), dict)
    assert first_item["processing_details"]["quality_level"] == 3
    assert first_item["processing_details"]["requested_quality_level"] == 3
    assert first_item["processing_details"]["effective_quality_level"] == 3
    assert first_item["processing_details"]["requested_inpainting_backend"] == "lama"
    assert first_item["processing_details"]["actual_inpainting_backend"] == "opencv"
    assert (
        first_item["processing_details"]["inpainting_fallback_reason"] == "lama_runtime_exception"
    )


def test_handle_queue_clear_clears_last_batch_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, *_ = _build_handler(signal_handler_module)

    handler._last_batch_ai_params = {"stale": True}
    handler._last_batch_ai_params_generated_at = "2026-03-24 10:00:00"
    handler._last_batch_config = {"max_concurrent_files": 4}
    handler._last_batch_runtime_config = {"resolved_processing_mode": "pipeline"}

    handler.handle_queue_clear()

    assert handler._last_batch_ai_params is None
    assert handler._last_batch_ai_params_generated_at is None
    assert handler._last_batch_config is None
    assert handler._last_batch_runtime_config is None


def test_handle_file_remove_clears_last_batch_snapshot_when_queue_not_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["keep.jpg", "remove.jpg"])

    handler._last_batch_ai_params = {"stale": True}
    handler._last_batch_ai_params_generated_at = "2026-03-24 10:00:00"
    handler._last_batch_config = {"max_concurrent_files": 4}
    handler._last_batch_runtime_config = {"resolved_processing_mode": "pipeline"}

    handler.handle_file_remove(1)

    assert handler.file_queue_manager.get_queue_size() == 1
    assert handler._last_batch_ai_params is None
    assert handler._last_batch_ai_params_generated_at is None
    assert handler._last_batch_config is None
    assert handler._last_batch_runtime_config is None


def test_handle_file_remove_allows_waiting_item_while_batch_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["first.jpg", "second.jpg"])

    original_queue = handler.file_queue_manager.get_queue()
    removed_file_id = original_queue[1]["file_id"]
    handler.file_queue_manager.update_file_status(
        0, signal_handler_module.ProcessingStatus.PROCESSING
    )

    class _RunningBatchProcessor:
        should_stop = False

        def __init__(self, file_queue):
            self.file_queue = file_queue
            self.removed = []

        @staticmethod
        def isRunning() -> bool:
            return True

        def remove_pending_file(self, file_id: str) -> bool:
            self.removed.append(file_id)
            return True

    handler.batch_processor = _RunningBatchProcessor(original_queue)
    handler._last_batch_ai_params = {"stale": True}
    handler._last_batch_ai_params_generated_at = "2026-03-24 10:00:00"
    handler._last_batch_config = {"max_concurrent_files": 4}
    handler._last_batch_runtime_config = {"resolved_processing_mode": "pipeline"}

    handler.handle_file_remove(1)

    after_queue = handler.file_queue_manager.get_queue()
    assert len(after_queue) == 1
    assert after_queue[0]["input_path"] == "first.jpg"
    assert handler.batch_processor.removed == [removed_file_id]
    assert handler._last_batch_ai_params is None
    assert handler._last_batch_config is None

    handler._on_batch_file_progress(50, 1)
    remaining_item = handler.file_queue_manager.get_file_info(0)
    assert remaining_item["progress"] == 0

    before_status = remaining_item["status"]
    before_error = remaining_item["error_message"]
    before_details = remaining_item.get("processing_details")
    handler._on_batch_file_completed(
        1,
        "removed_out.jpg",
        signal_handler_module.ProcessingStatus.COMPLETED,
        "",
        {"trace_id": "removed-item"},
    )
    after_remaining_item = handler.file_queue_manager.get_file_info(0)
    assert after_remaining_item["status"] == before_status
    assert after_remaining_item["progress"] == 0
    assert after_remaining_item["error_message"] == before_error
    assert after_remaining_item.get("processing_details") == before_details


def test_handle_file_remove_still_blocks_processing_item_while_batch_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["first.jpg", "second.jpg"])

    original_queue = handler.file_queue_manager.get_queue()

    class _RunningBatchProcessor:
        should_stop = False

        def __init__(self, file_queue):
            self.file_queue = file_queue
            self.removed = []

        @staticmethod
        def isRunning() -> bool:
            return True

        def remove_pending_file(self, file_id: str) -> bool:
            self.removed.append(file_id)
            return True

    handler.batch_processor = _RunningBatchProcessor(original_queue)
    handler.file_queue_manager.update_file_status(
        0, signal_handler_module.ProcessingStatus.PROCESSING
    )

    before_queue = handler.file_queue_manager.get_queue()
    handler.handle_file_remove(0)
    after_queue = handler.file_queue_manager.get_queue()

    assert len(after_queue) == len(before_queue)
    assert [item["input_path"] for item in after_queue] == [
        item["input_path"] for item in before_queue
    ]
    assert handler.batch_processor.removed == []


@pytest.mark.parametrize(
    ("stale_status_name", "stale_error"),
    [
        ("FAILED", "处理失败"),
        ("CANCELLED", "用户取消"),
    ],
)
def test_handle_file_remove_ignores_stale_failed_or_cancelled_completion_callback(
    monkeypatch: pytest.MonkeyPatch,
    stale_status_name: str,
    stale_error: str,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["first.jpg", "second.jpg"])

    original_queue = handler.file_queue_manager.get_queue()
    removed_file_id = original_queue[1]["file_id"]
    handler.file_queue_manager.update_file_status(
        0, signal_handler_module.ProcessingStatus.PROCESSING
    )

    class _RunningBatchProcessor:
        should_stop = False

        def __init__(self, file_queue):
            self.file_queue = file_queue
            self.removed = []

        @staticmethod
        def isRunning() -> bool:
            return True

        def remove_pending_file(self, file_id: str) -> bool:
            self.removed.append(file_id)
            return True

    handler.batch_processor = _RunningBatchProcessor(original_queue)
    handler.handle_file_remove(1)

    after_queue = handler.file_queue_manager.get_queue()
    assert len(after_queue) == 1
    assert handler.batch_processor.removed == [removed_file_id]

    remaining_item = handler.file_queue_manager.get_file_info(0)
    before_status = remaining_item["status"]
    before_progress = remaining_item["progress"]
    before_error = remaining_item["error_message"]
    before_details = remaining_item.get("processing_details")

    stale_status = getattr(signal_handler_module.ProcessingStatus, stale_status_name)
    handler._on_batch_file_completed(
        1,
        "removed_out.jpg",
        stale_status,
        stale_error,
        {"trace_id": f"removed-{stale_status_name.lower()}"},
    )

    after_remaining_item = handler.file_queue_manager.get_file_info(0)
    assert after_remaining_item["status"] == before_status
    assert after_remaining_item["progress"] == before_progress
    assert after_remaining_item["error_message"] == before_error
    assert after_remaining_item.get("processing_details") == before_details


def test_switching_to_single_file_clears_last_batch_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)
    handler, *_ = _build_handler(signal_handler_module)

    handler._last_batch_ai_params = {"stale": True}
    handler._last_batch_ai_params_generated_at = "2026-03-24 10:00:00"
    handler._last_batch_config = {"max_concurrent_files": 4}
    handler._last_batch_runtime_config = {"resolved_processing_mode": "pipeline"}

    handler._handle_single_file("demo.jpg")

    assert handler._last_batch_ai_params is None
    assert handler._last_batch_ai_params_generated_at is None
    assert handler._last_batch_config is None
    assert handler._last_batch_runtime_config is None


def test_replacing_queue_invalidates_stale_batch_snapshot_before_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)

    builder_result = {"stale": True}

    class _DummyAIParamsBuilder:
        def build_from_ui(self, **kwargs):
            return dict(builder_result)

        def build_batch_config(self, _advanced_params, **_kwargs):
            return {
                "max_concurrent_files": 1,
                "auto_retry_failed": True,
                "max_retry_count": 3,
            }

    monkeypatch.setattr(signal_handler_module, "AIParamsBuilder", _DummyAIParamsBuilder)

    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["old.jpg", "old2.jpg"])
    handler._start_batch_processing()
    handler._on_batch_completed()

    builder_result = {
        "fresh": True,
        "auto_detect": True,
        "processing_mode": "auto",
        "resolved_processing_mode": "single_process",
        "enable_multiprocess": False,
        "use_pipeline": False,
        "num_processes": 1,
        "gpu_memory_mb": 2048,
        "enable_cache": True,
        "cache_size_mb": 512,
        "output_format": "keep",
        "compression_quality": 85,
        "add_suffix": True,
        "add_timestamp": False,
        "preserve_audio": True,
    }
    handler._handle_multiple_files(["new.jpg", "new2.jpg"])

    manifest_store = _ManifestStore()
    _install_manifest_store(monkeypatch, signal_handler_module, manifest_store)
    manifest_path = Path("virtual_manifest") / "manifest.json"
    monkeypatch.setattr(
        handler,
        "_show_save_dialog",
        lambda *args, **kwargs: (str(manifest_path), "JSON文件 (*.json)"),
    )

    handler.handle_export_batch_manifest(parent_widget=None)
    manifest = manifest_store.read_json(manifest_path)
    run_manifest = manifest["run"]

    assert manifest["run"]["ai_params_source"] == "computed_at_export"
    expected_ai_params = dict(builder_result)
    assert run_manifest["ai_params"] == expected_ai_params
    assert run_manifest["runtime_performance"]["requested_processing_mode"] == "auto"
    assert run_manifest["runtime_performance"]["resolved_processing_mode"] == "single_process"


def test_export_manifest_records_file_level_runtime_performance_for_mixed_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signal_handler_module = _build_signal_handler_module(monkeypatch)

    class _DummyAIParamsBuilder:
        def build_from_ui(self, **kwargs):
            input_file_path = str(kwargs.get("input_file_path") or "")
            if input_file_path.endswith(".mp4"):
                return {
                    "auto_detect": True,
                    "processing_mode": "auto",
                    "resolved_processing_mode": "pipeline",
                    "enable_multiprocess": True,
                    "use_pipeline": True,
                    "num_processes": 4,
                    "gpu_memory_mb": 2048,
                    "enable_cache": True,
                    "cache_size_mb": 512,
                }
            return {
                "auto_detect": True,
                "processing_mode": "auto",
                "resolved_processing_mode": "single_process",
                "enable_multiprocess": False,
                "use_pipeline": False,
                "num_processes": 1,
                "gpu_memory_mb": 2048,
                "enable_cache": True,
                "cache_size_mb": 512,
            }

        def build_batch_config(self, _advanced_params, **_kwargs):
            return {
                "max_concurrent_files": 1,
                "auto_retry_failed": True,
                "max_retry_count": 3,
            }

    monkeypatch.setattr(signal_handler_module, "AIParamsBuilder", _DummyAIParamsBuilder)

    handler, *_ = _build_handler(signal_handler_module)
    handler._handle_multiple_files(["first.jpg", "second.mp4"])
    handler._start_batch_processing()

    manifest_store = _ManifestStore()
    _install_manifest_store(monkeypatch, signal_handler_module, manifest_store)
    manifest_path = Path("virtual_manifest") / "manifest.json"
    monkeypatch.setattr(
        handler,
        "_show_save_dialog",
        lambda *args, **kwargs: (str(manifest_path), "JSON文件 (*.json)"),
    )

    handler.handle_export_batch_manifest(parent_widget=None)
    manifest = manifest_store.read_json(manifest_path)

    assert (
        manifest["items"][0]["runtime_performance"]["resolved_processing_mode"] == "single_process"
    )
    assert manifest["items"][1]["runtime_performance"]["resolved_processing_mode"] == "pipeline"
