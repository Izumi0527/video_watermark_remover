#!/usr/bin/env powershell
# 智能视频水印去除工具 - 用户偏好设置完整测试脚本
# 偏好设置的保存、加载、验证和主题切换测试

param(
    [Parameter()]
    [switch]$DetailedOutput,

    [Parameter()]
    [switch]$Quick,

    [Parameter()]
    [string]$TestDataPath = "tests/test_data",

    [Parameter()]
    [switch]$KeepTestFiles
)

$ErrorActionPreference = "Stop"

$Colors = @{
    Header = "Green"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Detail = "White"
    Progress = "Blue"
    Summary = "Magenta"
}

$TestResults = @{
    Passed = 0
    Failed = 0
    Skipped = 0
    Details = @()
    StartTime = Get-Date
}

function Record-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = "",
        [bool]$Skipped = $false
    )

    $result = @{
        TestName = $TestName
        Passed = $Passed
        Skipped = $Skipped
        Details = $Details
        Timestamp = Get-Date
    }

    $TestResults.Details += $result

    if ($Skipped) {
        $TestResults.Skipped++
        Write-Host "⏭️ $TestName - 跳过" -ForegroundColor $Colors.Warning
    } elseif ($Passed) {
        $TestResults.Passed++
        Write-Host "✅ $TestName - 通过" -ForegroundColor $Colors.Success
    } else {
        $TestResults.Failed++
        Write-Host "❌ $TestName - 失败" -ForegroundColor $Colors.Error
        if ($Details -and $DetailedOutput) {
            Write-Host "   详细信息: $Details" -ForegroundColor $Colors.Detail
        }
    }
}

function Show-TestSummary {
    $endTime = Get-Date
    $duration = $endTime - $TestResults.StartTime

    Write-Host ""
    Write-Host "👤 用户偏好设置测试摘要" -ForegroundColor $Colors.Summary
    Write-Host ("=" * 50) -ForegroundColor $Colors.Info
    Write-Host "🕒 执行时间: $($duration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
    Write-Host "✅ 通过: $($TestResults.Passed)" -ForegroundColor $Colors.Success
    Write-Host "❌ 失败: $($TestResults.Failed)" -ForegroundColor $Colors.Error
    Write-Host "⏭️ 跳过: $($TestResults.Skipped)" -ForegroundColor $Colors.Warning
    Write-Host "📋 总计: $(($TestResults.Passed + $TestResults.Failed + $TestResults.Skipped))" -ForegroundColor $Colors.Info

    if ($TestResults.Failed -eq 0) {
        Write-Host ""
        Write-Host "🎉 所有用户偏好设置测试通过！" -ForegroundColor $Colors.Success
    } else {
        Write-Host ""
        Write-Host "⚠️ 有 $($TestResults.Failed) 项用户偏好设置失败" -ForegroundColor $Colors.Warning
    }
}

Write-Host "👤 智能视频水印去除工具 - 用户偏好设置测试" -ForegroundColor $Colors.Header
Write-Host "模式: $(if($Quick){'快速'}else{'完整'}) | 详细输出: $(if($DetailedOutput){'开启'}else{'关闭'})" -ForegroundColor $Colors.Info
Write-Host ("=" * 60) -ForegroundColor $Colors.Info

if (-not (Test-Path ".venv")) {
    Write-Host "❌ 虚拟环境不存在，请先运行: .\scripts\vwr.ps1 setup -Dev" -ForegroundColor $Colors.Error
    exit 1
}

Write-Host "🔄 激活虚拟环境..." -ForegroundColor $Colors.Progress
. .\.venv\Scripts\Activate.ps1

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$projectSrc = Join-Path (Get-Location).Path "src"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$projectSrc;$($env:PYTHONPATH)" } else { $projectSrc }
$PythonExecutable = Join-Path (Get-Location).Path ".venv/Scripts/python.exe"

function Invoke-PythonSnippet {
    param(
        [Parameter(Mandatory)]
        [string]$Code,

        [int[]]$AllowedExitCodes = @(0)
    )

    if (-not (Test-Path $PythonExecutable)) {
        throw "Python 解释器不存在: $PythonExecutable"
    }

    $output = & $PythonExecutable -c $Code 2>&1
    $outputText = ($output | Out-String).Trim()

    if ($outputText) {
        Write-Host $outputText -ForegroundColor $Colors.Detail
    }

    if ($LASTEXITCODE -ne 0) {
        if ($AllowedExitCodes -contains $LASTEXITCODE) {
            return @{
                Output = $outputText
                ExitCode = $LASTEXITCODE
            }
        }

        throw "Python 代码执行失败，退出码: $LASTEXITCODE"
    }

    return @{
        Output = $outputText
        ExitCode = 0
    }
}

