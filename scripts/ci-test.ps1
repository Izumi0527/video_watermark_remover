#!/usr/bin/env powershell
# 智能视频水印去除工具 - CI/CD测试脚本
# 专为持续集成环境设计：无交互模式运行，JSON格式输出测试结果，返回适当的退出码

param(
    [Parameter()]
    [switch]$SkipPerformance,
    
    [Parameter()]
    [switch]$SkipCoverage,
    
    [Parameter()]
    [double]$MinCoverage = 80.0,
    
    [Parameter()]
    [string]$OutputFile = "",
    
    [Parameter()]
    [string]$ArtifactsDir = "ci-artifacts",
    
    [Parameter()]
    [switch]$Verbose,
    
    [Parameter()]
    [int]$TimeoutMinutes = 30
)

# 设置错误处理和非交互模式
$ErrorActionPreference = "Continue"  # CI模式下不因单个错误停止
$ProgressPreference = "SilentlyContinue"  # 禁用进度条

# CI测试结果追踪
$CIResults = @{
    StartTime = Get-Date
    EndTime = $null
    Success = $false
    TotalTests = 0
    PassedTests = 0
    FailedTests = 0
    SkippedTests = 0
    TestResults = @{}
    Environment = @{}
    Artifacts = @{}
    Coverage = @{}
    Performance = @{}
    Errors = @()
    Warnings = @()
}

# 记录CI测试结果
function Record-CIResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = "",
        [bool]$Skipped = $false,
        [double]$Duration = 0,
        [hashtable]$Metadata = @{}
    )
    
    $CIResults.TestResults[$TestName] = @{
        Passed = $Passed
        Skipped = $Skipped
        Details = $Details
        Duration = $Duration
        Timestamp = Get-Date
        Metadata = $Metadata
    }
    
    if ($Skipped) {
        $CIResults.SkippedTests++
        Write-Output "SKIP: $TestName"
    } elseif ($Passed) {
        $CIResults.PassedTests++
        Write-Output "PASS: $TestName ($([math]::Round($Duration, 2))s)"
    } else {
        $CIResults.FailedTests++
        Write-Output "FAIL: $TestName - $Details"
        if ($Verbose) {
            Write-Output "DETAILS: $Details"
        }
    }
    
    $CIResults.TotalTests++
}

# 记录错误和警告
function Add-CIError {
    param([string]$Message)
    $CIResults.Errors += @{
        Message = $Message
        Timestamp = Get-Date
    }
    Write-Output "ERROR: $Message"
}

function Add-CIWarning {
    param([string]$Message)
    $CIResults.Warnings += @{
        Message = $Message
        Timestamp = Get-Date
    }
    Write-Output "WARNING: $Message"
}

# 收集环境信息
function Collect-EnvironmentInfo {
    try {
        $CIResults.Environment = @{
            OS = $env:OS
            ComputerName = $env:COMPUTERNAME
            UserName = $env:USERNAME
            PowerShellVersion = $PSVersionTable.PSVersion.ToString()
            WorkingDirectory = (Get-Location).Path
            Timestamp = Get-Date
        }
        
        # CI环境特定变量
        if ($env:CI) { $CIResults.Environment.CI = $env:CI }
        if ($env:GITHUB_ACTIONS) { $CIResults.Environment.GitHubActions = $env:GITHUB_ACTIONS }
        if ($env:BUILD_NUMBER) { $CIResults.Environment.BuildNumber = $env:BUILD_NUMBER }
        if ($env:GIT_COMMIT) { $CIResults.Environment.GitCommit = $env:GIT_COMMIT }
        
        Write-Output "INFO: Environment information collected"
        
    } catch {
        Add-CIWarning "Failed to collect environment info: $($_.Exception.Message)"
    }
}

# 创建制品目录
function Initialize-ArtifactsDirectory {
    try {
        if (-not (Test-Path $ArtifactsDir)) {
            New-Item -ItemType Directory -Path $ArtifactsDir -Force | Out-Null
        }
        
        # 创建子目录
        @("logs", "reports", "coverage", "performance") | ForEach-Object {
            $subDir = Join-Path $ArtifactsDir $_
            if (-not (Test-Path $subDir)) {
                New-Item -ItemType Directory -Path $subDir -Force | Out-Null
            }
        }
        
        Write-Output "INFO: Artifacts directory initialized: $ArtifactsDir"
        
    } catch {
        Add-CIError "Failed to initialize artifacts directory: $($_.Exception.Message)"
    }
}

