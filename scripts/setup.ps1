# 智能视频水印去除工具 - 环境配置脚本
# 使用现代化的 uv 包管理器和 .venv 虚拟环境

# 设置错误处理
$ErrorActionPreference = "Stop"

Write-Host "🚀 智能视频水印去除工具 - 现代化环境配置" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan

# 检查 uv 是否已安装
$uvInstalled = $false
try {
    $uvVersion = uv --version 2>$null
    if ($uvVersion) {
        Write-Host "✅ uv 已安装: $uvVersion" -ForegroundColor Green
        $uvInstalled = $true
    }
} catch {
    $uvInstalled = $false
}

if (-not $uvInstalled) {
    Write-Host "⚡ 安装 uv 包管理器..." -ForegroundColor Yellow
    try {
        pip install uv
        Write-Host "✅ uv 安装完成" -ForegroundColor Green
    } catch {
        Write-Host "❌ uv 安装失败，请检查网络连接或手动安装" -ForegroundColor Red
        Write-Host "手动安装方法:" -ForegroundColor Cyan
        Write-Host "  pip install uv" -ForegroundColor White
        Write-Host "  或访问: https://github.com/astral-sh/uv" -ForegroundColor White
        exit 1
    }
}

# 检查并删除旧的 venv 目录
if (Test-Path "venv") {
    Write-Host "🗑️ 删除旧的 venv 目录..." -ForegroundColor Magenta
    Remove-Item -Path "venv" -Recurse -Force
    Write-Host "✅ 旧环境已清理" -ForegroundColor Green
}

# 创建 .venv 虚拟环境
if (-not (Test-Path ".venv")) {
    Write-Host "🐍 创建 .venv 虚拟环境..." -ForegroundColor Blue
    try {
        uv venv .venv
        Write-Host "✅ .venv 环境创建完成" -ForegroundColor Green
    } catch {
        Write-Host "❌ .venv 环境创建失败" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ .venv 环境已存在" -ForegroundColor Green
}

# 激活虚拟环境并安装依赖
Write-Host "📦 使用 uv 安装依赖包..." -ForegroundColor Cyan

# 激活 Windows 虚拟环境
Write-Host "🔄 激活虚拟环境..." -ForegroundColor Blue
. .\.venv\Scripts\Activate.ps1
Write-Host "✅ Windows 环境已激活" -ForegroundColor Green

# 使用 uv 安装核心依赖
Write-Host "📦 安装核心依赖..." -ForegroundColor Yellow
try {
    uv pip install "PyQt6>=6.6.0"
    uv pip install "opencv-python>=4.8.0"
    uv pip install "numpy>=1.25.0"
    uv pip install "Pillow>=10.0.0"
    Write-Host "✅ 核心依赖安装完成" -ForegroundColor Green
} catch {
    Write-Host "❌ 核心依赖安装失败" -ForegroundColor Red
    exit 1
}

# 安装开发依赖
Write-Host "🧪 安装开发和测试依赖..." -ForegroundColor Magenta
try {
    uv pip install "pytest>=7.0.0"
    uv pip install "pytest-qt>=4.2.0"
    uv pip install "black>=23.0.0"
    uv pip install "flake8>=6.0.0"
    uv pip install "mypy>=1.0.0"
    Write-Host "✅ 开发依赖安装完成" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 开发依赖安装失败，但核心功能仍可使用" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 环境配置完成！" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "✅ 使用现代化的 uv + .venv 环境" -ForegroundColor Green
Write-Host "✅ 核心依赖已安装" -ForegroundColor Green
Write-Host "✅ 开发工具已配置" -ForegroundColor Green
Write-Host ""
Write-Host "📝 使用说明：" -ForegroundColor Yellow
Write-Host "   激活环境: .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   启动应用: .\scripts\run.ps1" -ForegroundColor Cyan
Write-Host "   运行测试: .\scripts\test.ps1" -ForegroundColor Cyan
Write-Host "   构建发布: .\scripts\build.ps1" -ForegroundColor Cyan
Write-Host ""