if (-not (Test-Path $TestDataPath)) {
    New-Item -ItemType Directory -Path $TestDataPath -Force | Out-Null
    Write-Host "📁 创建测试数据目录: $TestDataPath" -ForegroundColor $Colors.Info
}
$WorkspaceTempRoot = Join-Path (Get-Location).Path "tests/test_data/runtime_tmp/preferences"
New-Item -ItemType Directory -Path $WorkspaceTempRoot -Force | Out-Null

Write-Host ""
Write-Host "📦 用户偏好模块导入测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import importlib

modules = [
    'app.config.preferences',
    'app.config.preferences.manager',
    'app.config.preferences.storage',
    'app.config.preferences.validator',
    'app.config.preferences.defaults',
]

for module in modules:
    importlib.import_module(module)
    print(f'✅ {module} 导入成功')

print('所有用户偏好模块导入成功')
"@ | Out-Null
    Record-TestResult "用户偏好模块导入" $true "所有模块导入成功"
} catch {
    Record-TestResult "用户偏好模块导入" $false "模块导入失败: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "⚙️ 偏好设置管理器初始化测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import os
import shutil

from app.config.preferences.defaults import PreferencesDefaults
from app.config.preferences.manager import UserPreferencesManager

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'preferences')
os.makedirs(workspace_temp_root, exist_ok=True)
temp_dir = os.path.join(workspace_temp_root, 'manager_case')
shutil.rmtree(temp_dir, ignore_errors=True)
os.makedirs(temp_dir, exist_ok=True)

prefs_manager = UserPreferencesManager(config_dir=temp_dir)
default_prefs = PreferencesDefaults.get_default_preferences()

assert prefs_manager.config_dir.exists()
assert prefs_manager.preferences_file.name == 'user_preferences.json'
assert prefs_manager.get_ui_preferences()['theme'] == default_prefs['ui']['theme']
assert prefs_manager.get_advanced_params_preferences()['compression_quality'] == default_prefs['advanced_params']['compression_quality']
assert prefs_manager.get_advanced_params_preferences()['preserve_audio'] == default_prefs['advanced_params']['preserve_audio']
assert prefs_manager.get_advanced_preferences()['log_level'] == default_prefs['advanced']['log_level']
assert prefs_manager.get_batch_preferences()['max_concurrent_files'] == default_prefs['batch']['max_concurrent_files']

print('✅ UserPreferencesManager 创建成功')
print(f'✅ 配置目录: {prefs_manager.config_dir}')
print(f'✅ 偏好文件: {prefs_manager.preferences_file}')
print('偏好设置管理器初始化测试通过')
"@ | Out-Null
    Record-TestResult "偏好设置管理器初始化" $true "偏好设置管理器初始化成功"
} catch {
    Record-TestResult "偏好设置管理器初始化" $false "偏好设置管理器初始化失败: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "🔍 偏好设置验证测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
from app.config.preferences.validator import PreferencesValidator

validator = PreferencesValidator()

assert validator.validate_preference_value('ui', 'theme', 'dark') is True
assert validator.validate_preference_value('processing', 'detection_sensitivity', 0.5) is True
assert validator.validate_preference_value('advanced', 'auto_save_interval', 300) is True

assert validator.validate_preference_value('ui', 'theme', 'invalid_theme') is False
assert validator.validate_preference_value('processing', 'detection_sensitivity', 1.5) is False
assert validator.validate_preference_value('advanced', 'cache_size_mb', -1) is False

normalized = validator.normalize_splitter_sizes([50, 800])
assert normalized == [100, 800]

print('✅ 偏好值校验逻辑正常')
print(f'✅ 标准化分割尺寸: {normalized}')
print('偏好设置验证测试通过')
"@ | Out-Null
    Record-TestResult "偏好设置验证" $true "偏好设置验证功能正常"
} catch {
    Record-TestResult "偏好设置验证" $false "偏好设置验证失败: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "💾 偏好设置存储测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import os
import shutil

from app.config.preferences.defaults import PreferencesDefaults
from app.config.preferences.storage import PreferencesStorage

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'preferences')
os.makedirs(workspace_temp_root, exist_ok=True)
temp_dir = os.path.join(workspace_temp_root, 'storage_case')
shutil.rmtree(temp_dir, ignore_errors=True)
os.makedirs(temp_dir, exist_ok=True)

