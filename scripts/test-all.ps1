#!/usr/bin/env powershell
# 智能视频水印去除工具 - 完整测试套件脚本
# 依次执行：环境检查、代码质量检查、单元测试、集成测试、端到端测试、性能测试、生成综合报告

param(
    [Parameter()]
    [switch]$Verbose,
    
    [Parameter()]
    [switch]$Quick,
    
    [Parameter()]
    [switch]$SkipPerformance,
    
    [Parameter()]
    [switch]$SkipCoverage,
    
    [Parameter()]
    [switch]$Parallel,
    
    [Parameter()]
    [switch]$GenerateReport,
    
    [Parameter()]
    [string]$ReportFormat = "html",
    
    [Parameter()]
    [switch]$OpenReport,
    
    [Parameter()]
    [switch]$FailFast
)

# 设置错误处理
$ErrorActionPreference = "Stop"

# 颜色配置
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

# 测试套件结果追踪
$TestSuite = @{
    StartTime = Get-Date
    EndTime = $null
    TotalTests = 0
    PassedTests = 0
    FailedTests = 0
    SkippedTests = 0
    TestResults = @{}
    Reports = @()
    Environment = @{}
    Summary = @{}
}

# 测试步骤定义
$TestSteps = @(
    @{
        Name = "环境检查"
        ScriptPath = $null
        Function = "Test-Environment"
        Required = $true
        Description = "检查Python环境、虚拟环境和依赖包"
    },
    @{
        Name = "代码质量检查"
        ScriptPath = $null
        Function = "Test-CodeQuality"
        Required = $true
        Description = "运行代码格式化、风格检查和类型检查"
    },
    @{
        Name = "单元测试"
        ScriptPath = $null
        Function = "Test-Units"
        Required = $true
        Description = "执行pytest单元测试套件"
    },
    @{
        Name = "音频处理测试"
        ScriptPath = "tests/test_audio_processing.ps1"
        Function = $null
        Required = $false
        Description = "测试音频提取、合并和FFmpeg集成"
    },
    @{
        Name = "用户偏好测试"
        ScriptPath = "tests/test_user_preferences.ps1"
        Function = $null
        Required = $false
        Description = "测试用户偏好设置的保存、加载和验证"
    },
    @{
        Name = "端到端测试"
        ScriptPath = "tests/test_end_to_end.ps1"
        Function = $null
        Required = $true
        Description = "完整工作流程验证测试"
    },
    @{
        Name = "代码覆盖率分析"
        ScriptPath = "scripts/test-coverage.ps1"
        Function = $null
        Required = $false
        Description = "分析代码覆盖率并生成报告"
    },
    @{
        Name = "性能基准测试"
        ScriptPath = "scripts/test-performance.ps1" 
        Function = $null
        Required = $false
        Description = "性能基准测试和资源使用监控"
    }
)

# 记录测试步骤结果
function Record-StepResult {
    param(
        [string]$StepName,
        [bool]$Passed,
        [string]$Details = "",
        [bool]$Skipped = $false,
        [double]$Duration = 0
    )
    
    $TestSuite.TestResults[$StepName] = @{
        Passed = $Passed
        Skipped = $Skipped
        Details = $Details
        Duration = $Duration
        Timestamp = Get-Date
    }
    
    if ($Skipped) {
        $TestSuite.SkippedTests++
        Write-Host "⏭️ $StepName - 跳过" -ForegroundColor $Colors.Warning
    } elseif ($Passed) {
        $TestSuite.PassedTests++
        Write-Host "✅ $StepName - 通过 ($([math]::Round($Duration, 2))s)" -ForegroundColor $Colors.Success
    } else {
        $TestSuite.FailedTests++
        Write-Host "❌ $StepName - 失败" -ForegroundColor $Colors.Error
        if ($Details -and $Verbose) {
            Write-Host "   详细信息: $Details" -ForegroundColor $Colors.Detail
        }
    }
    
    $TestSuite.TotalTests++
}

# 环境检查函数
function Test-Environment {
    $startTime = Get-Date
    
    try {
        # 检查虚拟环境
        if (-not (Test-Path ".venv")) {
            throw "虚拟环境不存在"
        }
        
        # 激活虚拟环境
        . .\.venv\Scripts\Activate.ps1
        
        # 检查Python版本
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python不可用: $pythonVersion"
        }
        
        # 检查关键包
        $packages = @("pytest", "PyQt6", "opencv-python", "numpy", "pillow")
        foreach ($package in $packages) {
            $result = python -c "import $($package.Replace('-', '_')); print('OK')" 2>&1
            if ($LASTEXITCODE -ne 0) {
                throw "包 $package 不可用: $result"
            }
        }
        
        $TestSuite.Environment.PythonVersion = $pythonVersion
        $TestSuite.Environment.VirtualEnv = $true
        
        $endTime = Get-Date
        Record-StepResult "环境检查" $true "Python环境和依赖包检查通过" $false ($endTime - $startTime).TotalSeconds
        
    } catch {
        $endTime = Get-Date
        Record-StepResult "环境检查" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
        if ($FailFast) { throw }
    }
}

