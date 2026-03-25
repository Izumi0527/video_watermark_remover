import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import uuid

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"


@pytest.fixture
def temp_dir() -> Path:
    """使用仓库内临时目录，避免系统 Temp 写入失败。"""
    base_dir = PROJECT_ROOT / ".tmp_pytest_weight_inspector"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = base_dir / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    src_pythonpath = str(SRC_DIR)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_pythonpath}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else src_pythonpath
    )
    return env


def _run_python_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=_subprocess_env(),
    )


def _write_checkpoint(path: Path, mode: str, container_key: str = "") -> None:
    script = """
import sys
import torch
from app.core.ai.dl_inpainter import UNetInpaintingModel

output_path = sys.argv[1]
mode = sys.argv[2]
container_key = sys.argv[3]

model = UNetInpaintingModel(in_channels=4, out_channels=3, base_channels=32)
state_dict = model.state_dict()

if mode == "compatible":
    payload = state_dict
elif mode == "wrapped":
    payload = {container_key: state_dict, "epoch": 3}
elif mode == "prefixed":
    payload = {f"module.{key}": value for key, value in state_dict.items()}
elif mode == "shape_mismatch":
    payload = dict(state_dict)
    payload["enc1.0.weight"] = state_dict["enc1.0.weight"][0:16]
else:
    raise RuntimeError(f"unknown mode: {mode}")

torch.save(payload, output_path)
"""
    result = _run_python_script(script, str(path), mode, container_key)
    assert result.returncode == 0, result.stderr or result.stdout


def _inspect_file(path: Path) -> dict:
    script = """
import json
import sys
from dataclasses import asdict
from app.utils.inpainting_weight_inspector import InpaintingWeightInspector

result = InpaintingWeightInspector().inspect_file(sys.argv[1])
print(json.dumps(asdict(result), default=str))
"""
    result = _run_python_script(script, str(path))
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout.strip())


def _scan_directory(path: Path) -> list[dict]:
    script = """
import json
import sys
from dataclasses import asdict
from app.utils.inpainting_weight_inspector import InpaintingWeightInspector

results = InpaintingWeightInspector().scan_directory(sys.argv[1])
print(json.dumps([asdict(item) for item in results], default=str))
"""
    result = _run_python_script(script, str(path))
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout.strip())


def _run_cli(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.utils.inpainting_weight_inspector", str(path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=_subprocess_env(),
    )


class TestInpaintingWeightInspector:
    def test_inspect_file_returns_missing_for_nonexistent_path(self, temp_dir):
        result = _inspect_file(temp_dir / "missing-unet.pth")

        assert result["status"] == "missing"
        assert result["reason_code"] == "file_not_found"
        assert result["is_directly_loadable"] is False

    def test_inspect_file_detects_compatible_raw_state_dict(self, temp_dir):
        weight_path = temp_dir / "compatible-unet.pth"
        _write_checkpoint(weight_path, "compatible")

        result = _inspect_file(weight_path)

        assert result["status"] == "compatible"
        assert result["reason_code"] == "direct_state_dict"
        assert result["is_directly_loadable"] is True
        assert result["container_key"] is None

    def test_inspect_file_detects_wrapped_checkpoint(self, temp_dir):
        weight_path = temp_dir / "wrapped-state-dict.pth"
        _write_checkpoint(weight_path, "wrapped", "state_dict")

        result = _inspect_file(weight_path)

        assert result["status"] == "needs_unpacking"
        assert result["reason_code"] == "wrapped_state_dict"
        assert result["is_directly_loadable"] is False
        assert result["container_key"] == "state_dict"

    def test_inspect_file_detects_module_prefix_rewrite(self, temp_dir):
        weight_path = temp_dir / "module-prefixed-unet.pth"
        _write_checkpoint(weight_path, "prefixed")

        result = _inspect_file(weight_path)

        assert result["status"] == "needs_key_rewrite"
        assert result["reason_code"] == "prefixed_state_dict"
        assert result["is_directly_loadable"] is False
        assert result["prefix_to_strip"] == "module."

    def test_inspect_file_detects_shape_mismatch(self, temp_dir):
        weight_path = temp_dir / "shape-mismatch-unet.pth"
        _write_checkpoint(weight_path, "shape_mismatch")

        result = _inspect_file(weight_path)

        assert result["status"] == "incompatible"
        assert result["reason_code"] == "shape_mismatch"
        assert "enc1.0.weight" in result["shape_mismatches"]

    def test_inspect_file_marks_unsupported_format(self, temp_dir):
        weight_path = temp_dir / "candidate-unet.safetensors"
        weight_path.write_text("placeholder", encoding="utf-8")

        result = _inspect_file(weight_path)

        assert result["status"] == "incompatible"
        assert result["reason_code"] == "unsupported_format"
        assert result["is_directly_loadable"] is False

    def test_scan_directory_returns_candidate_results(self, temp_dir):
        _write_checkpoint(temp_dir / "compatible-unet.pth", "compatible")
        _write_checkpoint(temp_dir / "wrapped-unet.ckpt", "wrapped", "model")
        (temp_dir / "notes.txt").write_text("ignore me", encoding="utf-8")

        results = _scan_directory(temp_dir)

        assert [Path(result["path"]).name for result in results] == [
            "compatible-unet.pth",
            "wrapped-unet.ckpt",
        ]
        assert [result["status"] for result in results] == ["compatible", "needs_unpacking"]


class TestInpaintingWeightInspectorCli:
    @pytest.mark.cli
    def test_cli_returns_zero_for_compatible_file(self, temp_dir):
        weight_path = temp_dir / "compatible-unet.pth"
        _write_checkpoint(weight_path, "compatible")

        result = _run_cli(weight_path)

        assert result.returncode == 0
        assert "compatible" in result.stdout
        assert str(weight_path) in result.stdout

    @pytest.mark.cli
    def test_cli_returns_non_zero_when_manual_action_needed(self, temp_dir):
        weight_path = temp_dir / "wrapped-state-dict.pth"
        _write_checkpoint(weight_path, "wrapped", "model_state_dict")

        result = _run_cli(weight_path)

        assert result.returncode == 1
        assert "needs_unpacking" in result.stdout
        assert "model_state_dict" in result.stdout