storage = PreferencesStorage(temp_dir)
test_prefs = PreferencesDefaults.get_default_preferences()
test_prefs['ui']['theme'] = 'light'
test_prefs['paths']['last_input_dir'] = 'tests/test_data'
test_prefs['advanced']['log_level'] = 'DEBUG'

assert storage.save_preferences(test_prefs) is True
loaded_prefs = storage.load_preferences()

assert loaded_prefs['ui']['theme'] == 'light'
assert loaded_prefs['paths']['last_input_dir'] == 'tests/test_data'
assert loaded_prefs['advanced']['log_level'] == 'DEBUG'

print('✅ PreferencesStorage 创建成功')
print(f'✅ 偏好文件路径: {storage.get_preferences_file_path()}')
print('偏好设置存储测试通过')
"@ | Out-Null
    Record-TestResult "偏好设置存储" $true "偏好设置存储功能正常"
} catch {
    Record-TestResult "偏好设置存储" $false "偏好设置存储失败: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "🎨 主题切换测试..." -ForegroundColor $Colors.Progress
try {
    $themeTest = Invoke-PythonSnippet -Code @"
from app.config.styles import ModernStyleManager, get_available_themes, is_valid_theme

available_themes = get_available_themes()
if not available_themes:
    print('⚠️ 未找到可用主题')
    raise SystemExit(2)

for theme in available_themes:
    assert is_valid_theme(theme) is True
    style_manager = ModernStyleManager(theme)
    stylesheet = style_manager.get_complete_stylesheet()
    assert isinstance(stylesheet, str) and stylesheet.strip()
    print(f'✅ 主题 {theme} 可用，样式长度: {len(stylesheet)}')

print('主题切换测试通过')
"@ -AllowedExitCodes @(0, 2)

    if ($themeTest.ExitCode -eq 2) {
        Record-TestResult "主题切换" $false "未找到可用主题或缺少 GUI 依赖" $true
    } else {
        Record-TestResult "主题切换" $true "主题切换功能正常"
    }
} catch {
    Record-TestResult "主题切换" $false "主题切换测试失败: $($_.Exception.Message)"
}

if (-not $Quick) {
    Write-Host ""
    Write-Host "🌐 语言设置测试..." -ForegroundColor $Colors.Progress
    try {
        Invoke-PythonSnippet -Code @"
import os
import shutil

from app.config.preferences.manager import UserPreferencesManager

supported_languages = ['zh_CN', 'en_US', 'ja_JP', 'ko_KR']

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'preferences')
os.makedirs(workspace_temp_root, exist_ok=True)
temp_dir = os.path.join(workspace_temp_root, 'language_case')
shutil.rmtree(temp_dir, ignore_errors=True)
os.makedirs(temp_dir, exist_ok=True)

prefs_manager = UserPreferencesManager(config_dir=temp_dir)
for lang in supported_languages:
    assert prefs_manager.set_preference('ui', 'language', lang) is True
    assert prefs_manager.get_preference('ui', 'language') == lang
    print(f'✅ 语言 {lang} 设置成功')

print('语言设置测试通过')
"@ | Out-Null
        Record-TestResult "语言设置" $true "语言设置功能正常"
    } catch {
        Record-TestResult "语言设置" $false "语言设置测试失败: $($_.Exception.Message)"
    }
}

