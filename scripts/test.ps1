#!/usr/bin/env powershell
# 智能视频水印去除工具 - 增强测试执行脚本
# 支持参数化和模块化测试

param(
    [Parameter(Position=0)]
    [ValidateSet("unit", "integration", "quality", "audio", "e2e", "preferences", "all", "help")]
    [string]$Type = "all",

    [Parameter(Position=1)]
    [ValidateSet("mvp", "ai", "ui", "batch", "video", "audio", "preferences", "all")]
    [string]$Module = "all",

    [Parameter()]
    [switch]$Quick,

    [Parameter()]
    [switch]$Parallel,

    [Parameter()]
    [switch]$Report,

    [Parameter()]
    [switch]$Verbose,

    [Parameter()]
    [switch]$Coverage,

    [Parameter()]
    [switch]$Performance

# 设置错误处理
$ErrorActionPreference = "Stop"

# 颜色常量
$Colors = @{
    Header = "Green"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Progress = "Blue"
    Summary = "Magenta"
    Detail = "White"
}

# 显示帮助信息
function Show-Help {
    Write-Host "🧪 智能视频水印去除工具 - 测试脚本" -ForegroundColor $Colors.Header
    Write-Host "=" * 50 -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "用法:" -ForegroundColor $Colors.Header
    Write-Host "  .\scripts\test.ps1 [Type] [Module] [Options]" -ForegroundColor $Colors.Detail
    Write-Host ""
    Write-Host "测试类型 (Type):" -ForegroundColor $Colors.Header
    Write-Host "  unit        - 仅运行单元测试 (pytest)" -ForegroundColor $Colors.Detail
    Write-Host "  integration - 仅运行集成测试 (功能测试)" -ForegroundColor $Colors.Detail
    Write-Host "  quality     - 仅运行代码质量检查" -ForegroundColor $Colors.Detail
    Write-Host "  audio       - 仅运行音频处理测试" -ForegroundColor $Colors.Detail
    Write-Host "  e2e         - 端到端工作流测试" -ForegroundColor $Colors.Detail
    Write-Host "  preferences - 用户偏好设置测试" -ForegroundColor $Colors.Detail
    Write-Host "  all         - 运行所有测试 (默认)" -ForegroundColor $Colors.Detail
    Write-Host ""
    Write-Host "模块 (Module):" -ForegroundColor $Colors.Header
    Write-Host "  mvp         - MVP基础功能测试" -ForegroundColor $Colors.Detail
    Write-Host "  ai          - AI功能测试" -ForegroundColor $Colors.Detail
    Write-Host "  ui          - UI组件测试" -ForegroundColor $Colors.Detail
    Write-Host "  batch       - 批处理功能测试" -ForegroundColor $Colors.Detail
    Write-Host "  video       - 视频处理测试" -ForegroundColor $Colors.Detail
    Write-Host "  audio       - 音频处理测试" -ForegroundColor $Colors.Detail
    Write-Host "  preferences - 用户偏好设置测试" -ForegroundColor $Colors.Detail
    Write-Host "  all         - 所有模块 (默认)" -ForegroundColor $Colors.Detail
    Write-Host ""
    Write-Host "选项 (Options):" -ForegroundColor $Colors.Header
    Write-Host "  -Quick      - 快速模式 (跳过耗时检查)" -ForegroundColor $Colors.Detail
    Write-Host "  -Parallel   - 并行执行 (实验性)" -ForegroundColor $Colors.Detail
    Write-Host "  -Report     - 生成详细测试报告" -ForegroundColor $Colors.Detail
    Write-Host "  -Verbose    - 详细输出模式" -ForegroundColor $Colors.Detail
    Write-Host "  -Coverage   - 生成代码覆盖率报告" -ForegroundColor $Colors.Detail
    Write-Host "  -Performance- 运行性能基准测试" -ForegroundColor $Colors.Detail
    Write-Host ""
    Write-Host "示例:" -ForegroundColor $Colors.Header
    Write-Host "  .\scripts\test.ps1                      # 运行所有测试" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\test.ps1 unit                 # 仅运行单元测试" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\test.ps1 integration ai       # 仅运行AI集成测试" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\test.ps1 audio                # 仅运行音频处理测试" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\test.ps1 e2e -Verbose         # 端到端测试详细输出" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\test.ps1 preferences          # 用户偏好设置测试" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\test.ps1 quality -Quick       # 快速代码质量检查" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\test.ps1 all all -Coverage    # 全面测试并生成覆盖率报告" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\test.ps1 all all -Performance # 包含性能基准测试" -ForegroundColor $Colors.Detail
    Write-Host ""
}

# 如果请求帮助，显示帮助后退出
if ($Type -eq "help") {
    Show-Help
    exit 0
}

# 测试结果追踪
$TestResults = @{
    QualityChecks = @{}
    UnitTests = @{}
    IntegrationTests = @{}
    AudioTests = @{}
    E2ETests = @{}
    PreferencesTests = @{}
    PerformanceTests = @{}
    CoverageResults = @{}
    TotalPassed = 0
    TotalFailed = 0
    StartTime = Get-Date
}

# 记录测试结果
function Record-TestResult {
    param(
        [string]$Category,
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = ""
    )

    if (-not $TestResults[$Category]) {
        $TestResults[$Category] = @{}
    }

    $TestResults[$Category][$TestName] = @{
        Passed = $Passed
        Details = $Details
        Timestamp = Get-Date
    }

    if ($Passed) {
        $TestResults.TotalPassed++
    } else {
        $TestResults.TotalFailed++
    }
}

# 显示测试摘要
function Show-TestSummary {
    $endTime = Get-Date
    $duration = $endTime - $TestResults.StartTime

    Write-Host ""
    Write-Host "📊 测试执行摘要" -ForegroundColor $Colors.Summary
    Write-Host "=" * 50 -ForegroundColor $Colors.Info
    Write-Host "🕒 执行时间: $($duration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
    Write-Host "✅ 通过: $($TestResults.TotalPassed)" -ForegroundColor $Colors.Success
    Write-Host "❌ 失败: $($TestResults.TotalFailed)" -ForegroundColor $Colors.Error
    Write-Host "📋 总计: $($TestResults.TotalPassed + $TestResults.TotalFailed)" -ForegroundColor $Colors.Info

    if ($TestResults.TotalFailed -eq 0) {
        Write-Host ""
        Write-Host "🎉 所有测试通过！" -ForegroundColor $Colors.Success
    } else {
        Write-Host ""
        Write-Host "⚠️ 有 $($TestResults.TotalFailed) 项测试失败" -ForegroundColor $Colors.Warning
    }
}

# 保存测试报告
function Save-TestReport {
    if ($Report) {
        $reportPath = "logs/test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
        $TestResults | ConvertTo-Json -Depth 3 | Out-File -FilePath $reportPath -Encoding UTF8
        Write-Host "📄 测试报告已保存: $reportPath" -ForegroundColor $Colors.Info
    }
}

Write-Host "🧪 智能视频水印去除工具 - 测试执行器" -ForegroundColor $Colors.Header
Write-Host "测试类型: $Type | 模块: $Module | 模式: $(if($Quick){'快速'}else{'完整'})" -ForegroundColor $Colors.Info
Write-Host "=" * 60 -ForegroundColor $Colors.Info

# 检查 .venv 是否存在
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 虚拟环境不存在，请先运行: .\scripts\setup.ps1" -ForegroundColor $Colors.Error
    exit 1
}