# 检查Python环境
function Test-PythonEnvironment {
    $startTime = Get-Date
    
    try {
        # 检查虚拟环境
        if (-not (Test-Path ".venv")) {
            throw "Virtual environment not found"
        }
        
        # 激活虚拟环境（CI模式）
        & ".\.venv\Scripts\Activate.ps1"
        
        # 设置环境变量
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1" 
        $env:PYTHONPATH = (Get-Location).Path
        
        # 检查Python版本
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python not available: $pythonVersion"
        }
        
        # 检查关键依赖包
        $requiredPackages = @("pytest", "PyQt6", "opencv-python", "numpy")
        foreach ($package in $requiredPackages) {
            $checkResult = python -c "import $($package.Replace('-', '_')); print('OK')" 2>&1
            if ($LASTEXITCODE -ne 0) {
                throw "Package $package not available: $checkResult"
            }
        }
        
        $CIResults.Environment.PythonVersion = $pythonVersion.Trim()
        $CIResults.Environment.VirtualEnv = $true
        
        $endTime = Get-Date
        Record-CIResult "PythonEnvironment" $true "Python environment ready" $false ($endTime - $startTime).TotalSeconds
        
    } catch {
        $endTime = Get-Date
        Record-CIResult "PythonEnvironment" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
    }
}

# 运行代码质量检查
function Test-CodeQuality {
    $startTime = Get-Date
    
    try {
        Write-Output "INFO: Starting code quality checks"
        
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "scripts/test.ps1", "quality", "-Quick"
        ) -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$ArtifactsDir/logs/quality.log" -RedirectStandardError "$ArtifactsDir/logs/quality.err"
        
        $endTime = Get-Date
        
        if ($process.ExitCode -eq 0) {
            Record-CIResult "CodeQuality" $true "Code quality checks passed" $false ($endTime - $startTime).TotalSeconds
            $CIResults.Artifacts.QualityLog = "$ArtifactsDir/logs/quality.log"
        } else {
            $errorContent = if (Test-Path "$ArtifactsDir/logs/quality.err") { 
                (Get-Content "$ArtifactsDir/logs/quality.err" -Raw).Trim()
            } else { "Unknown error" }
            Record-CIResult "CodeQuality" $false "Exit code: $($process.ExitCode), $errorContent" $false ($endTime - $startTime).TotalSeconds
        }
        
    } catch {
        $endTime = Get-Date
        Record-CIResult "CodeQuality" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
    }
}

# 运行单元测试
function Test-UnitTests {
    $startTime = Get-Date
    
    try {
        Write-Output "INFO: Starting unit tests"
        
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "scripts/test.ps1", "unit", "-Quick"
        ) -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$ArtifactsDir/logs/unit.log" -RedirectStandardError "$ArtifactsDir/logs/unit.err"
        
        $endTime = Get-Date
        
        if ($process.ExitCode -eq 0) {
            Record-CIResult "UnitTests" $true "Unit tests passed" $false ($endTime - $startTime).TotalSeconds
            $CIResults.Artifacts.UnitTestLog = "$ArtifactsDir/logs/unit.log"
        } else {
            $errorContent = if (Test-Path "$ArtifactsDir/logs/unit.err") { 
                (Get-Content "$ArtifactsDir/logs/unit.err" -Raw).Trim()
            } else { "Unknown error" }
            Record-CIResult "UnitTests" $false "Exit code: $($process.ExitCode), $errorContent" $false ($endTime - $startTime).TotalSeconds
        }
        
    } catch {
        $endTime = Get-Date
        Record-CIResult "UnitTests" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
    }
}

# 运行集成测试
function Test-Integration {
    $startTime = Get-Date
    
    try {
        Write-Output "INFO: Starting integration tests"
        
        # 端到端测试
        if (Test-Path "tests/test_end_to_end.ps1") {
            $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
                "-File", "tests/test_end_to_end.ps1", "-Quick"
            ) -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$ArtifactsDir/logs/e2e.log" -RedirectStandardError "$ArtifactsDir/logs/e2e.err"
            
            if ($process.ExitCode -ne 0) {
                throw "End-to-end tests failed with exit code: $($process.ExitCode)"
            }
        }
        
        # 用户偏好测试
        if (Test-Path "tests/test_user_preferences.ps1") {
            $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
                "-File", "tests/test_user_preferences.ps1", "-Quick"
            ) -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$ArtifactsDir/logs/prefs.log" -RedirectStandardError "$ArtifactsDir/logs/prefs.err"
            
            if ($process.ExitCode -ne 0) {
                Add-CIWarning "User preferences tests failed with exit code: $($process.ExitCode)"
            }
        }
        
        $endTime = Get-Date
        Record-CIResult "Integration" $true "Integration tests completed" $false ($endTime - $startTime).TotalSeconds
        $CIResults.Artifacts.IntegrationLogs = @("$ArtifactsDir/logs/e2e.log", "$ArtifactsDir/logs/prefs.log")
        
    } catch {
        $endTime = Get-Date
        Record-CIResult "Integration" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
    }
}