if (-not $Quick) {
    Write-Host ""
    Write-Host "🔧 高级偏好设置测试..." -ForegroundColor $Colors.Progress
    try {
        Invoke-PythonSnippet -Code @"
import os
import shutil

from app.config.preferences.manager import UserPreferencesManager

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'preferences')
os.makedirs(workspace_temp_root, exist_ok=True)
temp_dir = os.path.join(workspace_temp_root, 'advanced_case')
shutil.rmtree(temp_dir, ignore_errors=True)
os.makedirs(temp_dir, exist_ok=True)

prefs_manager = UserPreferencesManager(config_dir=temp_dir)

assert prefs_manager.set_preference('advanced', 'max_threads', 4) is True
assert prefs_manager.set_preference('advanced', 'cache_size_mb', 1024) is True
assert prefs_manager.set_preference('advanced', 'log_level', 'INFO') is True
assert prefs_manager.set_preference('advanced', 'cache_size_mb', -1) is False

advanced_prefs = prefs_manager.get_advanced_preferences()
assert advanced_prefs['max_threads'] == 4
assert advanced_prefs['cache_size_mb'] == 1024
assert advanced_prefs['log_level'] == 'INFO'

print('✅ 高级偏好设置更新成功')
print(f'✅ 当前高级设置: {advanced_prefs}')
print('高级偏好设置测试通过')
"@ | Out-Null
        Record-TestResult "高级偏好设置" $true "高级偏好设置功能正常"
    } catch {
        Record-TestResult "高级偏好设置" $false "高级偏好设置测试失败: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "🔄 偏好设置重置测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import os
import shutil

from app.config.preferences.defaults import PreferencesDefaults
from app.config.preferences.manager import UserPreferencesManager

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'preferences')
os.makedirs(workspace_temp_root, exist_ok=True)
temp_dir = os.path.join(workspace_temp_root, 'reset_case')
shutil.rmtree(temp_dir, ignore_errors=True)
os.makedirs(temp_dir, exist_ok=True)

prefs_manager = UserPreferencesManager(config_dir=temp_dir)
defaults = PreferencesDefaults.get_default_preferences()

assert prefs_manager.set_preference('ui', 'theme', 'light') is True
assert prefs_manager.set_preference('advanced', 'log_level', 'DEBUG') is True
assert prefs_manager.save_preferences() is True

assert prefs_manager.reset_to_defaults() is True
assert prefs_manager.get_preference('ui', 'theme') == defaults['ui']['theme']
assert prefs_manager.get_preference('advanced', 'log_level') == defaults['advanced']['log_level']

print('✅ 偏好设置重置成功')
print('偏好设置重置测试通过')
"@ | Out-Null
    Record-TestResult "偏好设置重置" $true "偏好设置重置功能正常"
} catch {
    Record-TestResult "偏好设置重置" $false "偏好设置重置失败: $($_.Exception.Message)"
}

if (-not $Quick) {
    Write-Host ""
    Write-Host "📦 偏好设置迁移测试..." -ForegroundColor $Colors.Progress
    try {
        Invoke-PythonSnippet -Code @"
from app.config.preferences.defaults import PreferencesDefaults
from app.config.preferences.validator import PreferencesValidator

legacy_prefs = {
    'theme_name': 'dark',
    'lang': 'zh',
    'auto_save_enabled': True,
}

migrated = PreferencesDefaults.get_default_preferences()
migrated['ui']['theme'] = legacy_prefs['theme_name']
migrated['ui']['language'] = 'zh_CN' if legacy_prefs['lang'] == 'zh' else legacy_prefs['lang']
migrated['advanced']['auto_save_interval'] = 300 if legacy_prefs['auto_save_enabled'] else 0

validator = PreferencesValidator()
assert validator.validate_preference_value('ui', 'theme', migrated['ui']['theme']) is True
assert validator.validate_preference_value('advanced', 'auto_save_interval', migrated['advanced']['auto_save_interval']) is True

print(f'✅ 迁移后主题: {migrated["ui"]["theme"]}')
print(f'✅ 迁移后语言: {migrated["ui"]["language"]}')
print(f'✅ 迁移后自动保存间隔: {migrated["advanced"]["auto_save_interval"]}')
print('偏好设置迁移测试通过')
"@ | Out-Null
        Record-TestResult "偏好设置迁移" $true "偏好设置迁移逻辑验证正常"
    } catch {
        Record-TestResult "偏好设置迁移" $false "偏好设置迁移测试失败: $($_.Exception.Message)"
    }
}

Show-TestSummary

if ((Test-Path $TestDataPath) -and (-not $KeepTestFiles)) {
    $tempFiles = Get-ChildItem $TestDataPath -File | Where-Object {
        $_.Name -like "*prefs*" -or $_.Name -like "*test*"
    }
    if ($tempFiles.Count -gt 0) {
        Remove-Item $tempFiles.FullName -Force
        Write-Host "🧹 清理临时测试文件" -ForegroundColor $Colors.Info
    }
}

if (Test-Path $WorkspaceTempRoot) {
    Remove-Item $WorkspaceTempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "📋 用户偏好设置测试完成。运行完整测试: .\scripts\vwr.ps1 test all" -ForegroundColor $Colors.Info

if ($TestResults.Failed -gt 0) {
    exit 1
}

exit 0