# 激活虚拟环境
Write-Host "🔄 激活虚拟环境..." -ForegroundColor $Colors.Progress
. .\.venv\Scripts\Activate.ps1
Write-Host "✅ 虚拟环境已激活" -ForegroundColor $Colors.Success

# 设置UTF-8编码环境变量
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = (Get-Location).Path

# 确保日志目录存在
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    Write-Host "📁 创建日志目录" -ForegroundColor $Colors.Info
}

#region 代码质量检查函数
function Run-QualityChecks {
    param([string]$SelectedModule = "all")

    if ($Type -ne "quality" -and $Type -ne "all") { return }

    Write-Host ""
    Write-Host "🔍 代码质量检查..." -ForegroundColor $Colors.Progress

    $targetPaths = @()
    if (Test-Path "app") { $targetPaths += "app" }
    if (Test-Path "main.py") { $targetPaths += "main.py" }

    if ($targetPaths.Count -eq 0) {
        Write-Host "⚠️ 未找到代码文件，跳过质量检查" -ForegroundColor $Colors.Warning
        return
    }

    # 代码格式检查
    Write-Host "📝 检查代码格式 (black)..." -ForegroundColor $Colors.Info
    try {
        $blackArgs = @("--check") + $targetPaths + @("--diff")
        if ($Quick) { $blackArgs += "--fast" }

        black @blackArgs
        Write-Host "✅ 代码格式检查通过" -ForegroundColor $Colors.Success
        Record-TestResult "QualityChecks" "CodeFormat" $true "Black formatting check passed"
    } catch {
        Write-Host "❌ 代码格式检查失败" -ForegroundColor $Colors.Error
        Write-Host "建议运行: black $($targetPaths -join ' ')" -ForegroundColor $Colors.Warning
        Record-TestResult "QualityChecks" "CodeFormat" $false "Black formatting issues found"
    }

    # 代码风格检查
    Write-Host "📋 检查代码风格 (flake8)..." -ForegroundColor $Colors.Info
    try {
        $flakeArgs = $targetPaths + @("--max-line-length=100", "--exclude=.venv")
        if ($Quick) { $flakeArgs += "--select=E9,F63,F7,F82" }

        flake8 @flakeArgs
        Write-Host "✅ 代码风格检查通过" -ForegroundColor $Colors.Success
        Record-TestResult "QualityChecks" "CodeStyle" $true "Flake8 style check passed"
    } catch {
        Write-Host "❌ 代码风格检查失败" -ForegroundColor $Colors.Error
        Write-Host "请修复 flake8 报告的问题" -ForegroundColor $Colors.Warning
        Record-TestResult "QualityChecks" "CodeStyle" $false "Flake8 style issues found"
    }

    # 类型检查
    if (-not $Quick) {
        Write-Host "🔍 检查类型注解 (mypy)..." -ForegroundColor $Colors.Info
        try {
            $mypyArgs = $targetPaths + @("--ignore-missing-imports")
            mypy @mypyArgs
            Write-Host "✅ 类型检查通过" -ForegroundColor $Colors.Success
            Record-TestResult "QualityChecks" "TypeCheck" $true "Mypy type check passed"
        } catch {
            Write-Host "❌ 类型检查失败" -ForegroundColor $Colors.Error
            Write-Host "请修复类型注解问题" -ForegroundColor $Colors.Warning
            Record-TestResult "QualityChecks" "TypeCheck" $false "Mypy type issues found"
        }
    }
}
#endregion

