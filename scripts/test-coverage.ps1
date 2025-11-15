#!/usr/bin/env powershell
# 智能视频水印去除工具 - 测试覆盖率分析脚本
# 自动分析代码覆盖率，生成覆盖率报告，标识未测试的代码区域

param(
    [Parameter()]
    [switch]$Verbose,
    
    [Parameter()]
    [switch]$Quick,
    
    [Parameter()]
    [string]$OutputFormat = "html",
    
    [Parameter()]
    [string]$ReportPath = "logs/coverage_report",
    
    [Parameter()]
    [switch]$OpenReport,
    
    [Parameter()]
    [double]$MinCoverage = 80.0,
    
    [Parameter()]
    [switch]$FailOnLow
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

# 覆盖率结果追踪
$CoverageResults = @{
    OverallCoverage = 0.0
    ModuleCoverage = @{}
    UncoveredLines = @()
    CoveredLines = 0
    TotalLines = 0
    ReportFiles = @()
    StartTime = Get-Date
}

Write-Host "📊 智能视频水印去除工具 - 代码覆盖率分析" -ForegroundColor $Colors.Header
Write-Host "模式: $(if($Quick){'快速'}else{'完整'}) | 详细输出: $(if($Verbose){'开启'}else{'关闭'})" -ForegroundColor $Colors.Info
Write-Host "最小覆盖率阈值: $MinCoverage% | 输出格式: $OutputFormat" -ForegroundColor $Colors.Info
Write-Host "=" * 60 -ForegroundColor $Colors.Info

# 检查虚拟环境
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 虚拟环境不存在，请先运行: .\scripts\setup.ps1" -ForegroundColor $Colors.Error
    exit 1
}

# 激活虚拟环境
Write-Host "🔄 激活虚拟环境..." -ForegroundColor $Colors.Progress
. .\.venv\Scripts\Activate.ps1

# 设置环境变量
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = (Get-Location).Path

# 确保日志目录存在
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    Write-Host "📁 创建日志目录" -ForegroundColor $Colors.Info
}

#region 检查覆盖率工具
Write-Host ""
Write-Host "🔍 检查覆盖率分析工具..." -ForegroundColor $Colors.Progress

try {
    # 检查是否安装了coverage.py
    $coverageCheck = python -c "import coverage; print(coverage.__version__)"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ coverage.py 已安装，版本: $coverageCheck" -ForegroundColor $Colors.Success
    } else {
        Write-Host "❌ coverage.py 未安装" -ForegroundColor $Colors.Error
        Write-Host "正在安装 coverage.py..." -ForegroundColor $Colors.Info
        
        pip install coverage[toml] | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ coverage.py 安装失败" -ForegroundColor $Colors.Error
            exit 1
        }
        Write-Host "✅ coverage.py 安装成功" -ForegroundColor $Colors.Success
    }
} catch {
    Write-Host "❌ 覆盖率工具检查失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    exit 1
}
#endregion

#region 配置覆盖率分析
Write-Host ""
Write-Host "⚙️ 配置覆盖率分析..." -ForegroundColor $Colors.Progress

# 创建 .coveragerc 配置文件
$coverageConfig = @"
[run]
source = app
omit = 
    app/__init__.py
    app/*/__init__.py
    app/ui/resources/*
    */tests/*
    */test_*
    */.venv/*
    */venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    pass

[html]
directory = logs/htmlcov
title = 视频水印去除工具 - 代码覆盖率报告

[xml]
output = logs/coverage.xml

[json]
output = logs/coverage.json
"@

$coverageConfig | Out-File -FilePath ".coveragerc" -Encoding UTF8
Write-Host "✅ 覆盖率配置文件创建完成" -ForegroundColor $Colors.Success
#endregion

#region 运行覆盖率测试
Write-Host ""
Write-Host "🧪 运行覆盖率测试..." -ForegroundColor $Colors.Progress

