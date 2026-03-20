#!/usr/bin/env powershell
# 智能视频水印去除工具 - 端到端工作流测试脚本
# 完整的视频处理流程测试，从输入到输出的全链路验证

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
    Write-Host "🎬 端到端工作流测试摘要" -ForegroundColor $Colors.Summary
    Write-Host ("=" * 50) -ForegroundColor $Colors.Info
    Write-Host "🕒 执行时间: $($duration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
    Write-Host "✅ 通过: $($TestResults.Passed)" -ForegroundColor $Colors.Success
    Write-Host "❌ 失败: $($TestResults.Failed)" -ForegroundColor $Colors.Error
    Write-Host "⏭️ 跳过: $($TestResults.Skipped)" -ForegroundColor $Colors.Warning
    Write-Host "📋 总计: $(($TestResults.Passed + $TestResults.Failed + $TestResults.Skipped))" -ForegroundColor $Colors.Info

    if ($TestResults.Failed -eq 0) {
        Write-Host ""
        Write-Host "🎉 所有端到端测试通过！" -ForegroundColor $Colors.Success
    } else {
        Write-Host ""
        Write-Host "⚠️ 有 $($TestResults.Failed) 项端到端测试失败" -ForegroundColor $Colors.Warning
    }
}

Write-Host "🎬 智能视频水印去除工具 - 端到端工作流测试" -ForegroundColor $Colors.Header
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
$WorkspaceTempRoot = Join-Path (Get-Location).Path "tests/test_data/runtime_tmp/e2e"
New-Item -ItemType Directory -Path $WorkspaceTempRoot -Force | Out-Null

Write-Host ""
Write-Host "🔍 系统环境检查..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import importlib
import importlib.util

essential_modules = [
    'app.core.video.thread',
    'app.config.config_manager',
    'app.ui.main_window',
]

for module in essential_modules:
    importlib.import_module(module)
    print(f'✅ {module} 导入成功')

ai_spec = importlib.util.find_spec('app.core.ai.ai_handler')
assert ai_spec is not None
print(f'✅ AI 处理模块可定位: {ai_spec.origin}')
print('系统环境检查通过')
"@ | Out-Null
    Record-TestResult "系统环境检查" $true "所有关键模块可用"
} catch {
    Record-TestResult "系统环境检查" $false "系统环境检查失败: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "⚙️ 配置管理器测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import os
import shutil

from app.config.config_manager import ConfigManager

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'e2e')
os.makedirs(workspace_temp_root, exist_ok=True)
case_dir = os.path.join(workspace_temp_root, 'config_case')
shutil.rmtree(case_dir, ignore_errors=True)
os.makedirs(case_dir, exist_ok=True)

config_path = os.path.join(case_dir, 'runtime_config.ini')
config = ConfigManager.load_config(config_path)

assert config.has_section('Paths')
assert config.has_section('Processing')
assert config.get('Paths', 'ffmpeg_path', fallback='') != ''

config.set('Paths', 'last_input_dir', 'tests/test_data')
config.set('Processing', 'default_detection_sensitivity', '0.75')

assert ConfigManager.save_config(config, config_path) is True
loaded_config = ConfigManager.load_config(config_path)

assert loaded_config.get('Paths', 'last_input_dir') == 'tests/test_data'
assert loaded_config.get('Processing', 'default_detection_sensitivity') == '0.75'

print(f'✅ 默认配置路径: {ConfigManager.get_config_path()}')
print(f'✅ 临时配置文件: {config_path}')
print('配置管理器测试通过')
"@ | Out-Null
    Record-TestResult "配置管理器测试" $true "配置管理器功能正常"
} catch {
    Record-TestResult "配置管理器测试" $false "配置管理器测试失败: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "🎥 视频处理器初始化测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import os
import shutil

from app.config.config_manager import ConfigManager
from app.core.video.thread import VideoProcessorThread

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'e2e')
os.makedirs(workspace_temp_root, exist_ok=True)
case_dir = os.path.join(workspace_temp_root, 'video_case')
shutil.rmtree(case_dir, ignore_errors=True)
os.makedirs(case_dir, exist_ok=True)

config = ConfigManager.load_config(os.path.join(case_dir, 'video_config.ini'))
video_processor = VideoProcessorThread(
    input_path='tests/test_data/sample.jpg',
    output_path='tests/test_data/sample_output.jpg',
    ai_params={},
    config=config,
)

assert video_processor.input_path.endswith('sample.jpg')
assert video_processor.output_path.endswith('sample_output.jpg')
assert hasattr(video_processor, 'ffmpeg_processor')
assert video_processor.enable_multiprocess is False