#region 单元测试函数
function Run-UnitTests {
    param([string]$SelectedModule = "all")

    if ($Type -ne "unit" -and $Type -ne "all") { return }

    Write-Host ""
    Write-Host "🧪 单元测试..." -ForegroundColor $Colors.Progress

    if (-not (Test-Path "tests")) {
        Write-Host "⚠️ tests 目录不存在，跳过单元测试" -ForegroundColor $Colors.Warning
        return
    }

    try {
        $pytestArgs = @("tests", "-v", "--tb=short")

        # 根据模块过滤测试
        if ($SelectedModule -ne "all") {
            $testPattern = switch ($SelectedModule) {
                "mvp" { "test_mvp" }
                "ai" { "test_*ai*" }
                "ui" { "test_*ui*" }
                "batch" { "test_*batch*" }
                "video" { "test_*video*" }
                default { "*" }
            }
            $pytestArgs += "-k", $testPattern
        }

        if ($Quick) { $pytestArgs += "-x" } # Stop on first failure
        if ($Verbose) { $pytestArgs += "-s" } # Don't capture output

        pytest @pytestArgs
        Write-Host "✅ 单元测试通过" -ForegroundColor $Colors.Success
        Record-TestResult "UnitTests" "Pytest" $true "Pytest unit tests passed"
    } catch {
        Write-Host "❌ 单元测试失败" -ForegroundColor $Colors.Error
        Record-TestResult "UnitTests" "Pytest" $false "Pytest unit tests failed"
    }
}
#endregion

