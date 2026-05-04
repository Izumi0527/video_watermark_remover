from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _find_bash() -> str:
    candidates: list[str] = []
    if os.name == "nt":
        candidates.extend(
            [
                "C:/Program Files/Git/bin/bash.exe",
                "C:/Program Files/Git/usr/bin/bash.exe",
            ]
        )
    detected = shutil.which("bash")
    if detected:
        candidates.append(detected)

    for candidate in candidates:
        if not Path(candidate).exists():
            continue
        completed = subprocess.run(
            [candidate, "--noprofile", "--norc", "-lc", "true"],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            return candidate

    pytest.skip("未找到可用 Bash，跳过 vwr.sh 交互式测试")


def _run_bash_script(*args: str, user_input: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            _find_bash(),
            "--noprofile",
            "--norc",
            "scripts/vwr.sh",
            *args,
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        input=user_input,
        capture_output=True,
        check=False,
    )


def test_vwr_sh_has_valid_bash_syntax() -> None:
    completed = subprocess.run(
        [_find_bash(), "--noprofile", "--norc", "-n", "scripts/vwr.sh"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_vwr_sh_without_args_enters_interactive_menu() -> None:
    completed = _run_bash_script(user_input="0\n")

    assert completed.returncode == 0, completed.stderr
    assert "交互式菜单" in completed.stdout
    assert "1. 环境初始化" in completed.stdout
    assert "8. 清理缓存与临时文件" in completed.stdout


def test_vwr_sh_menu_help_mentions_lama_torchscript_download_link() -> None:
    completed = _run_bash_script(user_input="H\n0\n")

    assert completed.returncode == 0, completed.stderr
    assert "big-lama.pt" in completed.stdout
    assert "VWR_LAMA_MODEL_PATH" in completed.stdout


def test_vwr_sh_rejects_legacy_tail_commands() -> None:
    completed = _run_bash_script("help")

    assert completed.returncode == 1
    assert "纯交互模式" in completed.stdout
    assert "请直接运行" in completed.stdout
