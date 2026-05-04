from __future__ import annotations

import json
import re
import shutil
import subprocess
import textwrap
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest


def _find_pwsh() -> str:
    for candidate in ("pwsh", "powershell"):
        executable = shutil.which(candidate)
        if executable:
            return executable
    pytest.skip("未找到 PowerShell 可执行文件，跳过 vwr.ps1 交互式测试")


def _strip_dispatch_block(content: str) -> str:
    pattern = re.compile(
        r"\ntry \{\n[\s\S]*?exit 1\n\}\s*$",
        re.MULTILINE,
    )
    stripped, count = pattern.subn("\n", content)
    assert count == 1, "未能从 scripts/vwr.ps1 中移除结尾入口块"
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


@pytest.fixture
def tmp_path():
    with _local_harness_tmpdir() as tmp_dir:
        yield tmp_dir


def _run_powershell_harness(tmp_path: Path, harness: str) -> dict:
    project_root = tmp_path / "project"
    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    original_script = Path("scripts/vwr.ps1").read_text(encoding="utf-8-sig")
    stripped_script = _strip_dispatch_block(original_script)
    test_script = scripts_dir / "vwr.ps1"
    test_script.write_text(
        stripped_script + "\n\n" + textwrap.dedent(harness).strip() + "\n",
        encoding="utf-8-sig",
    )

    completed = subprocess.run(
        [_find_pwsh(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(test_script)],
        cwd=project_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        raise AssertionError(
            "PowerShell harness 执行失败：\n" f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    assert lines, "PowerShell harness 未输出任何结果"
    return json.loads(lines[-1])


def _run_script_with_input(*args: str, user_input: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            _find_pwsh(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/vwr.ps1",
            *args,
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        input=user_input,
        capture_output=True,
        check=False,
    )


def test_vwr_without_args_enters_interactive_menu() -> None:
    completed = _run_script_with_input(user_input="0\n")

    assert completed.returncode == 0, completed.stderr
    assert "交互式菜单" in completed.stdout
    assert "1. 环境初始化" in completed.stdout
    assert "8. 清理缓存与临时文件" in completed.stdout
    assert "10. 模型安装" in completed.stdout


def test_vwr_rejects_legacy_tail_commands() -> None:
    completed = _run_script_with_input("help")

    assert completed.returncode == 1
    assert "纯交互模式" in completed.stdout
    assert "请直接运行" in completed.stdout


def test_start_interactive_menu_dispatches_test_unit_quick(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $script:MockAnswers = @("4", "1", "Y", "N", "N", "N", "0")
        $script:Calls = @()

        function global:Read-Host {
            param([string]$Prompt)

            if ($script:MockAnswers.Count -eq 0) {
                throw "输入队列已耗尽：$Prompt"
            }

            $value = $script:MockAnswers[0]
            if ($script:MockAnswers.Count -gt 1) {
                $script:MockAnswers = @($script:MockAnswers[1..($script:MockAnswers.Count - 1)])
            } else {
                $script:MockAnswers = @()
            }
            return $value
        }

        function global:Invoke-Test {
            $script:Calls += [ordered]@{
                Command = "test"
                Arg1 = $script:Arg1
                Quick = [bool]$script:Quick
                Coverage = [bool]$script:Coverage
                Performance = [bool]$script:Performance
                Report = [bool]$script:Report
            }
        }

        Start-InteractiveMenu
        @{ Calls = $script:Calls } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["Calls"] == [
        {
            "Command": "test",
            "Arg1": "unit",
            "Quick": True,
            "Coverage": False,
            "Performance": False,
            "Report": False,
        }
    ]


def test_start_interactive_menu_dispatches_yolo_model_install(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $script:MockAnswers = @("10", "1", "2", "Y", "Y", "0")
        $script:Calls = @()

        function global:Read-Host {
            param([string]$Prompt)

            if ($script:MockAnswers.Count -eq 0) {
                throw "输入队列已耗尽：$Prompt"
            }

            $value = $script:MockAnswers[0]
            if ($script:MockAnswers.Count -gt 1) {
                $script:MockAnswers = @($script:MockAnswers[1..($script:MockAnswers.Count - 1)])
            } else {
                $script:MockAnswers = @()
            }
            return $value
        }

        function global:Invoke-YoloModelInstall {
            param(
                [string]$ModelKey,
                [switch]$Force,
                [switch]$UpdateConfig
            )

            $script:Calls += [ordered]@{
                Command = "yolo"
                ModelKey = $ModelKey
                Force = [bool]$Force
                UpdateConfig = [bool]$UpdateConfig
            }
        }

        Start-InteractiveMenu
        @{ Calls = $script:Calls } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["Calls"] == [
        {
            "Command": "yolo",
            "ModelKey": "yolo11x-watermark-corzent",
            "Force": True,
            "UpdateConfig": True,
        }
    ]


def test_start_interactive_menu_dispatches_lama_model_install(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $script:MockAnswers = @("10", "2", "Y", "Y", "0")
        $script:Calls = @()

        function global:Read-Host {
            param([string]$Prompt)

            if ($script:MockAnswers.Count -eq 0) {
                throw "输入队列已耗尽：$Prompt"
            }

            $value = $script:MockAnswers[0]
            if ($script:MockAnswers.Count -gt 1) {
                $script:MockAnswers = @($script:MockAnswers[1..($script:MockAnswers.Count - 1)])
            } else {
                $script:MockAnswers = @()
            }
            return $value
        }

        function global:Invoke-YoloModelInstall {
            param(
                [string]$ModelKey,
                [switch]$Force,
                [switch]$UpdateConfig
            )

            $script:Calls += [ordered]@{
                Command = "yolo"
                ModelKey = $ModelKey
                Force = [bool]$Force
                UpdateConfig = [bool]$UpdateConfig
            }
        }

        function global:Invoke-LamaTorchScriptModelInstall {
            param(
                [switch]$Force,
                [switch]$UpdateConfig
            )

            $script:Calls += [ordered]@{
                Command = "lama"
                Force = [bool]$Force
                UpdateConfig = [bool]$UpdateConfig
            }
        }

        Start-InteractiveMenu
        @{ Calls = $script:Calls } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["Calls"] == [
        {
            "Command": "lama",
            "Force": True,
            "UpdateConfig": True,
        }
    ]


def test_resolve_clean_targets_all_includes_temp_and_cache_targets(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $targets = Resolve-CleanTargets -Scope "all"
        @{
            Paths = @($targets | ForEach-Object { $_.Path })
        } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert ".mypy_cache" in result["Paths"]
    assert ".pytest_cache" in result["Paths"]
    assert ".cache/tmp" in result["Paths"]
    assert ".cache/pytest" in result["Paths"]
    assert ".cache/tests" in result["Paths"]
    assert ".pytest_tmp" in result["Paths"]
    assert ".tmp_test_harness" in result["Paths"]
    assert "pytest-cache-files-*" in result["Paths"]
    assert "tmp_*" in result["Paths"]
    assert "test_output" in result["Paths"]
    assert "tests/.cache" in result["Paths"]
    assert "tests/test_data/runtime_tmp" in result["Paths"]


def test_resolve_clean_targets_deep_includes_egg_info_metadata(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $targets = Resolve-CleanTargets -Scope "deep"
        @{
            Paths = @($targets | ForEach-Object { $_.Path })
        } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert "src/video_watermark_remover.egg-info" in result["Paths"]


def test_resolve_clean_targets_deep_includes_uv_cache(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $targets = Resolve-CleanTargets -Scope "deep"
        @{
            Paths = @($targets | ForEach-Object { $_.Path })
        } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert ".uv-cache" in result["Paths"]


def test_invoke_clean_all_removes_temp_and_cache_files_but_preserves_runtime_assets(
    tmp_path: Path,
) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        New-Item -ItemType Directory -Path ".mypy_cache" -Force | Out-Null
        Set-Content -LiteralPath ".mypy_cache/cache.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path ".cache/tmp/run_case" -Force | Out-Null
        Set-Content -LiteralPath ".cache/tmp/run_case/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path ".cache/pytest/pytest_case" -Force | Out-Null
        Set-Content -LiteralPath ".cache/pytest/pytest_case/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path ".cache/tests/ui-components" -Force | Out-Null
        Set-Content -LiteralPath ".cache/tests/ui-components/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path ".tmp_test_harness/case_local" -Force | Out-Null
        Set-Content -LiteralPath ".tmp_test_harness/case_local/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path "pytest-cache-files-case01/data" -Force | Out-Null
        Set-Content -LiteralPath "pytest-cache-files-case01/data/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path "tmp_test_preferences/case_local" -Force | Out-Null
        Set-Content -LiteralPath "tmp_test_preferences/case_local/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path "test_output" -Force | Out-Null
        Set-Content -LiteralPath "test_output/result.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path "tests/.cache/pytest-task6-local" -Force | Out-Null
        Set-Content -LiteralPath "tests/.cache/pytest-task6-local/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path "tests/test_data/runtime_tmp/e2e" -Force | Out-Null
        Set-Content -LiteralPath "tests/test_data/runtime_tmp/e2e/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path "__pycache__" -Force | Out-Null
        Set-Content -LiteralPath "__pycache__/main.cpython-312.pyc" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path "src/app/__pycache__" -Force | Out-Null
        Set-Content -LiteralPath "src/app/__pycache__/module.pyc" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path "tests/unit/__pycache__" -Force | Out-Null
        Set-Content -LiteralPath "tests/unit/__pycache__/test_module.pyc" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path ".venv" -Force | Out-Null
        Set-Content -LiteralPath ".venv/keep.txt" -Value "keep" -Encoding ASCII

        New-Item -ItemType Directory -Path "models" -Force | Out-Null
        Set-Content -LiteralPath "models/model.bin" -Value "keep" -Encoding ASCII

        New-Item -ItemType Directory -Path "release" -Force | Out-Null
        Set-Content -LiteralPath "release/app.exe" -Value "keep" -Encoding ASCII

        Invoke-Clean -Scope "all" -SkipConfirm

        @{
            MypyCacheExists = Test-Path ".mypy_cache"
            TempRootExists = Test-Path ".cache/tmp"
            PytestTempExists = Test-Path ".cache/pytest"
            TestsRuntimeCacheExists = Test-Path ".cache/tests"
            CacheRootExists = Test-Path ".cache"
            HarnessTempExists = Test-Path ".tmp_test_harness"
            PytestCacheFilesExists = Test-Path "pytest-cache-files-case01"
            TmpPatternExists = Test-Path "tmp_test_preferences"
            TestOutputExists = Test-Path "test_output"
            TestsCacheExists = Test-Path "tests/.cache"
            RuntimeTmpExists = Test-Path "tests/test_data/runtime_tmp"
            RootPycacheExists = Test-Path "__pycache__"
            SrcPycacheExists = Test-Path "src/app/__pycache__"
            TestsPycacheExists = Test-Path "tests/unit/__pycache__"
            VenvExists = Test-Path ".venv/keep.txt"
            ModelsExists = Test-Path "models/model.bin"
            ReleaseExists = Test-Path "release/app.exe"
        } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["MypyCacheExists"] is False
    assert result["TempRootExists"] is False
    assert result["PytestTempExists"] is False
    assert result["TestsRuntimeCacheExists"] is False
    assert result["CacheRootExists"] is False
    assert result["HarnessTempExists"] is False
    assert result["PytestCacheFilesExists"] is False
    assert result["TmpPatternExists"] is False
    assert result["TestOutputExists"] is False
    assert result["TestsCacheExists"] is False
    assert result["RuntimeTmpExists"] is False
    assert result["RootPycacheExists"] is False
    assert result["SrcPycacheExists"] is False
    assert result["TestsPycacheExists"] is False
    assert result["VenvExists"] is True
    assert result["ModelsExists"] is True
    assert result["ReleaseExists"] is True


def test_invoke_clean_all_preserves_cache_root_when_unmanaged_entries_remain(
    tmp_path: Path,
) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        New-Item -ItemType Directory -Path ".cache/tmp/run_case" -Force | Out-Null
        Set-Content -LiteralPath ".cache/tmp/run_case/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path ".cache/custom-keep" -Force | Out-Null
        Set-Content -LiteralPath ".cache/custom-keep/keep.txt" -Value "keep" -Encoding ASCII

        Invoke-Clean -Scope "all" -SkipConfirm

        @{
            TempRootExists = Test-Path ".cache/tmp"
            CacheRootExists = Test-Path ".cache"
            CustomKeepExists = Test-Path ".cache/custom-keep/keep.txt"
        } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["TempRootExists"] is False
    assert result["CacheRootExists"] is True
    assert result["CustomKeepExists"] is True


def test_invoke_clean_temp_continues_after_permission_denied_and_reports_summary(
    tmp_path: Path,
) -> None:
    result = _run_powershell_harness(
        tmp_path,
        r"""
        New-Item -ItemType Directory -Path ".cache/tmp/ok-dir" -Force | Out-Null
        Set-Content -LiteralPath ".cache/tmp/ok-dir/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path ".cache/tmp/locked-dir" -Force | Out-Null
        Set-Content -LiteralPath ".cache/tmp/locked-dir/temp.txt" -Value "x" -Encoding ASCII

        New-Item -ItemType Directory -Path ".cache/pytest/ok-dir" -Force | Out-Null
        Set-Content -LiteralPath ".cache/pytest/ok-dir/temp.txt" -Value "x" -Encoding ASCII

        $script:Warns = @()
        $script:Oks = @()

        function global:Write-Warn {
            param([string]$Message)
            $script:Warns += $Message
        }

        function global:Write-Ok {
            param([string]$Message)
            $script:Oks += $Message
        }

        function global:Test-IsElevated {
            return $false
        }

        function global:Remove-Item {
            param(
                [string]$Path,
                [string]$LiteralPath,
                [switch]$Recurse,
                [switch]$Force,
                [Parameter(ValueFromRemainingArguments = $true)]
                [object[]]$Remaining
            )

            $target = if ($PSBoundParameters.ContainsKey("LiteralPath")) { $LiteralPath } else { $Path }
            $normalized = ([string]$target).Replace("/", "\")

            if ($normalized -match '(^|\\)\.cache\\tmp$') {
                throw [System.UnauthorizedAccessException]::new("Access is denied.")
            }

            if ($normalized -match 'locked-dir') {
                throw [System.UnauthorizedAccessException]::new("Access is denied.")
            }

            $forward = @{}
            foreach ($entry in $PSBoundParameters.GetEnumerator()) {
                if ($entry.Key -eq "Remaining") {
                    continue
                }
                $forward[$entry.Key] = $entry.Value
            }
            Microsoft.PowerShell.Management\Remove-Item @forward
        }

        Invoke-Clean -Scope "temp" -SkipConfirm

        @{
            TmpOkRemoved = -not (Test-Path ".cache/tmp/ok-dir")
            LockedStillExists = Test-Path ".cache/tmp/locked-dir"
            PytestOkRemoved = -not (Test-Path ".cache/pytest/ok-dir")
            Warns = $script:Warns
            Oks = $script:Oks
        } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["TmpOkRemoved"] is True
    assert result["LockedStillExists"] is True
    assert result["PytestOkRemoved"] is True
    assert any("失败" in line for line in result["Warns"])
    assert any("管理员" in line for line in result["Warns"])
    assert any("继续处理其余项" in line for line in result["Warns"])


def test_invoke_clean_deep_removes_uv_cache(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        New-Item -ItemType Directory -Path ".uv-cache/builds-v0/.tmp-build" -Force | Out-Null
        Set-Content -LiteralPath ".uv-cache/builds-v0/.tmp-build/cache.txt" -Value "x" -Encoding ASCII

        Invoke-Clean -Scope "deep" -SkipConfirm

        @{
            UvCacheExists = Test-Path ".uv-cache"
        } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["UvCacheExists"] is False