try {
    # 清理之前的覆盖率数据
    if (Test-Path ".coverage") {
        Remove-Item ".coverage" -Force
    }
    if (Test-Path "logs/htmlcov") {
        Remove-Item "logs/htmlcov" -Recurse -Force
    }
    
    Write-Host "🔄 运行带覆盖率的测试..." -ForegroundColor $Colors.Detail
    
    # 构建覆盖率测试命令
    $coverageArgs = @("run", "-m", "pytest")
    
    if (Test-Path "tests") {
        $coverageArgs += "tests"
    }
    
    $coverageArgs += @("-v", "--tb=short")
    
    if ($Quick) {
        $coverageArgs += "-x"  # 停止在第一个失败
    }
    
    # 运行覆盖率测试
    coverage @coverageArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ 测试过程中有失败，但继续生成覆盖率报告" -ForegroundColor $Colors.Warning
    } else {
        Write-Host "✅ 覆盖率测试完成" -ForegroundColor $Colors.Success
    }
    
} catch {
    Write-Host "❌ 覆盖率测试执行失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    # 不退出，尝试生成已有的覆盖率数据报告
}
#endregion

#region 生成覆盖率报告
Write-Host ""
Write-Host "📋 生成覆盖率报告..." -ForegroundColor $Colors.Progress

try {
    # 生成控制台报告
    Write-Host "📄 生成控制台覆盖率报告..." -ForegroundColor $Colors.Detail
    $consoleReport = coverage report --format=text
    Write-Host $consoleReport -ForegroundColor $Colors.Detail
    
    # 解析总覆盖率
    $coverageLines = $consoleReport -split "`n"
    $totalLine = $coverageLines | Where-Object { $_ -match "TOTAL" } | Select-Object -Last 1
    if ($totalLine -and ($totalLine -match "(\d+)%")) {
        $CoverageResults.OverallCoverage = [double]$matches[1]
        Write-Host "📊 总体覆盖率: $($CoverageResults.OverallCoverage)%" -ForegroundColor $Colors.Info
    }
    
    # 生成HTML报告
    if ($OutputFormat -eq "html" -or $OutputFormat -eq "all") {
        Write-Host "🌐 生成HTML覆盖率报告..." -ForegroundColor $Colors.Detail
        coverage html
        if (Test-Path "logs/htmlcov/index.html") {
            $CoverageResults.ReportFiles += (Resolve-Path "logs/htmlcov/index.html").Path
            Write-Host "✅ HTML报告生成完成: logs/htmlcov/index.html" -ForegroundColor $Colors.Success
        }
    }
    
    # 生成XML报告
    if ($OutputFormat -eq "xml" -or $OutputFormat -eq "all") {
        Write-Host "📄 生成XML覆盖率报告..." -ForegroundColor $Colors.Detail
        coverage xml
        if (Test-Path "logs/coverage.xml") {
            $CoverageResults.ReportFiles += (Resolve-Path "logs/coverage.xml").Path
            Write-Host "✅ XML报告生成完成: logs/coverage.xml" -ForegroundColor $Colors.Success
        }
    }
    
    # 生成JSON报告
    if ($OutputFormat -eq "json" -or $OutputFormat -eq "all") {
        Write-Host "📊 生成JSON覆盖率报告..." -ForegroundColor $Colors.Detail
        coverage json
        if (Test-Path "logs/coverage.json") {
            $CoverageResults.ReportFiles += (Resolve-Path "logs/coverage.json").Path
            Write-Host "✅ JSON报告生成完成: logs/coverage.json" -ForegroundColor $Colors.Success
        }
    }
    
} catch {
    Write-Host "❌ 覆盖率报告生成失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
}
#endregion

#region 分析模块覆盖率
Write-Host ""
Write-Host "🔬 分析模块覆盖率..." -ForegroundColor $Colors.Progress

