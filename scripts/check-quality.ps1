#!/usr/bin/env powershell
# 智能视频水印去除工具 - 代码质量检查脚本
# 集成 Black、Flake8、MyPy 进行自动化代码质量检查

param(
    [Parameter()]
    [switch]$Fix,

    [Parameter()]
    [switch]$Verbose,

    [Parameter()]
    [switch]$Quick,

    [Parameter()]
    [ValidateSet("all", "format", "style", "type")]
    [string]$Check = "all",

    [Parameter()]
    [switch]$Help
)

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
    Write-Host "🔍 智能视频水印去除工具 - 代码质量检查" -ForegroundColor $Colors.Header
    Write-Host "=" * 60 -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "用法:" -ForegroundColor $Colors.Header
    Write-Host "  .\scripts\check-quality.ps1 [选项]" -ForegroundColor $Colors.Detail
    Write-Host ""
    Write-Host "选项:" -ForegroundColor $Colors.Header
    Write-Host "  -Fix        - 自动修复代码格式问题 (使用 Black 格式化)" -ForegroundColor $Colors.Detail
    Write-Host "  -Verbose    - 显示详细输出信息" -ForegroundColor $Colors.Detail
    Write-Host "  -Quick      - 快速检查模式 (跳过类型检查)" -ForegroundColor $Colors.Detail
    Write-Host "  -Check      - 指定检查类型: all, format, style, type" -ForegroundColor $Colors.Detail
    Write-Host "  -Help       - 显示此帮助信息" -ForegroundColor $Colors.Detail
    Write-Host ""
    Write-Host "检查类型:" -ForegroundColor $Colors.Header
    Write-Host "  all         - 运行所有检查 (默认)" -ForegroundColor $Colors.Detail
    Write-Host "  format      - 仅检查代码格式 (Black)" -ForegroundColor $Colors.Detail
    Write-Host "  style       - 仅检查代码风格 (Flake8)" -ForegroundColor $Colors.Detail
    Write-Host "  type        - 仅检查类型注解 (MyPy)" -ForegroundColor $Colors.Detail
    Write-Host ""
    Write-Host "示例:" -ForegroundColor $Colors.Header
    Write-Host "  .\scripts\check-quality.ps1                # 运行所有检查" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\check-quality.ps1 -Fix           # 自动修复格式问题" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\check-quality.ps1 -Quick         # 快速检查（跳过MyPy）" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\check-quality.ps1 -Check format  # 仅检查代码格式" -ForegroundColor $Colors.Detail
    Write-Host "  .\scripts\check-quality.ps1 -Verbose       # 显示详细输出" -ForegroundColor $Colors.Detail
    Write-Host ""
}

# 如果请求帮助，显示帮助后退出
if ($Help) {
    Show-Help
    exit 0
}

# 质量检查结果追踪
$QualityResults = @{
    Format = @{Passed = $null; Details = ""}
    Style = @{Passed = $null; Details = ""}
    Type = @{Passed = $null; Details = ""}
    StartTime = Get-Date
}

Write-Host "🔍 智能视频水印去除工具 - 代码质量检查" -ForegroundColor $Colors.Header
Write-Host "检查模式: $Check | 自动修复: $(if($Fix){'启用'}else{'禁用'}) | 详细输出: $(if($Verbose){'启用'}else{'禁用'})" -ForegroundColor $Colors.Info
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

# 确定要检查的目标路径
$targetPaths = @()
if (Test-Path "app") { $targetPaths += "app" }
if (Test-Path "main.py") { $targetPaths += "main.py" }
if (Test-Path "tests") { $targetPaths += "tests" }

if ($targetPaths.Count -eq 0) {
    Write-Host "❌ 未找到代码文件，无法执行质量检查" -ForegroundColor $Colors.Error
    exit 1
}

Write-Host "📁 检查目标: $($targetPaths -join ', ')" -ForegroundColor $Colors.Info
Write-Host ""