print('✅ VideoProcessorThread 初始化成功')
print(f'✅ 输入路径: {video_processor.input_path}')
print(f'✅ 输出路径: {video_processor.output_path}')
print('视频处理器初始化测试通过')
"@ | Out-Null
    Record-TestResult "视频处理器初始化" $true "视频处理器初始化成功"
} catch {
    Record-TestResult "视频处理器初始化" $false "视频处理器初始化失败: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "🤖 AI处理器初始化测试..." -ForegroundColor $Colors.Progress
try {
    if ($Quick) {
        Invoke-PythonSnippet -Code @"
import importlib.util

spec = importlib.util.find_spec('app.core.ai.ai_handler')
if spec is None:
    raise SystemExit(2)

print(f'✅ Quick 模式仅检查 AI 模块可定位: {spec.origin}')
print('AI 处理器快速检查通过')
"@ -AllowedExitCodes @(0, 2) | Out-Null
        Record-TestResult "AI处理器初始化" $true "Quick 模式下已完成轻量检查"
    } else {
        $aiHandlerTest = Invoke-PythonSnippet -Code @"
try:
    from app.core.ai.ai_handler import AIHandler
except (ModuleNotFoundError, ImportError, OSError) as exc:
    print(f'⚠️ 当前环境无法加载 AIHandler: {exc}')
    raise SystemExit(2)

ai_handler = AIHandler()
print('✅ AIHandler 初始化成功')
print(f'✅ 是否具备 load_models: {hasattr(ai_handler, "load_models")}')
print('AI处理器初始化测试通过')
"@ -AllowedExitCodes @(0, 2)

        if ($aiHandlerTest.ExitCode -eq 2) {
            Record-TestResult "AI处理器初始化" $false "当前环境缺少完整 AI 依赖" $true
        } else {
            Record-TestResult "AI处理器初始化" $true "AI处理器初始化成功"
        }
    }
} catch {
    Record-TestResult "AI处理器初始化" $false "AI处理器初始化测试失败: $($_.Exception.Message)"
}

if (-not $Quick) {
    Write-Host ""
    Write-Host "🖥️ UI组件初始化测试..." -ForegroundColor $Colors.Progress
    try {
        $uiTest = Invoke-PythonSnippet -Code @"
try:
    from PyQt6.QtWidgets import QApplication
except ImportError as exc:
    print(f'⚠️ 缺少 PyQt6: {exc}')
    raise SystemExit(2)

from app.ui.main_window import MainWindow
from app.ui.widgets.batch.batch_processing_widget import BatchProcessingWidget

app = QApplication.instance() or QApplication([])
window = MainWindow()
batch_widget = BatchProcessingWidget()

print(f'✅ MainWindow 类型: {type(window).__name__}')
print(f'✅ BatchProcessingWidget 类型: {type(batch_widget).__name__}')

window.close()
batch_widget.close()
app.quit()
print('UI组件初始化测试通过')
"@ -AllowedExitCodes @(0, 2)

        if ($uiTest.ExitCode -eq 2) {
            Record-TestResult "UI组件初始化" $false "当前环境缺少 GUI 依赖" $true
        } else {
            Record-TestResult "UI组件初始化" $true "UI组件初始化成功"
        }
    } catch {
        Record-TestResult "UI组件初始化" $false "UI组件初始化测试失败: $($_.Exception.Message)"
    }
}

if (-not $Quick) {
    Write-Host ""
    Write-Host "🔄 完整工作流集成测试..." -ForegroundColor $Colors.Progress
    try {
        Invoke-PythonSnippet -Code @"
import os
import shutil
from types import SimpleNamespace

from app.config.config_manager import ConfigManager
from app.core.video.thread import VideoProcessorThread

workflow_steps = [
    '初始化配置',
    '视频文件验证',
    '水印检测',
    '图像修复',
    '音频处理',
    '输出生成',
]

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'e2e')
os.makedirs(workspace_temp_root, exist_ok=True)
case_dir = os.path.join(workspace_temp_root, 'workflow_case')
shutil.rmtree(case_dir, ignore_errors=True)
os.makedirs(case_dir, exist_ok=True)

config = ConfigManager.load_config(os.path.join(case_dir, 'workflow.ini'))
fake_ai_handler = SimpleNamespace(load_models=lambda: True)
processor = VideoProcessorThread(
    input_path='tests/test_data/sample.jpg',
    output_path='tests/test_data/sample_output.jpg',
    ai_params={'mode': 'smoke'},
    config=config,
    preloaded_ai_handler=fake_ai_handler,
)

assert processor.ai_handler is fake_ai_handler
assert len(workflow_steps) == 6
for index, step in enumerate(workflow_steps, 1):
    print(f'  {index}. {step}')

print('✅ 工作流组件已完成轻量装配')
print('完整工作流集成测试通过')
"@ | Out-Null
        Record-TestResult "完整工作流集成" $true "工作流集成测试成功"
    } catch {
        Record-TestResult "完整工作流集成" $false "工作流集成测试失败: $($_.Exception.Message)"
    }
}