try {
    # 获取详细模块覆盖率信息
    $moduleReport = coverage report --format=text --show-missing
    $reportLines = $moduleReport -split "`n"
    
    $modulePattern = "^app[/\\]"
    
    foreach ($line in $reportLines) {
        if ($line -match $modulePattern -and $line -match "\s+(\d+)\s+(\d+)\s+(\d+)%") {
            $moduleName = ($line -split "\s+")[0]
            $statements = [int]$matches[1]
            $missing = [int]$matches[2]
            $coverage = [double]$matches[3]
            
            $CoverageResults.ModuleCoverage[$moduleName] = @{
                Statements = $statements
                Missing = $missing
                Coverage = $coverage
                CoveredLines = $statements - $missing
            }
            
            $CoverageResults.TotalLines += $statements
            $CoverageResults.CoveredLines += ($statements - $missing)
            
            $status = if ($coverage -ge $MinCoverage) { "✅" } else { "⚠️" }
            Write-Host "$status $moduleName`: $coverage% ($($statements - $missing)/$statements)" -ForegroundColor $(if($coverage -ge $MinCoverage) { $Colors.Success } else { $Colors.Warning })
        }
    }
    
} catch {
    Write-Host "❌ 模块覆盖率分析失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
}
#endregion

#region 识别未测试区域
if (-not $Quick) {
    Write-Host ""
    Write-Host "🔍 识别未测试的代码区域..." -ForegroundColor $Colors.Progress
    
    try {
        # 获取缺失的行号信息
        $missingReport = coverage report --show-missing --format=text
        $missingLines = $missingReport -split "`n"
        
        foreach ($line in $missingLines) {
            if ($line -match "^(app[/\\].*\.py)\s+\d+\s+\d+\s+\d+%\s+(.+)$") {
                $fileName = $matches[1]
                $missingLineNumbers = $matches[2]
                
                if ($missingLineNumbers -ne "" -and $missingLineNumbers -ne "0") {
                    $CoverageResults.UncoveredLines += @{
                        File = $fileName
                        Lines = $missingLineNumbers
                    }
                    
                    Write-Host "📄 $fileName`: 未覆盖行 $missingLineNumbers" -ForegroundColor $Colors.Warning
                }
            }
        }
        
        if ($CoverageResults.UncoveredLines.Count -eq 0) {
            Write-Host "🎉 所有代码行都已被测试覆盖！" -ForegroundColor $Colors.Success
        } else {
            Write-Host "⚠️ 发现 $($CoverageResults.UncoveredLines.Count) 个文件包含未测试代码" -ForegroundColor $Colors.Warning
        }
        
    } catch {
        Write-Host "❌ 未测试区域识别失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    }
}
#endregion

#region 生成覆盖率摘要
Write-Host ""
Write-Host "📈 覆盖率分析摘要" -ForegroundColor $Colors.Summary
Write-Host "=" * 50 -ForegroundColor $Colors.Info

$endTime = Get-Date
$duration = $endTime - $CoverageResults.StartTime

Write-Host "🕒 分析时间: $($duration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
Write-Host "📊 总体覆盖率: $($CoverageResults.OverallCoverage)%" -ForegroundColor $(if($CoverageResults.OverallCoverage -ge $MinCoverage) { $Colors.Success } else { $Colors.Warning })
Write-Host "📋 总代码行数: $($CoverageResults.TotalLines)" -ForegroundColor $Colors.Info
Write-Host "✅ 已覆盖行数: $($CoverageResults.CoveredLines)" -ForegroundColor $Colors.Success
Write-Host "❌ 未覆盖行数: $($CoverageResults.TotalLines - $CoverageResults.CoveredLines)" -ForegroundColor $Colors.Error
Write-Host "📁 模块数量: $($CoverageResults.ModuleCoverage.Count)" -ForegroundColor $Colors.Info
Write-Host "📄 生成报告: $($CoverageResults.ReportFiles.Count) 个" -ForegroundColor $Colors.Info

# 显示低覆盖率模块
$lowCoverageModules = $CoverageResults.ModuleCoverage.GetEnumerator() | Where-Object { $_.Value.Coverage -lt $MinCoverage }
if ($lowCoverageModules.Count -gt 0) {
    Write-Host ""
    Write-Host "⚠️ 低覆盖率模块 (< $MinCoverage%):" -ForegroundColor $Colors.Warning
    foreach ($module in $lowCoverageModules) {
        Write-Host "  📄 $($module.Key): $($module.Value.Coverage)%" -ForegroundColor $Colors.Warning
    }
}

# 显示高覆盖率模块
$highCoverageModules = $CoverageResults.ModuleCoverage.GetEnumerator() | Where-Object { $_.Value.Coverage -ge 95.0 }
if ($highCoverageModules.Count -gt 0) {
    Write-Host ""
    Write-Host "🏆 高覆盖率模块 (≥ 95%):" -ForegroundColor $Colors.Success
    foreach ($module in $highCoverageModules) {
        Write-Host "  📄 $($module.Key): $($module.Value.Coverage)%" -ForegroundColor $Colors.Success
    }
}
#endregion

#region 保存覆盖率数据
Write-Host ""
Write-Host "💾 保存覆盖率分析数据..." -ForegroundColor $Colors.Progress

$reportData = @{
    Timestamp = Get-Date
    OverallCoverage = $CoverageResults.OverallCoverage
    MinCoverage = $MinCoverage
    ModuleCoverage = $CoverageResults.ModuleCoverage
    UncoveredLines = $CoverageResults.UncoveredLines
    ReportFiles = $CoverageResults.ReportFiles
    Summary = @{
        TotalLines = $CoverageResults.TotalLines
        CoveredLines = $CoverageResults.CoveredLines
        UncoveredLines = $CoverageResults.TotalLines - $CoverageResults.CoveredLines
        ModuleCount = $CoverageResults.ModuleCoverage.Count
        LowCoverageCount = ($CoverageResults.ModuleCoverage.GetEnumerator() | Where-Object { $_.Value.Coverage -lt $MinCoverage }).Count
    }
}

$reportJson = $reportData | ConvertTo-Json -Depth 4
$reportPath = "logs/coverage_analysis_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$reportJson | Out-File -FilePath $reportPath -Encoding UTF8
Write-Host "📄 覆盖率分析数据已保存: $reportPath" -ForegroundColor $Colors.Info
#endregion

#region 打开报告
if ($OpenReport -and $CoverageResults.ReportFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "🌐 打开覆盖率报告..." -ForegroundColor $Colors.Progress
    
    $htmlReport = $CoverageResults.ReportFiles | Where-Object { $_ -match "\.html$" } | Select-Object -First 1
    if ($htmlReport) {
        try {
            Start-Process $htmlReport
            Write-Host "✅ HTML报告已在浏览器中打开" -ForegroundColor $Colors.Success
        } catch {
            Write-Host "❌ 无法打开HTML报告: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        }
    }
}
#endregion

# 清理配置文件
if (Test-Path ".coveragerc") {
    Remove-Item ".coveragerc" -Force
}

Write-Host ""
if ($CoverageResults.OverallCoverage -ge $MinCoverage) {
    Write-Host "🎉 代码覆盖率分析完成，覆盖率达到要求！" -ForegroundColor $Colors.Success
    Write-Host "📋 查看详细报告: .\logs\htmlcov\index.html" -ForegroundColor $Colors.Info
    
    if ($FailOnLow) {
        exit 0
    }
} else {
    Write-Host "⚠️ 代码覆盖率分析完成，但覆盖率低于要求 ($MinCoverage%)" -ForegroundColor $Colors.Warning
    Write-Host "📋 请查看报告并增加测试覆盖: .\logs\htmlcov\index.html" -ForegroundColor $Colors.Info
    
    if ($FailOnLow) {
        Write-Host "❌ 由于覆盖率不足，测试失败" -ForegroundColor $Colors.Error
        exit 1
    }
}