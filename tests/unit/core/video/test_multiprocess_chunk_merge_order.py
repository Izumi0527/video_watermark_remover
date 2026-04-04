#!/usr/bin/env python3
"""
多进程分块合并顺序回归测试。
"""

from __future__ import annotations

import importlib
import os
import sys
import types

import pytest


def _import_multiprocess_module(monkeypatch: pytest.MonkeyPatch):
    """通过最小桩隔离 GUI/图像依赖，专注验证排序逻辑。"""
    monkeypatch.delitem(sys.modules, "app.core.video.modes.multiprocess", raising=False)

    cv2_module = types.ModuleType("cv2")
    monkeypatch.setitem(sys.modules, "cv2", cv2_module)

    pyqt_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")

    class _DummyQTimer:
        pass

    qtcore_module.QTimer = _DummyQTimer
    monkeypatch.setitem(sys.modules, "PyQt6", pyqt_module)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore_module)

    return importlib.import_module("app.core.video.modes.multiprocess")


def test_merge_chunk_paths_uses_numeric_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """块编号超过 9 时，必须按数值顺序而不是字符串顺序合并。"""
    module = _import_multiprocess_module(monkeypatch)

    chunk_paths = [
        "C:/tmp/video_chunk_0_100.mp4",
        "C:/tmp/video_chunk_1_100.mp4",
        "C:/tmp/video_chunk_10_100.mp4",
        "C:/tmp/video_chunk_2_100.mp4",
    ]

    ordered = module._sort_chunk_paths(chunk_paths)

    assert ordered == [
        "C:/tmp/video_chunk_0_100.mp4",
        "C:/tmp/video_chunk_1_100.mp4",
        "C:/tmp/video_chunk_2_100.mp4",
        "C:/tmp/video_chunk_10_100.mp4",
    ]


def test_process_video_multiprocess_sorts_chunk_paths_before_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真实合并链路在传给 FFmpeg 前必须先按分块编号数值排序。"""
    module = _import_multiprocess_module(monkeypatch)

    class _DummySignal:
        def connect(self, callback) -> None:
            self.callback = callback

    class _DummyTimer:
        def __init__(self) -> None:
            self.timeout = _DummySignal()

        def start(self, _interval: int) -> None:
            return None

        def stop(self) -> None:
            return None

    class _DummyVideoCapture:
        def __init__(self, _path: str) -> None:
            self._properties = {
                1: 120,
                2: 24.0,
                3: 1920,
                4: 1080,
            }

        def isOpened(self) -> bool:
            return True

        def get(self, prop: int):
            return self._properties[prop]

        def release(self) -> None:
            return None

    class _DummyQueue:
        def empty(self) -> bool:
            return True

        def get_nowait(self):
            raise AssertionError("空队列不应被读取")

    class _DummyEvent:
        def __init__(self) -> None:
            self._is_set = False

        def is_set(self) -> bool:
            return self._is_set

        def set(self) -> None:
            self._is_set = True

    class _DummyManager:
        def Queue(self) -> _DummyQueue:
            return _DummyQueue()

        def Event(self) -> _DummyEvent:
            return _DummyEvent()

    class _FakeFuture:
        def __init__(self, result_tuple) -> None:
            self._result = result_tuple

        def result(self):
            return self._result

    class _FakeExecutor:
        def __init__(self, *args, **kwargs) -> None:
            self._futures = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def submit(self, _fn, _input_path, _start, _end, temp_path, *_args):
            future = _FakeFuture((temp_path, True, None))
            self._futures.append(future)
            return future

    merge_inputs: list[str] = []

    monkeypatch.setattr(module, "QTimer", _DummyTimer)
    monkeypatch.setattr(
        module,
        "cv2",
        types.SimpleNamespace(
            VideoCapture=_DummyVideoCapture,
            CAP_PROP_FRAME_COUNT=1,
            CAP_PROP_FPS=2,
            CAP_PROP_FRAME_WIDTH=3,
            CAP_PROP_FRAME_HEIGHT=4,
        ),
    )
    monkeypatch.setattr(module.os, "getpid", lambda: 100)
    monkeypatch.setattr(module.tempfile, "gettempdir", lambda: "C:/tmp")
    monkeypatch.setattr(module.multiprocessing, "Manager", lambda: _DummyManager())
    monkeypatch.setattr(module, "ProcessPoolExecutor", _FakeExecutor)
    monkeypatch.setattr(module, "as_completed", lambda futures: list(reversed(futures)))
    monkeypatch.setattr(module, "build_temp_path", lambda _output, _suffix: "C:/tmp/merged.mp4")
    monkeypatch.setattr(module, "should_preserve_audio", lambda _ai_params: False)
    monkeypatch.setattr(module.os.path, "exists", lambda _path: False)
    monkeypatch.setattr(module.os, "replace", lambda _src, _dst: None)
    monkeypatch.setattr(
        module,
        "_merge_video_chunks",
        lambda _processor, chunk_paths, _output: merge_inputs.extend(chunk_paths),
    )

    processor = types.SimpleNamespace(
        input_path="C:/tmp/input.mp4",
        output_path="C:/tmp/output.mp4",
        num_processes=12,
        ai_params={},
        config=None,
        ffmpeg_processor=None,
        _is_running=True,
        _progress_timer=None,
        _stop_event=None,
        logger=types.SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            debug=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
        ),
        status=types.SimpleNamespace(emit=lambda *args, **kwargs: None),
        progress=types.SimpleNamespace(emit=lambda *args, **kwargs: None),
        finished=types.SimpleNamespace(emit=lambda *args, **kwargs: None),
        _emit_detailed_progress=lambda *args, **kwargs: None,
        _process_video_singleprocess=lambda: None,
    )

    module.process_video_multiprocess(processor)

    assert [os.path.basename(path) for path in merge_inputs] == [
        f"video_chunk_{index}_100.mp4" for index in range(12)
    ]
