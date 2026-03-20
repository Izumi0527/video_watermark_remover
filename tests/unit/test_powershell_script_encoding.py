import re
from pathlib import Path


UTF8_BOM = b"\xef\xbb\xbf"
E2E_SCRIPT_PATHS = (
    Path("tests/e2e/ps1/test_audio_processing.ps1"),
    Path("tests/e2e/ps1/test_user_preferences.ps1"),
    Path("tests/e2e/ps1/test_end_to_end.ps1"),
)
LEGACY_RUNTIME_PATTERNS = {
    Path("tests/e2e/ps1/test_audio_processing.ps1"): ("detector.get_version(",),
    Path("tests/e2e/ps1/test_user_preferences.ps1"): (
        "prefs_manager.get_default_preferences(",
        "from app.config.style_manager import StyleManager",
        "style_manager = StyleManager(",
        "validate_preferences(",
        "reset_keys_to_defaults(",
        "migrate_preferences(",
    ),
    Path("tests/e2e/ps1/test_end_to_end.ps1"): (
        "config_manager.get_default_config(",
        "config_manager.validate_config(",
        "prefs_manager.get_default_preferences(",
    ),
}


def test_powershell_e2e_scripts_use_utf8_bom() -> None:
    """确保 Windows PowerShell 可正确解析包含中文的端到端脚本。"""
    missing_bom = []
    for script_path in E2E_SCRIPT_PATHS:
        content = script_path.read_bytes()
        if not content.startswith(UTF8_BOM):
            missing_bom.append(str(script_path))

    assert not missing_bom, f"以下 PowerShell 脚本缺少 UTF-8 BOM：{missing_bom}"


def test_powershell_e2e_scripts_do_not_shadow_common_verbose_parameter() -> None:
    """避免与 PowerShell 公共参数 -Verbose 冲突。"""
    duplicated_verbose = []
    for script_path in E2E_SCRIPT_PATHS:
        content = script_path.read_text(encoding="utf-8-sig")
        if "[switch]$Verbose" in content:
            duplicated_verbose.append(str(script_path))

    assert not duplicated_verbose, (
        f"以下 PowerShell 脚本仍声明了冲突的 Verbose 参数：{duplicated_verbose}"
    )


def test_powershell_e2e_scripts_set_src_pythonpath() -> None:
    """src 布局下，E2E 脚本必须显式把 src 注入 PYTHONPATH。"""
    missing_src_pythonpath = []

    for script_path in E2E_SCRIPT_PATHS:
        content = script_path.read_text(encoding="utf-8-sig")
        if 'Join-Path (Get-Location).Path "src"' not in content:
            missing_src_pythonpath.append(str(script_path))

    assert not missing_src_pythonpath, (
        f"以下 PowerShell 脚本未将 src 注入 PYTHONPATH：{missing_src_pythonpath}"
    )


def test_powershell_e2e_scripts_do_not_use_invalid_array_filter() -> None:
    """Get-ChildItem -Filter 只能接收单个字符串，不能传数组。"""
    invalid_filter_scripts = []

    for script_path in E2E_SCRIPT_PATHS:
        content = script_path.read_text(encoding="utf-8-sig")
        if '-Filter "*prefs*", "*test*"' in content or '-Filter "*temp*", "*test*"' in content:
            invalid_filter_scripts.append(str(script_path))

    assert not invalid_filter_scripts, (
        f"以下 PowerShell 脚本仍使用了非法的数组 Filter：{invalid_filter_scripts}"
    )


def test_vwr_prefers_pwsh_for_child_powershell_scripts() -> None:
    """统一脚本入口应优先使用 PowerShell 7 运行子脚本。"""
    content = Path("scripts/vwr.ps1").read_text(encoding="utf-8-sig")
    assert "Get-Command pwsh" in content


def test_powershell_e2e_scripts_do_not_reference_removed_runtime_apis() -> None:
    """运行态脚本不得再引用已移除或已过期的旧接口。"""
    invalid_references = []

    for script_path, legacy_patterns in LEGACY_RUNTIME_PATTERNS.items():
        content = script_path.read_text(encoding="utf-8-sig")
        for legacy_pattern in legacy_patterns:
            if legacy_pattern in content:
                invalid_references.append(f"{script_path}: {legacy_pattern}")

    assert not invalid_references, (
        "以下 PowerShell 脚本仍引用旧运行时接口："
        f"{invalid_references}"
    )


def test_powershell_e2e_scripts_use_python_execution_helper() -> None:
    """内联 Python 执行必须走统一 helper，并显式检查退出码。"""
    missing_helper = []
    missing_exitcode_guard = []
    legacy_inline_python = []

    for script_path in E2E_SCRIPT_PATHS:
        content = script_path.read_text(encoding="utf-8-sig")

        if "function Invoke-PythonSnippet" not in content:
            missing_helper.append(str(script_path))

        if "if ($LASTEXITCODE -ne 0)" not in content:
            missing_exitcode_guard.append(str(script_path))

        if re.search(r"\$\w+\s*=\s*python\s+-c\s+@\"", content):
            legacy_inline_python.append(str(script_path))

    assert not missing_helper, f"以下脚本尚未统一使用 Python helper：{missing_helper}"
    assert not missing_exitcode_guard, (
        f"以下脚本尚未检查 Python 退出码：{missing_exitcode_guard}"
    )
    assert not legacy_inline_python, (
        f"以下脚本仍直接使用 python -c 内联执行：{legacy_inline_python}"
    )