# 代码质量检查函数
function Test-CodeQuality {
    $startTime = Get-Date
    
    try {
        $qualityArgs = @("quality")
        if ($Quick) { $qualityArgs += "-Quick" }
        if ($Verbose) { $qualityArgs += "-Verbose" }
        
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "scripts/test.ps1"
        ) + $qualityArgs -Wait -PassThru -NoNewWindow
        
        if ($process.ExitCode -eq 0) {
            $endTime = Get-Date
            Record-StepResult "代码质量检查" $true "代码格式和风格检查通过" $false ($endTime - $startTime).TotalSeconds
        } else {
            throw "代码质量检查失败，退出码: $($process.ExitCode)"
        }
        
    } catch {
        $endTime = Get-Date
        Record-StepResult "代码质量检查" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
        if ($FailFast) { throw }
    }
}

# 单元测试函数
function Test-Units {
    $startTime = Get-Date
    
    try {
        $unitArgs = @("unit")
        if ($Quick) { $unitArgs += "-Quick" }
        if ($Verbose) { $unitArgs += "-Verbose" }
        
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "scripts/test.ps1"
        ) + $unitArgs -Wait -PassThru -NoNewWindow
        
        if ($process.ExitCode -eq 0) {
            $endTime = Get-Date
            Record-StepResult "单元测试" $true "pytest单元测试通过" $false ($endTime - $startTime).TotalSeconds
        } else {
            throw "单元测试失败，退出码: $($process.ExitCode)"
        }
        
    } catch {
        $endTime = Get-Date
        Record-StepResult "单元测试" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
        if ($FailFast) { throw }
    }
}

# 执行脚本测试步骤
function Invoke-ScriptTest {
    param([hashtable]$Step)
    
    $startTime = Get-Date
    
    # 检查是否应该跳过
    $shouldSkip = $false
    if ($Step.Name -eq "性能基准测试" -and $SkipPerformance) { $shouldSkip = $true }
    if ($Step.Name -eq "代码覆盖率分析" -and $SkipCoverage) { $shouldSkip = $true }
    
    if ($shouldSkip) {
        Record-StepResult $Step.Name $true "用户选择跳过" $true 0
        return
    }
    
    # 检查脚本文件是否存在
    if (-not (Test-Path $Step.ScriptPath)) {
        Record-StepResult $Step.Name $false "脚本文件不存在: $($Step.ScriptPath)" $false 0
        if ($Step.Required -and $FailFast) { 
            throw "必需的测试脚本不存在: $($Step.ScriptPath)"
        }
        return
    }
    
    try {
        $scriptArgs = @()
        if ($Quick) { $scriptArgs += "-Quick" }
        if ($Verbose) { $scriptArgs += "-Verbose" }
        
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", $Step.ScriptPath
        ) + $scriptArgs -Wait -PassThru -NoNewWindow
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        if ($process.ExitCode -eq 0) {
            Record-StepResult $Step.Name $true "$($Step.Description)执行成功" $false $duration
        } else {
            $errorMsg = "$($Step.Description)执行失败，退出码: $($process.ExitCode)"
            Record-StepResult $Step.Name $false $errorMsg $false $duration
            
            if ($Step.Required -and $FailFast) {
                throw $errorMsg
            }
        }
        
    } catch {
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        Record-StepResult $Step.Name $false $_.Exception.Message $false $duration
        
        if ($Step.Required -and $FailFast) { 
            throw 
        }
    }
}