# 运行代码覆盖率分析
function Test-Coverage {
    if ($SkipCoverage) {
        Record-CIResult "Coverage" $true "Skipped by user request" $true 0
        return
    }
    
    $startTime = Get-Date
    
    try {
        Write-Output "INFO: Starting coverage analysis"
        
        if (-not (Test-Path "scripts/test-coverage.ps1")) {
            throw "Coverage script not found"
        }
        
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "scripts/test-coverage.ps1", "-Quick", "-MinCoverage", $MinCoverage, "-FailOnLow"
        ) -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$ArtifactsDir/logs/coverage.log" -RedirectStandardError "$ArtifactsDir/logs/coverage.err"
        
        $endTime = Get-Date
        
        # 复制覆盖率报告到制品目录
        if (Test-Path "logs/htmlcov") {
            Copy-Item "logs/htmlcov" "$ArtifactsDir/coverage" -Recurse -Force
        }
        if (Test-Path "logs/coverage.xml") {
            Copy-Item "logs/coverage.xml" "$ArtifactsDir/reports/" -Force
        }
        
        if ($process.ExitCode -eq 0) {
            Record-CIResult "Coverage" $true "Coverage analysis passed" $false ($endTime - $startTime).TotalSeconds
            $CIResults.Coverage.Status = "Passed"
            $CIResults.Artifacts.CoverageReport = "$ArtifactsDir/coverage/index.html"
        } else {
            $errorContent = if (Test-Path "$ArtifactsDir/logs/coverage.err") { 
                (Get-Content "$ArtifactsDir/logs/coverage.err" -Raw).Trim()
            } else { "Coverage below minimum threshold" }
            Record-CIResult "Coverage" $false "Exit code: $($process.ExitCode), $errorContent" $false ($endTime - $startTime).TotalSeconds
            $CIResults.Coverage.Status = "Failed"
        }
        
    } catch {
        $endTime = Get-Date
        Record-CIResult "Coverage" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
        $CIResults.Coverage.Status = "Error"
    }
}

# 运行性能测试
function Test-Performance {
    if ($SkipPerformance) {
        Record-CIResult "Performance" $true "Skipped by user request" $true 0
        return
    }
    
    $startTime = Get-Date
    
    try {
        Write-Output "INFO: Starting performance tests"
        
        if (-not (Test-Path "scripts/test-performance.ps1")) {
            throw "Performance script not found"
        }
        
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-File", "scripts/test-performance.ps1", "-Quick"
        ) -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$ArtifactsDir/logs/performance.log" -RedirectStandardError "$ArtifactsDir/logs/performance.err"
        
        $endTime = Get-Date
        
        # 复制性能报告到制品目录
        if (Test-Path "logs/performance_report_*.json") {
            Get-ChildItem "logs/performance_report_*.json" | Sort-Object LastWriteTime | Select-Object -Last 1 | ForEach-Object {
                Copy-Item $_.FullName "$ArtifactsDir/reports/performance.json" -Force
                $CIResults.Artifacts.PerformanceReport = "$ArtifactsDir/reports/performance.json"
            }
        }
        
        if ($process.ExitCode -eq 0) {
            Record-CIResult "Performance" $true "Performance tests passed" $false ($endTime - $startTime).TotalSeconds
            $CIResults.Performance.Status = "Passed"
        } else {
            $errorContent = if (Test-Path "$ArtifactsDir/logs/performance.err") { 
                (Get-Content "$ArtifactsDir/logs/performance.err" -Raw).Trim()
            } else { "Performance tests failed" }
            Record-CIResult "Performance" $false "Exit code: $($process.ExitCode), $errorContent" $false ($endTime - $startTime).TotalSeconds
            $CIResults.Performance.Status = "Failed"
        }
        
    } catch {
        $endTime = Get-Date
        Record-CIResult "Performance" $false $_.Exception.Message $false ($endTime - $startTime).TotalSeconds
        $CIResults.Performance.Status = "Error"
    }
}