#region 集成测试函数
function Run-IntegrationTests {
    param([string]$SelectedModule = "all")

    if ($Type -ne "integration" -and $Type -ne "all") { return }

    Write-Host ""
    Write-Host "🎯 集成测试..." -ForegroundColor $Colors.Progress

    $integrationTests = @()

    # 根据选择的模块确定要运行的测试
    if ($SelectedModule -eq "all" -or $SelectedModule -eq "mvp") {
        if (Test-Path "tests/test_mvp.py") {
            $integrationTests += @{Name="MVP功能测试"; Path="tests/test_mvp.py"; Category="MVP"}
        }
    }

    if ($SelectedModule -eq "all" -or $SelectedModule -eq "ai") {
        if (Test-Path "tests/test_phase2.py") {
            $integrationTests += @{Name="AI功能测试"; Path="tests/test_phase2.py"; Category="AI"}
        }
    }

    if ($SelectedModule -eq "all" -or $SelectedModule -eq "ui") {
        if (Test-Path "tests/test_phase3.py") {
            $integrationTests += @{Name="UI功能测试"; Path="tests/test_phase3.py"; Category="UI"}
        }
    }

    if ($SelectedModule -eq "all" -or $SelectedModule -eq "batch") {
        if (Test-Path "tests/test_batch_processing.py") {
            $integrationTests += @{Name="批处理测试"; Path="tests/test_batch_processing.py"; Category="Batch"}
        }
    }

    if ($SelectedModule -eq "all" -or $SelectedModule -eq "video") {
        if (Test-Path "tests/test_video_processor.py") {
            $integrationTests += @{Name="视频处理测试"; Path="tests/test_video_processor.py"; Category="Video"}
        }
    }

    if ($integrationTests.Count -eq 0) {
        Write-Host "⚠️ 未找到匹配的集成测试文件" -ForegroundColor $Colors.Warning
        return
    }

    foreach ($test in $integrationTests) {
        Write-Host "🧪 运行 $($test.Name)..." -ForegroundColor $Colors.Detail
        try {
            $result = python $test.Path
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ $($test.Name) 完成" -ForegroundColor $Colors.Success
                Record-TestResult "IntegrationTests" $test.Category $true "$($test.Name) passed"
            } else {
                Write-Host "❌ $($test.Name) 失败，退出码: $LASTEXITCODE" -ForegroundColor $Colors.Error
                if ($Verbose) { Write-Host "详细信息: $result" -ForegroundColor $Colors.Warning }
                Record-TestResult "IntegrationTests" $test.Category $false "$($test.Name) failed with exit code $LASTEXITCODE"
            }
        } catch {
            Write-Host "❌ $($test.Name) 执行异常: $($_.Exception.Message)" -ForegroundColor $Colors.Error
            Record-TestResult "IntegrationTests" $test.Category $false "$($test.Name) execution error: $($_.Exception.Message)"
        }

        if ($Quick -and $LASTEXITCODE -ne 0) {
            Write-Host "⚠️ 快速模式：遇到失败后停止" -ForegroundColor $Colors.Warning
            break
        }
    }
}
#endregion