# 显示测试套件摘要
function Show-TestSuiteSummary {
    $TestSuite.EndTime = Get-Date
    $totalDuration = ($TestSuite.EndTime - $TestSuite.StartTime)
    
    Write-Host ""
    Write-Host "🧪 完整测试套件执行摘要" -ForegroundColor $Colors.Summary
    Write-Host "=" * 60 -ForegroundColor $Colors.Info
    Write-Host "🕒 总执行时间: $($totalDuration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
    Write-Host "📋 总测试数: $($TestSuite.TotalTests)" -ForegroundColor $Colors.Info
    Write-Host "✅ 通过: $($TestSuite.PassedTests)" -ForegroundColor $Colors.Success
    Write-Host "❌ 失败: $($TestSuite.FailedTests)" -ForegroundColor $Colors.Error  
    Write-Host "⏭️ 跳过: $($TestSuite.SkippedTests)" -ForegroundColor $Colors.Warning
    Write-Host "📊 成功率: $([math]::Round($TestSuite.PassedTests / $TestSuite.TotalTests * 100, 1))%" -ForegroundColor $Colors.Info
    
    Write-Host ""
    Write-Host "📋 测试步骤详情:" -ForegroundColor $Colors.Header
    foreach ($result in $TestSuite.TestResults.GetEnumerator()) {
        $status = if ($result.Value.Skipped) { "⏭️" } elseif ($result.Value.Passed) { "✅" } else { "❌" }
        $color = if ($result.Value.Skipped) { $Colors.Warning } elseif ($result.Value.Passed) { $Colors.Success } else { $Colors.Error }
        Write-Host "  $status $($result.Key): $([math]::Round($result.Value.Duration, 2))s" -ForegroundColor $color
    }
    
    # 显示失败的测试
    $failedTests = $TestSuite.TestResults.GetEnumerator() | Where-Object { -not $_.Value.Passed -and -not $_.Value.Skipped }
    if ($failedTests.Count -gt 0) {
        Write-Host ""
        Write-Host "❌ 失败的测试:" -ForegroundColor $Colors.Error
        foreach ($failed in $failedTests) {
            Write-Host "  • $($failed.Key): $($failed.Value.Details)" -ForegroundColor $Colors.Error
        }
    }
    
    # 总体结果
    if ($TestSuite.FailedTests -eq 0) {
        Write-Host ""
        Write-Host "🎉 所有测试通过！代码质量良好，可以安全部署。" -ForegroundColor $Colors.Success
    } else {
        Write-Host ""
        Write-Host "⚠️ 有 $($TestSuite.FailedTests) 项测试失败，请修复后重新测试。" -ForegroundColor $Colors.Warning
    }
}

