#!/usr/bin/env python3
"""
LaMa backend GPU subprocess smoke 包装测试。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _save_stub_lama_torchscript_model(path: Path) -> None:
    script = f"""
from pathlib import Path
import torch

class StubLaMa(torch.nn.Module):
    def forward(self, image: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        expanded_mask = mask.to(dtype=image.dtype).repeat(1, image.shape[1], 1, 1)
        return image * (1 - expanded_mask) + torch.ones_like(image) * expanded_mask

path = Path(r\"{str(path).replace('\\', '/')}\")
path.parent.mkdir(parents=True, exist_ok=True)
model = StubLaMa().eval()
example_image = torch.zeros((1, 3, 16, 16), dtype=torch.float32)
example_mask = torch.zeros((1, 1, 16, 16), dtype=torch.float32)
scripted = torch.jit.trace(model, (example_image, example_mask))
scripted.save(str(path))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def _probe_torch_import() -> tuple[bool, str]:
    """在子进程中探测 torch 是否可导入，避免当前 pytest 进程被 DLL 错误拖崩。"""
    command = [sys.executable, "-c", "import torch"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return True, ""
    return False, (result.stderr or result.stdout or "torch import failed").strip()


def test_torch_runtime_probe() -> None:
    """探测当前环境是否具备运行 GPU smoke 所需的 torch 运行时。"""
    torch_available, torch_probe_error = _probe_torch_import()
    if not torch_available:
        pytest.skip(f"torch 不可用，跳过 GPU 集成测试：{torch_probe_error}")
    assert torch_available


def test_lama_smoke_runs_in_subprocess_or_skips() -> None:
    """LaMa smoke 必须在 subprocess 中运行，避免 Qt 与 torch GPU 运行时互相影响。"""
    torch_available, torch_probe_error = _probe_torch_import()
    if not torch_available:
        pytest.skip(f"torch 不可用，跳过 GPU 集成测试：{torch_probe_error}")

    script_path = Path(__file__).resolve().parent / "runtime" / "lama_smoke.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    output = (result.stdout or result.stderr or "").strip()
    if result.returncode == 2:
        pytest.skip(output or "LaMa smoke 前置条件不满足")

    assert result.returncode == 0, output or "LaMa smoke 失败"


def test_lama_smoke_runs_with_temp_torchscript_asset(tmp_path: Path) -> None:
    """给定临时 TorchScript 资产时，LaMa smoke 应真实执行而不是跳过。"""
    torch_available, torch_probe_error = _probe_torch_import()
    if not torch_available:
        pytest.skip(f"torch 不可用，跳过 GPU 集成测试：{torch_probe_error}")

    model_path = tmp_path / "big-lama.pt"
    _save_stub_lama_torchscript_model(model_path)

    script_path = Path(__file__).resolve().parent / "runtime" / "lama_smoke.py"
    env = os.environ.copy()
    env["VWR_LAMA_MODEL_PATH"] = str(model_path)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    output = (result.stdout or result.stderr or "").strip()
    if result.returncode == 2 and "CUDA 不可用" in output:
        pytest.skip(output)

    assert result.returncode == 0, output or "临时 TorchScript 资产 smoke 失败"