#region 音频处理测试函数
function Run-AudioTests {
    param([string]$SelectedModule = "all")

    if ($Type -ne "audio" -and $Type -ne "all") { return }

    Write-Host ""
    Write-Host "🎵 音频处理测试..." -ForegroundColor $Colors.Progress

    if (-not (Test-Path "tests/test_audio_processing.ps1")) {
        Write-Host "⚠️ 音频处理测试脚本不存在" -ForegroundColor $Colors.Warning
        Record-TestResult "AudioTests" "AudioProcessing" $false "音频处理测试脚本不存在"
        return
    }

    try {
        $audioArgs = @()
        if ($Quick) { $audioArgs += "-Quick" }
        if ($Verbose) { $audioArgs += "-Verbose" }

        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "tests/test_audio_processing.ps1"
        ) + $audioArgs -Wait -PassThru -NoNewWindow

        if ($process.ExitCode -eq 0) {
            Write-Host "✅ 音频处理测试通过" -ForegroundColor $Colors.Success
            Record-TestResult "AudioTests" "AudioProcessing" $true "音频处理测试通过"
        } else {
            Write-Host "❌ 音频处理测试失败，退出码: $($process.ExitCode)" -ForegroundColor $Colors.Error
            Record-TestResult "AudioTests" "AudioProcessing" $false "音频处理测试失败，退出码: $($process.ExitCode)"
        }
    } catch {
        Write-Host "❌ 音频处理测试执行异常: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        Record-TestResult "AudioTests" "AudioProcessing" $false "音频处理测试执行异常: $($_.Exception.Message)"
    }
}
#endregion

#region 端到端测试函数
function Run-E2ETests {
    param([string]$SelectedModule = "all")

    if ($Type -ne "e2e" -and $Type -ne "all") { return }

    Write-Host ""
    Write-Host "🎬 端到端工作流测试..." -ForegroundColor $Colors.Progress

    if (-not (Test-Path "tests/test_end_to_end.ps1")) {
        Write-Host "⚠️ 端到端测试脚本不存在" -ForegroundColor $Colors.Warning
        Record-TestResult "E2ETests" "EndToEnd" $false "端到端测试脚本不存在"
        return
    }

    try {
        $e2eArgs = @()
        if ($Quick) { $e2eArgs += "-Quick" }
        if ($Verbose) { $e2eArgs += "-Verbose" }

        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "tests/test_end_to_end.ps1"
        ) + $e2eArgs -Wait -PassThru -NoNewWindow

        if ($process.ExitCode -eq 0) {
            Write-Host "✅ 端到端测试通过" -ForegroundColor $Colors.Success
            Record-TestResult "E2ETests" "EndToEnd" $true "端到端测试通过"
        } else {
            Write-Host "❌ 端到端测试失败，退出码: $($process.ExitCode)" -ForegroundColor $Colors.Error
            Record-TestResult "E2ETests" "EndToEnd" $false "端到端测试失败，退出码: $($process.ExitCode)"
        }
    } catch {
        Write-Host "❌ 端到端测试执行异常: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        Record-TestResult "E2ETests" "EndToEnd" $false "端到端测试执行异常: $($_.Exception.Message)"
    }
}
#endregion

#region 用户偏好设置测试函数
function Run-PreferencesTests {
    param([string]$SelectedModule = "all")

    if ($Type -ne "preferences" -and $Type -ne "all") { return }

    Write-Host ""
    Write-Host "👤 用户偏好设置测试..." -ForegroundColor $Colors.Progress

    if (-not (Test-Path "tests/test_user_preferences.ps1")) {
        Write-Host "⚠️ 用户偏好设置测试脚本不存在" -ForegroundColor $Colors.Warning
        Record-TestResult "PreferencesTests" "UserPreferences" $false "用户偏好设置测试脚本不存在"
        return
    }

    try {
        $prefsArgs = @()
        if ($Quick) { $prefsArgs += "-Quick" }
        if ($Verbose) { $prefsArgs += "-Verbose" }

        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "tests/test_user_preferences.ps1"
        ) + $prefsArgs -Wait -PassThru -NoNewWindow

        if ($process.ExitCode -eq 0) {
            Write-Host "✅ 用户偏好设置测试通过" -ForegroundColor $Colors.Success
            Record-TestResult "PreferencesTests" "UserPreferences" $true "用户偏好设置测试通过"
        } else {
            Write-Host "❌ 用户偏好设置测试失败，退出码: $($process.ExitCode)" -ForegroundColor $Colors.Error
            Record-TestResult "PreferencesTests" "UserPreferences" $false "用户偏好设置测试失败，退出码: $($process.ExitCode)"
        }
    } catch {
        Write-Host "❌ 用户偏好设置测试执行异常: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        Record-TestResult "PreferencesTests" "UserPreferences" $false "用户偏好设置测试执行异常: $($_.Exception.Message)"
    }
}
#endregion