#region 代码格式检查 (Black)
function Check-CodeFormat {
    if ($Check -ne "all" -and $Check -ne "format") { return }

    Write-Host "📝 代码格式检查 (Black)..." -ForegroundColor $Colors.Progress
    Write-Host "─" * 60 -ForegroundColor $Colors.Info

    try {
        $blackArgs = @()

        if ($Fix) {
            # 修复模式：自动格式化代码
            $blackArgs = $targetPaths
            Write-Host "🔧 自动格式化代码..." -ForegroundColor $Colors.Info
        } else {
            # 检查模式：只检查不修复
            $blackArgs = @("--check", "--diff") + $targetPaths
        }

        if ($Verbose) {
            $blackArgs += "--verbose"
        }

        # 执行 Black
        $output = black @blackArgs 2>&1
        $exitCode = $LASTEXITCODE

        if ($Verbose -or $exitCode -ne 0) {
            Write-Host $output -ForegroundColor $Colors.Detail
        }

        if ($exitCode -eq 0) {
            if ($Fix) {
                Write-Host "✅ 代码已格式化" -ForegroundColor $Colors.Success
            } else {
                Write-Host "✅ 代码格式符合规范" -ForegroundColor $Colors.Success
            }
            $QualityResults.Format.Passed = $true
            $QualityResults.Format.Details = "Black formatting check passed"
        } else {
            if ($Fix) {
                Write-Host "⚠️ 代码格式化过程中出现问题" -ForegroundColor $Colors.Warning
            } else {
                Write-Host "❌ 代码格式不符合规范" -ForegroundColor $Colors.Error
                Write-Host "💡 建议运行: .\scripts\check-quality.ps1 -Fix" -ForegroundColor $Colors.Warning
            }
            $QualityResults.Format.Passed = $false
            $QualityResults.Format.Details = "Black formatting issues found"
        }
    } catch {
        Write-Host "❌ Black 执行失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        $QualityResults.Format.Passed = $false
        $QualityResults.Format.Details = "Black execution error: $($_.Exception.Message)"
    }

    Write-Host ""
}
#endregion

#region 代码风格检查 (Flake8)
function Check-CodeStyle {
    if ($Check -ne "all" -and $Check -ne "style") { return }

    Write-Host "📋 代码风格检查 (Flake8)..." -ForegroundColor $Colors.Progress
    Write-Host "─" * 60 -ForegroundColor $Colors.Info

    try {
        $flakeArgs = $targetPaths

        if ($Quick) {
            # 快速模式：仅检查严重错误
            $flakeArgs += @("--select=E9,F63,F7,F82")
            Write-Host "⚡ 快速模式：仅检查严重错误" -ForegroundColor $Colors.Info
        }

        if ($Verbose) {
            $flakeArgs += "--show-source"
        }

        # 执行 Flake8 (配置从 .flake8 文件读取)
        $output = flake8 @flakeArgs 2>&1
        $exitCode = $LASTEXITCODE

        if ($Verbose -or $exitCode -ne 0) {
            Write-Host $output -ForegroundColor $Colors.Detail
        }

        if ($exitCode -eq 0) {
            Write-Host "✅ 代码风格符合规范" -ForegroundColor $Colors.Success
            $QualityResults.Style.Passed = $true
            $QualityResults.Style.Details = "Flake8 style check passed"
        } else {
            Write-Host "❌ 发现代码风格问题" -ForegroundColor $Colors.Error
            Write-Host "💡 请根据上述提示修复代码风格问题" -ForegroundColor $Colors.Warning
            $QualityResults.Style.Passed = $false
            $QualityResults.Style.Details = "Flake8 style issues found"
        }
    } catch {
        Write-Host "❌ Flake8 执行失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        $QualityResults.Style.Passed = $false
        $QualityResults.Style.Details = "Flake8 execution error: $($_.Exception.Message)"
    }

    Write-Host ""
}
#endregion