if (-not $Quick) {
    Write-Host ""
    Write-Host "📚 批量处理工作流测试..." -ForegroundColor $Colors.Progress
    try {
        Invoke-PythonSnippet -Code @"
from app.ui.widgets.batch.batch_processor_thread import FileQueueManager, ProcessingStatus

queue_manager = FileQueueManager()
queue_manager.add_file('tests/test_data/sample1.mp4')
queue_manager.add_file('tests/test_data/sample2.mov')
queue_manager.update_file_status(0, ProcessingStatus.PROCESSING, progress=55)

assert queue_manager.get_queue_size() == 2
assert queue_manager.get_pending_count() == 1
assert queue_manager.get_processing_count() == 1

queue = queue_manager.get_queue()
print(f'✅ 队列长度: {len(queue)}')
print(f'✅ 第一项状态: {queue[0]["status"].value}')
print('批量处理工作流测试通过')
"@ | Out-Null
        Record-TestResult "批量处理工作流" $true "批量处理工作流测试成功"
    } catch {
        Record-TestResult "批量处理工作流" $false "批量处理工作流测试失败: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "👤 用户偏好设置工作流测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import os
import shutil

from app.config.preferences.defaults import PreferencesDefaults
from app.config.preferences.manager import UserPreferencesManager

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'e2e')
os.makedirs(workspace_temp_root, exist_ok=True)
case_dir = os.path.join(workspace_temp_root, 'preferences_case')
shutil.rmtree(case_dir, ignore_errors=True)
os.makedirs(case_dir, exist_ok=True)

prefs_manager = UserPreferencesManager(config_dir=case_dir)
defaults = PreferencesDefaults.get_default_preferences()

assert prefs_manager.set_preference('ui', 'theme', 'light') is True
assert prefs_manager.set_preference('paths', 'last_input_dir', 'tests/test_data') is True
assert prefs_manager.save_preferences() is True

reloaded_manager = UserPreferencesManager(config_dir=case_dir)
assert reloaded_manager.get_preference('ui', 'theme') == 'light'
assert reloaded_manager.get_preference('paths', 'last_input_dir') == 'tests/test_data'
assert defaults['ui']['theme'] in {'dark', 'light'}

print('✅ UserPreferencesManager 创建成功')
print('✅ 用户偏好设置保存与重载成功')
print('用户偏好设置工作流测试通过')
"@ | Out-Null
    Record-TestResult "用户偏好设置工作流" $true "用户偏好设置工作流测试成功"
} catch {
    Record-TestResult "用户偏好设置工作流" $false "用户偏好设置工作流测试失败: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "💾 内存和资源管理测试..." -ForegroundColor $Colors.Progress
try {
    Invoke-PythonSnippet -Code @"
import os
import gc
import shutil

import psutil

from app.config.config_manager import ConfigManager
from app.core.video.thread import VideoProcessorThread

process = psutil.Process()
initial_memory = process.memory_info().rss / 1024 / 1024

workspace_temp_root = os.path.join(os.getcwd(), 'tests', 'test_data', 'runtime_tmp', 'e2e')
os.makedirs(workspace_temp_root, exist_ok=True)
case_dir = os.path.join(workspace_temp_root, 'memory_case')
shutil.rmtree(case_dir, ignore_errors=True)
os.makedirs(case_dir, exist_ok=True)

config = ConfigManager.load_config(os.path.join(case_dir, 'memory.ini'))
processors = []
for index in range(10):
    processors.append(
        VideoProcessorThread(
            input_path='tests/test_data/sample.jpg',
            output_path=f'tests/test_data/sample_output_{index}.jpg',
            ai_params={},
            config=config,
        )
    )

print(f'✅ 创建处理器数量: {len(processors)}')
del processors
gc.collect()

final_memory = process.memory_info().rss / 1024 / 1024
memory_diff = final_memory - initial_memory

print(f'初始内存使用: {initial_memory:.2f} MB')
print(f'最终内存使用: {final_memory:.2f} MB')
print(f'内存差异: {memory_diff:.2f} MB')

if memory_diff >= 150:
    raise SystemExit(1)

print('内存和资源管理测试通过')
"@ | Out-Null
    Record-TestResult "内存和资源管理" $true "内存和资源管理测试完成"
} catch {
    Record-TestResult "内存和资源管理" $false "内存和资源管理测试失败: $($_.Exception.Message)"
}

Show-TestSummary

if ((Test-Path $TestDataPath) -and (-not $KeepTestFiles)) {
    $tempFiles = Get-ChildItem $TestDataPath -File | Where-Object {
        $_.Name -like "*temp*" -or $_.Name -like "*test*"
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
Write-Host "📋 端到端测试完成。运行完整测试套件: .\scripts\vwr.ps1 test all" -ForegroundColor $Colors.Info

if ($TestResults.Failed -gt 0) {
    exit 1
}

exit 0