#region 代码覆盖率测试函数
function Run-CoverageTests {
    if (-not $Coverage) { return }

    Write-Host ""
    Write-Host "📊 代码覆盖率分析..." -ForegroundColor $Colors.Progress

    if (-not (Test-Path "scripts/test-coverage.ps1")) {
        Write-Host "⚠️ 代码覆盖率脚本不存在，跳过覆盖率分析" -ForegroundColor $Colors.Warning
        Record-TestResult "CoverageResults" "Coverage" $false "代码覆盖率脚本不存在"
        return
    }

    try {
        $coverageArgs = @()
        if ($Quick) { $coverageArgs += "-Quick" }
        if ($Verbose) { $coverageArgs += "-Verbose" }

        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "scripts/test-coverage.ps1"
        ) + $coverageArgs -Wait -PassThru -NoNewWindow

        if ($process.ExitCode -eq 0) {
            Write-Host "✅ 代码覆盖率分析完成" -ForegroundColor $Colors.Success
            Record-TestResult "CoverageResults" "Coverage" $true "代码覆盖率分析完成"
        } else {
            Write-Host "❌ 代码覆盖率分析失败，退出码: $($process.ExitCode)" -ForegroundColor $Colors.Error
            Record-TestResult "CoverageResults" "Coverage" $false "代码覆盖率分析失败，退出码: $($process.ExitCode)"
        }
    } catch {
        Write-Host "❌ 代码覆盖率分析执行异常: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        Record-TestResult "CoverageResults" "Coverage" $false "代码覆盖率分析执行异常: $($_.Exception.Message)"
    }
}
#endregion

#region 性能基准测试函数
function Run-PerformanceTests {
    if (-not $Performance) { return }

    Write-Host ""
    Write-Host "🚀 性能基准测试..." -ForegroundColor $Colors.Progress

    if (-not (Test-Path "scripts/test-performance.ps1")) {
        Write-Host "⚠️ 性能测试脚本不存在，跳过性能测试" -ForegroundColor $Colors.Warning
        Record-TestResult "PerformanceTests" "Performance" $false "性能测试脚本不存在"
        return
    }

    try {
        $perfArgs = @()
        if ($Quick) { $perfArgs += "-Quick" }
        if ($Verbose) { $perfArgs += "-Verbose" }

        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "scripts/test-performance.ps1"
        ) + $perfArgs -Wait -PassThru -NoNewWindow

        if ($process.ExitCode -eq 0) {
            Write-Host "✅ 性能基准测试完成" -ForegroundColor $Colors.Success
            Record-TestResult "PerformanceTests" "Performance" $true "性能基准测试完成"
        } else {
            Write-Host "❌ 性能基准测试失败，退出码: $($process.ExitCode)" -ForegroundColor $Colors.Error
            Record-TestResult "PerformanceTests" "Performance" $false "性能基准测试失败，退出码: $($process.ExitCode)"
        }
    } catch {
        Write-Host "❌ 性能基准测试执行异常: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        Record-TestResult "PerformanceTests" "Performance" $false "性能基准测试执行异常: $($_.Exception.Message)"
    }
}
#endregion

# 主执行逻辑
try {
    # 根据参数执行相应的测试
    Run-QualityChecks -SelectedModule $Module
    Run-UnitTests -SelectedModule $Module
    Run-IntegrationTests -SelectedModule $Module
    Run-AudioTests -SelectedModule $Module
    Run-E2ETests -SelectedModule $Module
    Run-PreferencesTests -SelectedModule $Module

    # 运行可选的额外测试
    Run-CoverageTests
    Run-PerformanceTests

    # 显示测试摘要
    Show-TestSummary

    # 保存测试报告
    Save-TestReport

} catch {
    Write-Host "❌ 测试执行过程中发生严重错误: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    exit 1
} finally {
    Write-Host ""
    Write-Host "📝 使用 '.\scripts\test.ps1 help' 查看详细使用说明" -ForegroundColor $Colors.Info
}
