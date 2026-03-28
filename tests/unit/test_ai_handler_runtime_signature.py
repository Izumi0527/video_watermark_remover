#!/usr/bin/env python3
"""
AIHandler 运行时签名刷新判定测试。
"""

from __future__ import annotations

import importlib
import sys
import types

import pytest


class _DummyAIHandler:
    def __init__(self, ai_params: dict):
        self.ai_params = dict(ai_params)


class _DummySignal:
    def connect(self, callback):
        return None


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


class _DummyTimer:
    def __init__(self, *args, **kwargs):
        self.timeout = _DummySignal()


def _install_qtcore_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")
    qtcore_module.QThread = _QObject
    qtcore_module.QTimer = _DummyTimer
    qtcore_module.pyqtSignal = lambda *args, **kwargs: _QtSignalDescriptor()
    monkeypatch.setitem(sys.modules, "PyQt6", pyqt6_module)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore_module)


def _build_base_ai_params() -> dict:
    return {
        "device": "auto",
        "use_gpu_inpainting": True,
        "conf_threshold": 0.5,
        "requested_inpainting_backend": "lama",
        "opencv_inpainting_method": "auto",
        "inpainting_algorithm": "gpu_dl",
        "inpaint_radius": 3,
        "quality_level": 3,
        "min_area_pixels": 100,
        "gpu_memory_mb": 2048,
        "inpainting_model_path": "models/stub-unet.pth",
        "lama_model_path": "models/big-lama.pt",
        "lama_model_dir": "models/lama",
    }


def test_ai_handler_refreshes_when_gpu_memory_budget_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_qtcore_stub(monkeypatch)
    monkeypatch.delitem(sys.modules, "app.core.video.thread", raising=False)
    thread_module = importlib.import_module("app.core.video.thread")

    existing = _DummyAIHandler(_build_base_ai_params())
    next_params = _build_base_ai_params()
    next_params["gpu_memory_mb"] = 1024

    assert thread_module._ai_handler_needs_refresh(existing, next_params) is True


def test_ai_handler_refreshes_when_conf_threshold_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_qtcore_stub(monkeypatch)
    monkeypatch.delitem(sys.modules, "app.core.video.thread", raising=False)
    thread_module = importlib.import_module("app.core.video.thread")

    existing = _DummyAIHandler(_build_base_ai_params())
    next_params = _build_base_ai_params()
    next_params["conf_threshold"] = 0.35

    assert thread_module._ai_handler_needs_refresh(existing, next_params) is True
