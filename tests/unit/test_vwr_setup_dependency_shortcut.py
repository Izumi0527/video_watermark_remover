from __future__ import annotations

import os
import hashlib
import json
import re
import shutil
import subprocess
import sys
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
    pytest.skip("未找到 PowerShell 可执行文件，跳过 vwr.ps1 定向测试")


def _strip_dispatch_block(content: str) -> str:
    pattern = re.compile(
        r"\ntry \{\n\s+switch \(\$Command\) \{[\s\S]*?exit 1\n\}\s*$",
        re.MULTILINE,
    )
    stripped, count = pattern.subn("\n", content)
    assert count == 1, "未能从 scripts/vwr.ps1 中移除结尾命令分发块"
    return stripped


def _build_requirements_signature(project_root: Path, entry_file: str) -> str:
    visited: set[Path] = set()
    parts: list[str] = []

    def walk(target: Path) -> None:
        resolved = target.resolve()
        if resolved in visited:
            return
        visited.add(resolved)

        content = resolved.read_bytes().decode("utf-8")
        relative = resolved.relative_to(project_root.resolve()).as_posix()
        parts.append(f"FILE:{relative}\n{content}\n")

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("-r "):
                walk((resolved.parent / line[3:].strip()).resolve())

    walk((project_root / entry_file).resolve())
    payload = "\n---\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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

    env = os.environ.copy()
    for leaked_name in (
        "UV_CACHE_DIR",
        "VWR_UV_CACHE_DIR",
        "VWR_LAMA_MODEL_PATH",
        "VWR_INPAINTING_MODEL_PATH",
    ):
        env.pop(leaked_name, None)

    completed = subprocess.run(
        [_find_pwsh(), "-NoProfile", "-File", str(test_script)],
        cwd=project_root,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        raise AssertionError(
            "PowerShell 测试脚本执行失败：\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    assert lines, "PowerShell 测试脚本未输出任何结果"
    return json.loads(lines[-1])


def test_get_lama_torchscript_download_url_returns_expected_release_link(
    tmp_path: Path,
) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $url = Get-LamaTorchScriptDownloadUrl
        @{ Url = $url } | ConvertTo-Json -Compress
        """,
    )

    assert (
        result["Url"]
        == "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"
    )


def test_show_lama_torchscript_hint_outputs_download_guidance(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $script:Infos = @()
        function global:Write-Info {
            param([string]$Message)
            $script:Infos += $Message
        }

        Show-LamaTorchScriptHint
        @{ Infos = $script:Infos } | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert any("big-lama.pt" in line for line in result["Infos"])
    assert any("VWR_LAMA_MODEL_PATH" in line for line in result["Infos"])


def test_vwr_help_mentions_lama_torchscript_download_link() -> None:
    completed = subprocess.run(
        [_find_pwsh(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/vwr.ps1", "help"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "big-lama.pt" in completed.stdout
    assert "VWR_LAMA_MODEL_PATH" in completed.stdout


def test_startup_precheck_guides_when_no_inpainting_assets_configured() -> None:
    with _local_harness_tmpdir() as tmp_dir:
        result = _run_powershell_harness(
            tmp_dir,
            """
        $script:Infos = @()
        $script:Warns = @()
        $script:Oks = @()

        function global:Write-Info {
            param([string]$Message)
            $script:Infos += $Message
        }
        function global:Write-Warn {
            param([string]$Message)
            $script:Warns += $Message
        }
        function global:Write-Ok {
            param([string]$Message)
            $script:Oks += $Message
        }

        Show-StartupInpaintingPrecheck -ConfigPath ""
        @{
            Infos = $script:Infos
            Warns = $script:Warns
            Oks = $script:Oks
        } | ConvertTo-Json -Depth 6 -Compress
            """,
        )

    assert any("LaMa" in line and "big-lama.pt" in line for line in result["Infos"])
    assert any("VWR_LAMA_MODEL_PATH" in line for line in result["Infos"])
    assert any("VWR_INPAINTING_MODEL_PATH" in line for line in result["Infos"])
    assert result["Warns"] == []
    assert result["Oks"] == []


def test_startup_precheck_warns_when_lama_env_path_missing() -> None:
    missing_path = "C:/missing-models/big-lama.pt"
    with _local_harness_tmpdir() as tmp_dir:
        result = _run_powershell_harness(
            tmp_dir,
            f"""
        $env:VWR_LAMA_MODEL_PATH = "{missing_path}"
        $script:Infos = @()
        $script:Warns = @()
        $script:Oks = @()

        function global:Write-Info {{
            param([string]$Message)
            $script:Infos += $Message
        }}
        function global:Write-Warn {{
            param([string]$Message)
            $script:Warns += $Message
        }}
        function global:Write-Ok {{
            param([string]$Message)
            $script:Oks += $Message
        }}

        Show-StartupInpaintingPrecheck -ConfigPath ""
        @{{
            Infos = $script:Infos
            Warns = $script:Warns
            Oks = $script:Oks
        }} | ConvertTo-Json -Depth 6 -Compress
            """,
        )

    assert any("VWR_LAMA_MODEL_PATH" in line and "不存在" in line for line in result["Warns"])
    assert any("big-lama.pt" in line for line in result["Infos"])
    assert result["Oks"] == []


def test_startup_precheck_reports_existing_lama_torchscript_asset() -> None:
    with _local_harness_tmpdir() as tmp_dir:
        result = _run_powershell_harness(
            tmp_dir,
            """
        New-Item -ItemType Directory -Path "models" -Force | Out-Null
        Set-Content -LiteralPath "models/big-lama.pt" -Value "stub" -Encoding ASCII

        $script:Infos = @()
        $script:Warns = @()
        $script:Oks = @()

        function global:Write-Info {
            param([string]$Message)
            $script:Infos += $Message
        }
        function global:Write-Warn {
            param([string]$Message)
            $script:Warns += $Message
        }
        function global:Write-Ok {
            param([string]$Message)
            $script:Oks += $Message
        }

        Show-StartupInpaintingPrecheck -ConfigPath ""
        @{
            Infos = $script:Infos
            Warns = $script:Warns
            Oks = $script:Oks
        } | ConvertTo-Json -Depth 6 -Compress
            """,
        )

    assert any("big-lama.pt" in line and "可直接用于 LaMa" in line for line in result["Oks"])
    assert result["Warns"] == []


def test_startup_precheck_is_called_during_invoke_run_environment_checks() -> None:
    python_path = sys.executable.replace("\\", "/")
    with _local_harness_tmpdir() as tmp_dir:
        result = _run_powershell_harness(
            tmp_dir,
            f"""
        Set-Content -LiteralPath "main.py" -Value @'
import json
import os
print(json.dumps({{"precheck_calls": int(os.environ.get("VWR_PRECHECK_CALLS", "0"))}}))
'@ -Encoding UTF8

        function global:Ensure-Uv {{}}
        function global:Get-VenvInfo {{
            return @{{
                Python = "{python_path}"
                Root = ".venv"
            }}
        }}
        function global:Ensure-ProjectImportable {{ param([switch]$AutoFixSetup) }}
        function global:Test-KeyPackages {{ param([switch]$FixIfMissing) return $true }}
        function global:Test-CommandExists {{ param([string]$Name) return $false }}
        function global:Show-StartupInpaintingPrecheck {{
            param([string]$ConfigPath)
            $env:VWR_PRECHECK_CALLS = "1"
        }}

        Invoke-Run
            """,
        )

    assert result["precheck_calls"] == 1


def test_setup_dependency_state_allows_skip_when_signature_matches_and_probes_pass(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "requirements.txt").write_text(
        "PyQt6>=6.6.0\nnumpy>=1.25.0\nPillow>=10.0.0\ntorch>=2.6.0\n",
        encoding="utf-8",
    )
    python_path = sys.executable.replace("\\", "/")
    state_dir = project_root / ".cache" / "setup-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "prod.json").write_text(
        json.dumps(
            {
                "DependencySet": "prod",
                "Signature": _build_requirements_signature(project_root, "requirements.txt"),
                "PythonPath": python_path,
            }
        ),
        encoding="utf-8",
    )

    result = _run_powershell_harness(
        tmp_path,
        f"""
        function global:Get-VenvInfo {{
            return @{{
                Python = "{python_path}"
                Root = ".venv"
            }}
        }}
        function global:Test-PythonDistributionInstalled {{
            param([string]$PythonPath, [string]$DistributionName)
            return $true
        }}

        $result = Test-SetupDependencyState -RequirementsFile "requirements.txt" -DependencySet "prod"
        $result | ConvertTo-Json -Depth 5 -Compress
        """,
    )

    assert result["Satisfied"] is True
    assert result["Reason"] == "state_match"


def test_setup_dependency_state_rejects_skip_when_dev_probe_missing(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "requirements.txt").write_text(
        "PyQt6>=6.6.0\nnumpy>=1.25.0\nPillow>=10.0.0\ntorch>=2.6.0\n",
        encoding="utf-8",
    )
    (project_root / "requirements-dev.txt").write_text(
        "-r requirements.txt\npytest>=8.0.0\nblack>=23.12.1\nmypy>=1.0.0\n",
        encoding="utf-8",
    )
    python_path = sys.executable.replace("\\", "/")
    state_dir = project_root / ".cache" / "setup-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "dev.json").write_text(
        json.dumps(
            {
                "DependencySet": "dev",
                "Signature": _build_requirements_signature(project_root, "requirements-dev.txt"),
                "PythonPath": python_path,
            }
        ),
        encoding="utf-8",
    )

    result = _run_powershell_harness(
        tmp_path,
        f"""
        function global:Get-VenvInfo {{
            return @{{
                Python = "{python_path}"
                Root = ".venv"
            }}
        }}
        function global:Test-PythonDistributionInstalled {{
            param([string]$PythonPath, [string]$DistributionName)
            return ($DistributionName -ne "pytest")
        }}

        $result = Test-SetupDependencyState -RequirementsFile "requirements-dev.txt" -DependencySet "dev"
        $result | ConvertTo-Json -Depth 5 -Compress
        """,
    )

    assert result["Satisfied"] is False
    assert result["Reason"] == "probe_missing"
    assert result["MissingPackages"] == ["pytest"]


def test_setup_dependency_state_probe_checks_use_venv_python_metadata(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "requirements.txt").write_text("numpy>=1.25.0\n", encoding="utf-8")
    python_path = sys.executable.replace("\\", "/")
    state_dir = project_root / ".cache" / "setup-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "prod.json").write_text(
        json.dumps(
            {
                "DependencySet": "prod",
                "Signature": _build_requirements_signature(project_root, "requirements.txt"),
                "PythonPath": python_path,
            }
        ),
        encoding="utf-8",
    )

    result = _run_powershell_harness(
        tmp_path,
        f"""
        $script:Calls = @()
        function global:Get-VenvInfo {{
            return @{{
                Python = "{python_path}"
                Root = ".venv"
            }}
        }}
        function global:Ensure-Uv {{
            throw "uv should not be called"
        }}
        function global:Test-PythonDistributionInstalled {{
            param([string]$PythonPath, [string]$DistributionName)
            $script:Calls += $DistributionName
            return $true
        }}

        $result = Test-SetupDependencyState -RequirementsFile "requirements.txt" -DependencySet "prod"
        @{{
            Satisfied = $result.Satisfied
            Reason = $result.Reason
            Calls = $script:Calls
        }} | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["Satisfied"] is True
    assert result["Reason"] == "state_match"
    assert result["Calls"] == ["PyQt6", "numpy", "Pillow", "torch"]


def test_setup_dependency_state_dev_signature_tracks_base_requirements(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".venv" / "Scripts").mkdir(parents=True, exist_ok=True)
    (project_root / ".venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    requirements_txt = project_root / "requirements.txt"
    requirements_txt.write_text("numpy>=1.25.0\n", encoding="utf-8")
    (project_root / "requirements-dev.txt").write_text(
        "-r requirements.txt\npytest>=8.0.0\n",
        encoding="utf-8",
    )
    state_dir = project_root / ".cache" / "setup-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "dev.json").write_text(
        json.dumps(
            {
                "DependencySet": "dev",
                "Signature": _build_requirements_signature(project_root, "requirements-dev.txt"),
                "PythonPath": str(project_root / ".venv" / "Scripts" / "python.exe"),
            }
        ),
        encoding="utf-8",
    )
    requirements_txt.write_text("numpy>=1.26.0\n", encoding="utf-8")

    result = _run_powershell_harness(
        tmp_path,
        """
        function global:Ensure-Uv {}
        function global:uv {
            param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Args)
            $global:LASTEXITCODE = 0
        }

        $result = Test-SetupDependencyState -RequirementsFile "requirements-dev.txt" -DependencySet "dev"
        $result | ConvertTo-Json -Depth 5 -Compress
        """,
    )

    assert result["Satisfied"] is False
    assert result["Reason"] == "signature_mismatch"


def test_invoke_setup_skips_dependency_install_when_state_is_satisfied(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $script:InstallCount = 0
        $script:EditableCount = 0
        $script:StateWriteCount = 0

        function global:Ensure-Venv { param([string]$PythonSelector) }
        function global:Get-VenvInfo {
            return @{
                Python = (Get-Command pwsh).Source
                Root = ".venv"
            }
        }
        function global:Test-SetupDependencyState {
            param([string]$RequirementsFile, [string]$DependencySet)
            return [pscustomobject]@{
                Satisfied = $true
                Reason = "state_match"
                MissingPackages = @()
            }
        }
        function global:Invoke-UvPipInstall { $script:InstallCount += 1 }
        function global:Write-SetupDependencyState { $script:StateWriteCount += 1 }
        function global:Install-EditableProject { param([switch]$NoDeps) $script:EditableCount += 1 }
        function global:Assert-ProjectImportable { return "src/app" }

        Invoke-Setup
        @{
            InstallCount = $script:InstallCount
            EditableCount = $script:EditableCount
            StateWriteCount = $script:StateWriteCount
        } | ConvertTo-Json -Compress
        """,
    )

    assert result == {
        "InstallCount": 0,
        "EditableCount": 1,
        "StateWriteCount": 0,
    }


def test_invoke_setup_runs_dependency_install_and_refreshes_state_when_needed(
    tmp_path: Path,
) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $script:InstallCount = 0
        $script:EditableCount = 0
        $script:StateWriteCount = 0

        function global:Ensure-Venv { param([string]$PythonSelector) }
        function global:Get-VenvInfo {
            return @{
                Python = (Get-Command pwsh).Source
                Root = ".venv"
            }
        }
        function global:Test-SetupDependencyState {
            param([string]$RequirementsFile, [string]$DependencySet)
            return [pscustomobject]@{
                Satisfied = $false
                Reason = "state_missing"
                MissingPackages = @()
            }
        }
        function global:Invoke-UvPipInstall { $script:InstallCount += 1 }
        function global:Write-SetupDependencyState { $script:StateWriteCount += 1 }
        function global:Install-EditableProject { param([switch]$NoDeps) $script:EditableCount += 1 }
        function global:Assert-ProjectImportable { return "src/app" }

        Invoke-Setup
        @{
            InstallCount = $script:InstallCount
            EditableCount = $script:EditableCount
            StateWriteCount = $script:StateWriteCount
        } | ConvertTo-Json -Compress
        """,
    )

    assert result == {
        "InstallCount": 1,
        "EditableCount": 1,
        "StateWriteCount": 1,
    }


def test_invoke_setup_dev_refreshes_prod_and_dev_state(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $script:InstallCount = 0
        $script:EditableCount = 0
        $script:StateWriteCount = 0
        $script:Dev = $true

        function global:Ensure-Venv { param([string]$PythonSelector) }
        function global:Get-VenvInfo {
            return @{
                Python = (Get-Command pwsh).Source
                Root = ".venv"
            }
        }
        function global:Test-SetupDependencyState {
            param([string]$RequirementsFile, [string]$DependencySet)
            return [pscustomobject]@{
                Satisfied = $false
                Reason = "state_missing"
                MissingPackages = @()
            }
        }
        function global:Invoke-UvPipInstall { $script:InstallCount += 1 }
        function global:Write-SetupDependencyState { $script:StateWriteCount += 1 }
        function global:Install-EditableProject { param([switch]$NoDeps) $script:EditableCount += 1 }
        function global:Assert-ProjectImportable { return "src/app" }

        Invoke-Setup
        @{
            InstallCount = $script:InstallCount
            EditableCount = $script:EditableCount
            StateWriteCount = $script:StateWriteCount
        } | ConvertTo-Json -Compress
        """,
    )

    assert result == {
        "InstallCount": 1,
        "EditableCount": 1,
        "StateWriteCount": 2,
    }


def test_install_editable_project_passes_project_uv_cache_dir(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        $script:CapturedArgs = @()
        function global:Get-VenvInfo {
            return @{
                Python = (Get-Command pwsh).Source
                Root = ".venv"
            }
        }
        function global:Ensure-Uv {}
        function Invoke-UvCommand {
            param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Args)
            $global:LASTEXITCODE = 0
            $script:CapturedArgs = @($Args)
        }

        Install-EditableProject -NoDeps
        @{
            Args = $script:CapturedArgs
        } | ConvertTo-Json -Compress
        """,
    )

    cache_arg = next(str(arg) for arg in result["Args"] if str(arg).startswith("--cache-dir="))
    assert cache_arg.endswith(".cache\\uv")


def test_invoke_uv_command_prefers_real_application_over_uv_function(tmp_path: Path) -> None:
    python_path = sys.executable.replace("\\", "/")
    result = _run_powershell_harness(
        tmp_path,
        """
        $fakeBin = Join-Path $PWD "fakebin"
        New-Item -ItemType Directory -Path $fakeBin -Force | Out-Null
        $capturePath = Join-Path $PWD "uv-args.txt"
        $fakeUv = Join-Path $fakeBin "uv.cmd"
        @'
@echo off
setlocal
> "%~dp0..\\uv-args.txt" echo %*
exit /b 0
'@ | Set-Content -LiteralPath $fakeUv -Encoding ASCII

        $env:PATH = $fakeBin + ";" + $env:PATH
        function global:uv {
            throw "wrapper function should not be called"
        }
        function global:Get-VenvInfo {
            return @{
                Python = "__PYTHON__"
                Root = ".venv"
            }
        }
        function global:Ensure-Uv {}

        Install-EditableProject -NoDeps
        @{
            Args = (Get-Content -LiteralPath $capturePath -Raw -Encoding UTF8).Trim()
        } | ConvertTo-Json -Compress
        """.replace("__PYTHON__", python_path),
    )

    assert result["Args"].startswith("pip install --python ")
    assert "--cache-dir=" in result["Args"]
    assert "--no-deps" in result["Args"]


def test_install_editable_project_falls_back_to_pth_bridge_on_permission_denied(
    tmp_path: Path,
) -> None:
    result = _run_powershell_harness(
        tmp_path,
        """
        New-Item -ItemType Directory -Force ".venv/Lib/site-packages" | Out-Null
        New-Item -ItemType Directory -Force "src/app" | Out-Null
        Set-Content -LiteralPath "src/app/__init__.py" -Value "# test" -Encoding UTF8
        function global:Get-VenvInfo {
            return @{
                Python = (Get-Command pwsh).Source
                Root = ".venv"
            }
        }
        function global:Ensure-Uv {}
        function Invoke-UvCommand {
            param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Args)
            $global:LASTEXITCODE = 1
            Write-Output "PermissionError: [WinError 5] 拒绝访问。"
            Write-Output "Call to setuptools.build_meta.build_editable failed"
        }

        Install-EditableProject -NoDeps
        $pthPath = ".venv/Lib/site-packages/video_watermark_remover_local_editable.pth"
        @{
            PthExists = (Test-Path -LiteralPath $pthPath)
            PthContent = (Get-Content -LiteralPath $pthPath -Raw -Encoding UTF8)
        } | ConvertTo-Json -Compress
        """,
    )

    assert result["PthExists"] is True
    assert result["PthContent"].strip().endswith("\\src")


def test_install_editable_project_keeps_throwing_for_unknown_failure(
    tmp_path: Path,
) -> None:
    with pytest.raises(AssertionError, match="当前项目 editable 安装失败（退出码：1）。"):
        _run_powershell_harness(
            tmp_path,
            """
            function global:Get-VenvInfo {
                return @{
                Python = (Get-Command pwsh).Source
                Root = ".venv"
            }
        }
        function global:Ensure-Uv {}
            function Invoke-UvCommand {
                param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Args)
                $global:LASTEXITCODE = 1
                Write-Output "error: invalid editable metadata"
            }

            Install-EditableProject -NoDeps
            """,
        )


def test_test_key_packages_use_venv_python_metadata(tmp_path: Path) -> None:
    python_path = sys.executable.replace("\\", "/")
    result = _run_powershell_harness(
        tmp_path,
        f"""
        Set-Content -LiteralPath "requirements.txt" -Value "numpy>=1.25.0" -Encoding UTF8
        $script:Calls = @()
        function global:Get-VenvInfo {{
            return @{{
                Python = "{python_path}"
                Root = ".venv"
            }}
        }}
        function global:Ensure-Uv {{
            throw "uv should not be called"
        }}
        function global:Test-PythonDistributionInstalled {{
            param([string]$PythonPath, [string]$DistributionName)
            $script:Calls += $DistributionName
            return $true
        }}

        $result = Test-KeyPackages
        @{{
            Result = $result
            Calls = $script:Calls
        }} | ConvertTo-Json -Depth 6 -Compress
        """,
    )

    assert result["Result"] is True
    assert result["Calls"] == ["PyQt6", "opencv-python", "numpy", "Pillow", "torch", "ultralytics"]


def test_ensure_uv_resolves_application_even_if_uv_function_hijacked(
    tmp_path: Path,
) -> None:
    if sys.platform != "win32":
        pytest.skip("仅 Windows 需要验证 uv 可执行文件解析逻辑")

    result = _run_powershell_harness(
        tmp_path,
        r"""
        $fakeBin = Join-Path $ProjectRoot "fake-bin"
        New-Item -ItemType Directory -Path $fakeBin -Force | Out-Null

        $uvCmd = Join-Path $fakeBin "uv.cmd"
        Set-Content -LiteralPath $uvCmd -Value @'
@echo off
if "%1"=="--version" (
  echo uv 999.0.0
) else (
  echo ok
)
exit /b 0
'@ -Encoding ASCII

        $env:PATH = "$fakeBin;$env:PATH"

        function uv { throw "hijacked uv should not be called" }

        Ensure-Uv
        @{
            UvExe = (Get-UvExecutablePath)
        } | ConvertTo-Json -Compress
        """,
    )

    uv_exe = result["UvExe"].replace("\\", "/").lower()
    assert "/fake-bin/" in uv_exe
    assert uv_exe.endswith("/uv.cmd")


def test_get_uv_cache_args_repairs_empty_process_env(tmp_path: Path) -> None:
    result = _run_powershell_harness(
        tmp_path,
        r"""
        $env:UV_CACHE_DIR = ""
        $env:VWR_UV_CACHE_DIR = ""

        $args = @(Get-UvCacheArgs)
        @{
            Args = $args
            Uv = $env:UV_CACHE_DIR
            Vwr = $env:VWR_UV_CACHE_DIR
        } | ConvertTo-Json -Compress
        """,
    )

    assert isinstance(result["Args"], list)
    assert len(result["Args"]) == 1
    assert result["Args"][0].startswith("--cache-dir=")
    assert result["Uv"]
    assert result["Vwr"]
    assert result["Uv"] == result["Vwr"]
