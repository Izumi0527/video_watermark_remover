# 智能视频水印去除工具 - 应用启动脚本
# 自动激活环境并启动应用

# 设置错误处理
$ErrorActionPreference = "Stop"

Write-Host "🎬 启动智能视频水印去除工具..." -ForegroundColor Green

# 检查 .venv 是否存在
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 虚拟环境不存在，请先运行: .\scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

# 激活 Windows 虚拟环境
Write-Host "🔄 激活虚拟环境..." -ForegroundColor Blue
. .\.venv\Scripts\Activate.ps1
Write-Host "✅ 虚拟环境已激活" -ForegroundColor Green

# 确保日志目录存在
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    Write-Host "📁 创建日志目录" -ForegroundColor Cyan
}

# 启动应用
Write-Host "🚀 启动应用程序..." -ForegroundColor Yellow
python main.py

Write-Host "✨ 应用程序已退出" -ForegroundColor Magenta
