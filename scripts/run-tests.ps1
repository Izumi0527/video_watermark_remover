#!/usr/bin/env pwsh
# 运行单元测试脚本

param(
    [string]$TestPath = "tests/",
    [switch]$Coverage,
    [switch]$Verbose
)

Write-Host "🧪 Running unit tests..." -ForegroundColor Cyan

# 确保虚拟环境已激活
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Virtual environment not activated. Activating .venv..." -ForegroundColor Yellow
    & ".\.venv\Scripts\Activate.ps1"
}

# 构建 pytest 命令
$pytestCmd = "pytest"
$args = @($TestPath)

if ($Verbose) {
    $args += "-v"
}

if ($Coverage) {
    $args += "--cov=app"
    $args += "--cov-report=html"
    $args += "--cov-report=term"
}

# 添加颜色输出
$args += "--color=yes"

# 运行测试
Write-Host "Command: $pytestCmd $($args -join ' ')" -ForegroundColor Gray
& $pytestCmd @args

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "❌ Some tests failed." -ForegroundColor Red
}

exit $LASTEXITCODE
