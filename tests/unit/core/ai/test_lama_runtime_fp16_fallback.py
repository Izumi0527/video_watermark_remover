#!/usr/bin/env python3
"""
LaMa FP16 回退逻辑回归测试

说明：
- 真实 torch 在 pytest + PyQt6 环境下可能触发 WinError 1114（DLL 初始化失败）。
- 为了保证单元测试稳定且 <60s，这里使用轻量 torch 桩模块，仅验证回退控制逻辑本身。
"""

import importlib
import sys
import types

import pytest


def _install_torch_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """注入最小 torch 桩模块，避免 pytest 环境加载真实 torch DLL。"""
    torch_module = types.ModuleType("torch")

    class _DummyDevice:
        def __init__(self, device_type: str):
            self.type = str(device_type)

    torch_module.device = _DummyDevice
    # 供模块 import 阶段默认参数使用（dtype 默认值会在函数定义时求值）。
    torch_module.float32 = object()
    torch_module.float16 = object()

    monkeypatch.setitem(sys.modules, "torch", torch_module)


def test_lama_fp16_failure_fallbacks_and_locks(monkeypatch: pytest.MonkeyPatch) -> None:
    """当 FP16 分支抛出 cuFFT half precision 错误时，应回退到 FP32 并锁定 use_fp16=False。"""
    _install_torch_stub(monkeypatch)
    monkeypatch.delitem(sys.modules, "app.core.ai.lama_runtime", raising=False)

    lama_runtime = importlib.import_module("app.core.ai.lama_runtime")
    runner_cls = lama_runtime.LaMaTorchScriptRunner

    runner = runner_cls(
        model=object(),
        device=types.SimpleNamespace(type="cuda"),
        asset_ref="tests://dummy",
        model_path="dummy.pt",
        use_fp16=True,
    )

    calls = {"fp16": 0, "fp32": 0}

    def run_fp16():
        calls["fp16"] += 1
        raise RuntimeError(
            "cuFFT only supports dimensions whose sizes are powers of two when computing in half precision"
        )

    def run_fp32():
        calls["fp32"] += 1
        return "ok"

    result = runner._run_with_fp16_fallback(
        use_fp16=True,
        run_fp16=run_fp16,
        run_fp32=run_fp32,
        context="单元测试",
    )

    assert result == "ok"
    assert runner.use_fp16 is False
    assert calls["fp16"] == 1
    assert calls["fp32"] == 1

    # 第二次执行：即使调用方仍传入 use_fp16=True，runner.use_fp16 已锁定为 False（上层应据此计算 use_fp16）
    # 这里验证“锁定”的副作用存在。
    result2 = runner._run_with_fp16_fallback(
        use_fp16=runner.use_fp16,
        run_fp16=run_fp16,
        run_fp32=run_fp32,
        context="单元测试二次",
    )
    assert result2 == "ok"
    assert runner.use_fp16 is False
    assert calls["fp16"] == 1
    assert calls["fp32"] == 2