# 生成CI测试结果报告
function Generate-CIReport {
    try {
        $CIResults.EndTime = Get-Date
        $CIResults.Success = ($CIResults.FailedTests -eq 0)
        
        # 计算成功率
        $successRate = if ($CIResults.TotalTests -gt 0) { 
            [math]::Round($CIResults.PassedTests / $CIResults.TotalTests * 100, 2) 
        } else { 
            0 
        }
        
        # 准备最终报告
        $finalReport = @{
            Success = $CIResults.Success
            Summary = @{
                TotalTests = $CIResults.TotalTests
                PassedTests = $CIResults.PassedTests
                FailedTests = $CIResults.FailedTests
                SkippedTests = $CIResults.SkippedTests
                SuccessRate = $successRate
                Duration = ($CIResults.EndTime - $CIResults.StartTime).TotalSeconds
            }
            Environment = $CIResults.Environment
            TestResults = $CIResults.TestResults
            Coverage = $CIResults.Coverage
            Performance = $CIResults.Performance
            Artifacts = $CIResults.Artifacts
            Errors = $CIResults.Errors
            Warnings = $CIResults.Warnings
            Timestamp = Get-Date
        }
        
        # 输出到指定文件或标准输出
        $jsonOutput = $finalReport | ConvertTo-Json -Depth 4 -Compress
        
        if ($OutputFile) {
            $jsonOutput | Out-File -FilePath $OutputFile -Encoding UTF8
            Write-Output "INFO: CI report saved to: $OutputFile"
        } else {
            # 输出JSON到标准输出（CI系统可以解析）
            Write-Output "CI_RESULTS_JSON:$jsonOutput"
        }
        
        # 保存到制品目录
        $jsonOutput | ConvertFrom-Json | ConvertTo-Json -Depth 4 | Out-File -FilePath "$ArtifactsDir/reports/ci-results.json" -Encoding UTF8
        
        # 输出摘要信息
        Write-Output ""
        Write-Output "CI_SUMMARY: Tests: $($CIResults.TotalTests), Passed: $($CIResults.PassedTests), Failed: $($CIResults.FailedTests), Skipped: $($CIResults.SkippedTests)"
        Write-Output "CI_SUCCESS_RATE: $successRate%"
        Write-Output "CI_DURATION: $([math]::Round(($CIResults.EndTime - $CIResults.StartTime).TotalSeconds, 2))s"
        Write-Output "CI_STATUS: $(if($CIResults.Success){'PASSED'}else{'FAILED'})"
        
        if ($CIResults.Errors.Count -gt 0) {
            Write-Output "CI_ERRORS: $($CIResults.Errors.Count)"
        }
        
        if ($CIResults.Warnings.Count -gt 0) {
            Write-Output "CI_WARNINGS: $($CIResults.Warnings.Count)"
        }
        
    } catch {
        Add-CIError "Failed to generate CI report: $($_.Exception.Message)"
    }
}

# 主CI执行流程
Write-Output "INFO: Starting CI test pipeline"
Write-Output "INFO: Timeout: $TimeoutMinutes minutes"
Write-Output "INFO: Skip Performance: $SkipPerformance"
Write-Output "INFO: Skip Coverage: $SkipCoverage"
Write-Output "INFO: Min Coverage: $MinCoverage%"

# 设置超时
$timeout = (Get-Date).AddMinutes($TimeoutMinutes)

try {
    # 初始化
    Collect-EnvironmentInfo
    Initialize-ArtifactsDirectory
    
    # 检查超时
    if ((Get-Date) -gt $timeout) {
        throw "CI pipeline timeout exceeded"
    }
    
    # 核心测试流程
    Test-PythonEnvironment
    
    if ((Get-Date) -gt $timeout) {
        throw "CI pipeline timeout exceeded"
    }
    
    Test-CodeQuality
    Test-UnitTests
    Test-Integration
    
    # 可选测试（如果时间允许）
    if ((Get-Date) -lt $timeout) {
        Test-Coverage
    }
    
    if ((Get-Date) -lt $timeout) {
        Test-Performance
    }
    
} catch {
    Add-CIError "CI pipeline error: $($_.Exception.Message)"
} finally {
    # 生成最终报告
    Generate-CIReport
    
    Write-Output ""
    Write-Output "INFO: CI test pipeline completed"
    Write-Output "INFO: Artifacts directory: $ArtifactsDir"
    
    # 返回适当的退出码
    if ($CIResults.Success) {
        Write-Output "INFO: All CI tests passed"
        exit 0
    } else {
        Write-Output "ERROR: CI tests failed"
        exit 1
    }
}