#region 类型检查 (MyPy)
function Check-TypeAnnotations {
    if ($Quick) {
        Write-Host "⚡ 快速模式：跳过类型检查" -ForegroundColor $Colors.Info
        Write-Host ""
        return
    }

    if ($Check -ne "all" -and $Check -ne "type") { return }

    Write-Host "🔍 类型注解检查 (MyPy)..." -ForegroundColor $Colors.Progress
    Write-Host "─" * 60 -ForegroundColor $Colors.Info

    try {
        # 只检查 app 目录和 main.py，不检查 tests
        $mypyTargets = @()
        if (Test-Path "app") { $mypyTargets += "app" }
        if (Test-Path "main.py") { $mypyTargets += "main.py" }

        if ($mypyTargets.Count -eq 0) {
            Write-Host "⚠️ 未找到需要类型检查的文件" -ForegroundColor $Colors.Warning
            return
        }

        # MyPy 配置从 pyproject.toml 读取
        $mypyArgs = $mypyTargets

        if ($Verbose) {
            $mypyArgs += "--verbose"
        }

        # 执行 MyPy
        $output = mypy @mypyArgs 2>&1
        $exitCode = $LASTEXITCODE

        if ($Verbose -or $exitCode -ne 0) {
            Write-Host $output -ForegroundColor $Colors.Detail
        }

        if ($exitCode -eq 0) {
            Write-Host "✅ 类型注解检查通过" -ForegroundColor $Colors.Success
            $QualityResults.Type.Passed = $true
            $QualityResults.Type.Details = "MyPy type check passed"
        } else {
            Write-Host "❌ 发现类型注解问题" -ForegroundColor $Colors.Error
            Write-Host "💡 请根据上述提示修复类型注解问题" -ForegroundColor $Colors.Warning
            $QualityResults.Type.Passed = $false
            $QualityResults.Type.Details = "MyPy type issues found"
        }
    } catch {
        Write-Host "❌ MyPy 执行失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
        $QualityResults.Type.Passed = $false
        $QualityResults.Type.Details = "MyPy execution error: $($_.Exception.Message)"
    }

    Write-Host ""
}
#endregion

#region 显示检查摘要
function Show-Summary {
    $endTime = Get-Date
    $duration = $endTime - $QualityResults.StartTime

    Write-Host "📊 代码质量检查摘要" -ForegroundColor $Colors.Summary
    Write-Host "=" * 60 -ForegroundColor $Colors.Info
    Write-Host "🕒 检查耗时: $($duration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
    Write-Host ""

    $allPassed = $true
    $checkedCount = 0
    $passedCount = 0

    # 统计结果
    if ($QualityResults.Format.Passed -ne $null) {
        $checkedCount++
        $status = if ($QualityResults.Format.Passed) { "✅" } else { "❌" }
        $color = if ($QualityResults.Format.Passed) { $Colors.Success } else { $Colors.Error }
        Write-Host "$status 代码格式 (Black)" -ForegroundColor $color
        if ($QualityResults.Format.Passed) { $passedCount++ } else { $allPassed = $false }
    }

    if ($QualityResults.Style.Passed -ne $null) {
        $checkedCount++
        $status = if ($QualityResults.Style.Passed) { "✅" } else { "❌" }
        $color = if ($QualityResults.Style.Passed) { $Colors.Success } else { $Colors.Error }
        Write-Host "$status 代码风格 (Flake8)" -ForegroundColor $color
        if ($QualityResults.Style.Passed) { $passedCount++ } else { $allPassed = $false }
    }

    if ($QualityResults.Type.Passed -ne $null) {
        $checkedCount++
        $status = if ($QualityResults.Type.Passed) { "✅" } else { "❌" }
        $color = if ($QualityResults.Type.Passed) { $Colors.Success } else { $Colors.Error }
        Write-Host "$status 类型注解 (MyPy)" -ForegroundColor $color
        if ($QualityResults.Type.Passed) { $passedCount++ } else { $allPassed = $false }
    }

    Write-Host ""
    Write-Host "总计: $passedCount/$checkedCount 项通过" -ForegroundColor $Colors.Info

    if ($allPassed) {
        Write-Host ""
        Write-Host "🎉 所有代码质量检查通过！" -ForegroundColor $Colors.Success
        Write-Host ""
        exit 0
    } else {
        Write-Host ""
        Write-Host "⚠️ 部分检查未通过，请修复上述问题" -ForegroundColor $Colors.Warning
        if (-not $Fix -and $QualityResults.Format.Passed -eq $false) {
            Write-Host "💡 提示: 使用 -Fix 参数自动修复代码格式问题" -ForegroundColor $Colors.Info
        }
        Write-Host ""
        exit 1
    }
}
#endregion

# 主执行逻辑
try {
    Check-CodeFormat
    Check-CodeStyle
    Check-TypeAnnotations
    Show-Summary
} catch {
    Write-Host "❌ 代码质量检查过程中发生严重错误: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    Write-Host $_.ScriptStackTrace -ForegroundColor $Colors.Detail
    exit 1
} finally {
    Write-Host "📝 使用 '.\scripts\check-quality.ps1 -Help' 查看详细使用说明" -ForegroundColor $Colors.Info
}
