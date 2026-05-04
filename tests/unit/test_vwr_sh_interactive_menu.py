from __future__ import annotations

import os
import re
import shutil
import subprocess
import textwrap
import uuid
from contextlib import contextmanager
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


def _strip_bash_dispatch_block(content: str) -> str:
    pattern = re.compile(
        r"\nif \[\[ \"\$#\" -gt 0 \]\]; then\n[\s\S]*?\nstart_interactive_menu\s*$",
        re.MULTILINE,
    )
    stripped, count = pattern.subn("\n", content)
    assert count == 1, "未能从 scripts/vwr.sh 中移除结尾入口块"
    return stripped


@contextmanager
def _local_harness_tmpdir():
    base_dir = Path.cwd() / ".tmp_test_harness"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = base_dir / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _run_bash_harness(harness: str) -> subprocess.CompletedProcess[str]:
    with _local_harness_tmpdir() as tmp_dir:
        project_root = tmp_dir / "project"
        scripts_dir = project_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        original_script = Path("scripts/vwr.sh").read_text(encoding="utf-8")
        stripped_script = _strip_bash_dispatch_block(original_script)
        test_script = scripts_dir / "vwr.sh"
        test_script.write_text(
            stripped_script + "\n\n" + textwrap.dedent(harness).strip() + "\n",
            encoding="utf-8",
        )

        return subprocess.run(
            [_find_bash(), "--noprofile", "--norc", str(test_script)],
            cwd=project_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            input="10\n2\nY\nY\n0\n",
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
    assert "10. 模型安装" in completed.stdout


def test_vwr_sh_menu_help_mentions_lama_torchscript_download_link() -> None:
    completed = _run_bash_script(user_input="H\n0\n")

    assert completed.returncode == 0, completed.stderr
    assert "big-lama.pt" in completed.stdout
    assert "VWR_LAMA_MODEL_PATH" in completed.stdout
    assert "模型安装" in completed.stdout


def test_vwr_sh_interactive_menu_dispatches_lama_model_install() -> None:
    completed = _run_bash_harness(
        """
        CALLS=()

        invoke_yolo_model_install() {
          CALLS+=("yolo:$1:$2:$3")
        }

        invoke_lama_torchscript_model_install() {
          CALLS+=("lama:$1:$2")
        }

        start_interactive_menu
        printf 'CALLS:%s\n' "${CALLS[*]}"
        """,
    )

    assert completed.returncode == 0, completed.stderr
    assert "CALLS:lama:1:1" in completed.stdout


def test_vwr_sh_rejects_legacy_tail_commands() -> None:
    completed = _run_bash_script("help")

    assert completed.returncode == 1
    assert "纯交互模式" in completed.stdout
    assert "请直接运行" in completed.stdout