# 生成测试报告
function Generate-TestReport {
    if (-not $GenerateReport) { return }
    
    Write-Host ""
    Write-Host "📄 生成测试报告..." -ForegroundColor $Colors.Progress
    
    try {
        # 确保日志目录存在
        if (-not (Test-Path "logs")) {
            New-Item -ItemType Directory -Path "logs" -Force | Out-Null
        }
        
        # 准备报告数据
        $reportData = @{
            TestSuite = "智能视频水印去除工具 - 完整测试套件"
            Timestamp = Get-Date
            Duration = ($TestSuite.EndTime - $TestSuite.StartTime).TotalSeconds
            Summary = @{
                TotalTests = $TestSuite.TotalTests
                PassedTests = $TestSuite.PassedTests
                FailedTests = $TestSuite.FailedTests
                SkippedTests = $TestSuite.SkippedTests
                SuccessRate = if ($TestSuite.TotalTests -gt 0) { $TestSuite.PassedTests / $TestSuite.TotalTests * 100 } else { 0 }
            }
            Environment = $TestSuite.Environment
            TestResults = $TestSuite.TestResults
            Parameters = @{
                Quick = $Quick
                SkipPerformance = $SkipPerformance
                SkipCoverage = $SkipCoverage
                FailFast = $FailFast
                Parallel = $Parallel
            }
        }
        
        # 生成JSON报告
        $jsonReport = $reportData | ConvertTo-Json -Depth 4
        $jsonPath = "logs/test_suite_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
        $jsonReport | Out-File -FilePath $jsonPath -Encoding UTF8
        $TestSuite.Reports += $jsonPath
        Write-Host "✅ JSON报告生成: $jsonPath" -ForegroundColor $Colors.Success
        
        # 生成HTML报告
        if ($ReportFormat -eq "html" -or $ReportFormat -eq "all") {
            $htmlContent = @"
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试套件报告 - 智能视频水印去除工具</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric { background: #ecf0f1; padding: 15px; border-radius: 5px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; margin-top: 5px; }
        .success { color: #27ae60; }
        .error { color: #e74c3c; }
        .warning { color: #f39c12; }
        .test-results { margin-top: 20px; }
        .test-item { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #ecf0f1; }
        .status-passed { color: #27ae60; }
        .status-failed { color: #e74c3c; }
        .status-skipped { color: #f39c12; }
        .duration { font-family: monospace; color: #7f8c8d; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 测试套件报告</h1>
        <p><strong>项目:</strong> 智能视频水印去除工具</p>
        <p><strong>执行时间:</strong> $($TestSuite.StartTime.ToString('yyyy-MM-dd HH:mm:ss'))</p>
        <p><strong>总执行时长:</strong> $($totalDuration.ToString('mm\:ss'))</p>
        
        <h2>📊 测试摘要</h2>
        <div class="summary">
            <div class="metric">
                <div class="metric-value">$($TestSuite.TotalTests)</div>
                <div class="metric-label">总测试数</div>
            </div>
            <div class="metric">
                <div class="metric-value success">$($TestSuite.PassedTests)</div>
                <div class="metric-label">通过</div>
            </div>
            <div class="metric">
                <div class="metric-value error">$($TestSuite.FailedTests)</div>
                <div class="metric-label">失败</div>
            </div>
            <div class="metric">
                <div class="metric-value warning">$($TestSuite.SkippedTests)</div>
                <div class="metric-label">跳过</div>
            </div>
            <div class="metric">
                <div class="metric-value">$([math]::Round($reportData.Summary.SuccessRate, 1))%</div>
                <div class="metric-label">成功率</div>
            </div>
        </div>
        
        <h2>📋 测试结果详情</h2>
        <div class="test-results">
"@
            
            foreach ($result in $TestSuite.TestResults.GetEnumerator()) {
                $statusClass = if ($result.Value.Skipped) { "status-skipped" } elseif ($result.Value.Passed) { "status-passed" } else { "status-failed" }
                $statusIcon = if ($result.Value.Skipped) { "⏭️" } elseif ($result.Value.Passed) { "✅" } else { "❌" }
                
                $htmlContent += @"
            <div class="test-item">
                <span class="$statusClass">$statusIcon $($result.Key)</span>
                <span class="duration">$([math]::Round($result.Value.Duration, 2))s</span>
            </div>
"@
            }
            
            $htmlContent += @"
        </div>
        
        <div class="footer">
            <p>报告生成时间: $(Get-Date)</p>
            <p>智能视频水印去除工具 - 自动化测试报告</p>
        </div>
    </div>
</body>
</html>
"@
            
            $htmlPath = "logs/test_suite_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').html"
            $htmlContent | Out-File -FilePath $htmlPath -Encoding UTF8
            $TestSuite.Reports += $htmlPath
            Write-Host "✅ HTML报告生成: $htmlPath" -ForegroundColor $Colors.Success
            
            if ($OpenReport) {
                try {
                    Start-Process $htmlPath
                    Write-Host "🌐 HTML报告已在浏览器中打开" -ForegroundColor $Colors.Success
                } catch {
                    Write-Host "❌ 无法打开HTML报告: $($_.Exception.Message)" -ForegroundColor $Colors.Error
                }
            }
        }
        
    } catch {
        Write-Host "❌ 测试报告生成失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    }
}

# 主执行逻辑
Write-Host "🧪 智能视频水印去除工具 - 完整测试套件" -ForegroundColor $Colors.Header
Write-Host "模式: $(if($Quick){'快速'}else{'完整'}) | 失败快速停止: $(if($FailFast){'开启'}else{'关闭'})" -ForegroundColor $Colors.Info
Write-Host "性能测试: $(if($SkipPerformance){'跳过'}else{'包含'}) | 覆盖率分析: $(if($SkipCoverage){'跳过'}else{'包含'})" -ForegroundColor $Colors.Info
Write-Host "=" * 60 -ForegroundColor $Colors.Info

try {
    # 设置环境变量
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONPATH = (Get-Location).Path
    
    # 确保日志目录存在
    if (-not (Test-Path "logs")) {
        New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    }
    
    # 执行所有测试步骤
    foreach ($step in $TestSteps) {
        Write-Host ""
        Write-Host "🔄 执行: $($step.Name)" -ForegroundColor $Colors.Progress
        Write-Host "📝 $($step.Description)" -ForegroundColor $Colors.Detail
        
        if ($step.Function) {
            # 执行内置函数
            & $step.Function
        } elseif ($step.ScriptPath) {
            # 执行外部脚本
            Invoke-ScriptTest $step
        }
        
        # 如果启用了快速失败且测试失败，停止执行
        if ($FailFast -and $TestSuite.TestResults[$step.Name] -and 
            -not $TestSuite.TestResults[$step.Name].Passed -and 
            -not $TestSuite.TestResults[$step.Name].Skipped -and
            $step.Required) {
            Write-Host "💥 快速失败模式：停止测试执行" -ForegroundColor $Colors.Error
            break
        }
    }
    
    # 显示测试摘要
    Show-TestSuiteSummary
    
    # 生成测试报告
    Generate-TestReport
    
} catch {
    Write-Host "❌ 测试套件执行过程中发生严重错误: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    $TestSuite.EndTime = Get-Date
    exit 1
} finally {
    Write-Host ""
    Write-Host "📝 测试套件执行完成。查看详细报告: logs/" -ForegroundColor $Colors.Info
    if ($TestSuite.Reports.Count -gt 0) {
        foreach ($report in $TestSuite.Reports) {
            Write-Host "📄 $report" -ForegroundColor $Colors.Detail
        }
    }
}

# 返回适当的退出码
if ($TestSuite.FailedTests -gt 0) {
    exit 1
} else {
    exit 0
}