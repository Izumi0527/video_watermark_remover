#!/usr/bin/env python3
"""
LaMa TorchScript 运行时回归测试。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
import subprocess
import sys
import uuid

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def tmp_path() -> Path:
    """使用仓库内临时目录，避免系统 Temp 的 .lock 权限噪音。"""
    base_dir = PROJECT_ROOT / ".tmp_pytest_lama_runtime_cases"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = base_dir / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _run_python(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(PROJECT_ROOT),
    )


def _torchscript_stub_code(model_path: Path, *, asset_ref: Path) -> str:
    model_path_str = str(model_path).replace("\\", "/")
    asset_ref_str = str(asset_ref).replace("\\", "/")
    return f"""
from pathlib import Path
import json
import numpy as np
import torch

class StubLaMa(torch.nn.Module):
    def forward(self, image: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        expanded_mask = mask.to(dtype=image.dtype).repeat(1, image.shape[1], 1, 1)
        return image * (1 - expanded_mask) + torch.ones_like(image) * expanded_mask

model_path = Path(r\"{model_path_str}\")
model_path.parent.mkdir(parents=True, exist_ok=True)
model = StubLaMa().eval()
example_image = torch.zeros((1, 3, 16, 16), dtype=torch.float32)
example_mask = torch.zeros((1, 1, 16, 16), dtype=torch.float32)
scripted = torch.jit.trace(model, (example_image, example_mask))
scripted.save(str(model_path))

from app.core.ai.lama_runtime import build_lama_runner

runner = build_lama_runner(
    config=None,
    torch_device=torch.device(\"cpu\"),
    asset_ref=r\"{asset_ref_str}\",
)

frame = np.zeros((13, 19, 3), dtype=np.uint8)
frame[1:3, 1:3] = (0, 0, 255)
mask = np.zeros((13, 19), dtype=np.uint8)
mask[4:9, 7:12] = 255

result = runner(
    frame,
    mask,
    inpaint_radius=3,
    quality_level=3,
    device=torch.device(\"cpu\"),
    asset_ref=r\"{asset_ref_str}\",
)

payload = {{
    \"shape\": list(result.shape),
    \"dtype\": str(result.dtype),
    \"masked_all_white\": bool(np.all(result[mask > 0] == 255)),
    \"preserved_corner\": bool(np.array_equal(result[0, 0], frame[0, 0])),
    \"model_path\": getattr(runner, \"model_path\", None),
}}
print(json.dumps(payload))
"""


def test_build_lama_runner_executes_torchscript_model_from_file(tmp_path: pytest.TempPathFactory) -> None:
    model_path = tmp_path / "big-lama.pt"
    result = _run_python(_torchscript_stub_code(model_path, asset_ref=model_path))

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["shape"] == [13, 19, 3]
    assert payload["dtype"] == "uint8"
    assert payload["masked_all_white"] is True
    assert payload["preserved_corner"] is True


def test_build_lama_runner_supports_directory_asset_ref(tmp_path: pytest.TempPathFactory) -> None:
    asset_dir = tmp_path / "lama-assets"
    model_path = asset_dir / "big-lama.pt"
    result = _run_python(_torchscript_stub_code(model_path, asset_ref=asset_dir))

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["model_path"] == str(model_path)


def test_lama_backend_rejects_official_checkpoint_assets_without_runtime_support(
    tmp_path: pytest.TempPathFactory,
) -> None:
    asset_dir = tmp_path / "big-lama"
    models_dir = asset_dir / "models"
    models_dir.mkdir(parents=True)
    (asset_dir / "config.yaml").write_text("model:\n  path: ./models\n", encoding="utf-8")
    (models_dir / "best.ckpt").write_bytes(b"stub")

    code = f"""
import json
from app.core.ai.inpainting_backends.lama_backend import LaMaInpaintingBackend

backend = LaMaInpaintingBackend(
    config=None,
    torch_device=\"cpu\",
    asset_ref=r\"{str(asset_dir).replace('\\', '/')}\",
)

loaded = backend.load()
trace = backend.get_last_trace()
print(json.dumps({{
    \"loaded\": loaded,
    \"reason\": trace.get(\"load_failure_reason\"),
    \"detail\": trace.get(\"load_failure_detail\"),
}}))
"""
    result = _run_python(code)

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["loaded"] is False
    assert payload["reason"] == "lama_checkpoint_assets_unsupported"
    assert "TorchScript" in payload["detail"]
