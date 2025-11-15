# 智能视频水印去除工具 - 环境安装脚本 (旧版)
# 自动检测系统并安装相应依赖

# 设置错误处理
$ErrorActionPreference = "Stop"

Write-Host "🚀 智能视频水印去除工具 - 环境安装脚本" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan

# 检测操作系统
Write-Host "🪟 检测到 Windows 系统 (PowerShell)" -ForegroundColor Yellow

# 检查Python版本
Write-Host ""
Write-Host "🐍 检查Python版本..." -ForegroundColor Blue

try {
    $pythonVersion = python --version 2>$null
    if ($pythonVersion) {
        Write-Host "✅ $pythonVersion" -ForegroundColor Green
        $pythonCmd = "python"
    } else {
        throw "Python not found"
    }
} catch {
    try {
        $python3Version = python3 --version 2>$null
        if ($python3Version) {
            Write-Host "✅ $python3Version" -ForegroundColor Green
            $pythonCmd = "python3"
        } else {
            throw "Python3 not found"
        }
    } catch {
        Write-Host "❌ 未找到Python，请先安装Python 3.8+" -ForegroundColor Red
        exit 1
    }
}

# 检查pip
Write-Host ""
Write-Host "📦 检查pip..." -ForegroundColor Blue

try {
    $pipTest = pip --version 2>$null
    if ($pipTest) {
        $pipCmd = "pip"
        Write-Host "✅ 找到pip" -ForegroundColor Green
    } else {
        throw "pip not found"
    }
} catch {
    try {
        $pip3Test = pip3 --version 2>$null
        if ($pip3Test) {
            $pipCmd = "pip3"
            Write-Host "✅ 找到pip3" -ForegroundColor Green
        } else {
            throw "pip3 not found"
        }
    } catch {
        Write-Host "❌ 未找到pip，请先安装pip" -ForegroundColor Red
        exit 1
    }
}

# 询问安装类型
Write-Host ""
Write-Host "📋 请选择安装类型:" -ForegroundColor Cyan
Write-Host "1) 最小安装 (仅核心功能)" -ForegroundColor White
Write-Host "2) 完整安装 (包含AI功能)" -ForegroundColor White
Write-Host "3) 开发环境 (包含开发工具)" -ForegroundColor White

$installType = Read-Host "请输入选择 (1-3)"

switch ($installType) {
    "1" {
        $requirementsFile = "requirements-minimal.txt"
        Write-Host "🎯 选择最小安装" -ForegroundColor Yellow
    }
    "2" {
        $requirementsFile = "requirements.txt"
        Write-Host "🎯 选择完整安装" -ForegroundColor Yellow
    }
    "3" {
        $requirementsFile = "requirements-dev.txt"
        Write-Host "🎯 选择开发环境安装" -ForegroundColor Yellow
    }
    default {
        Write-Host "❌ 无效选择，使用默认完整安装" -ForegroundColor Red
        $requirementsFile = "requirements.txt"
    }
}

# 创建虚拟环境
Write-Host ""
Write-Host "🏠 创建Python虚拟环境..." -ForegroundColor Blue

if (-not (Test-Path "venv")) {
    & $pythonCmd -m venv venv
    Write-Host "✅ 虚拟环境创建成功" -ForegroundColor Green
} else {
    Write-Host "✅ 虚拟环境已存在" -ForegroundColor Green
}

# 激活虚拟环境
Write-Host ""
Write-Host "🔄 激活虚拟环境..." -ForegroundColor Blue
. .\venv\Scripts\Activate.ps1
Write-Host "✅ 虚拟环境已激活" -ForegroundColor Green

# 升级pip
Write-Host ""
Write-Host "⬆️ 升级pip..." -ForegroundColor Magenta
python -m pip install --upgrade pip
Write-Host "✅ pip升级完成" -ForegroundColor Green

# 安装依赖
Write-Host ""
Write-Host "📦 安装Python依赖..." -ForegroundColor Blue
Write-Host "使用文件: $requirementsFile" -ForegroundColor Yellow

if (Test-Path $requirementsFile) {
    pip install -r $requirementsFile
    Write-Host "✅ Python依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "❌ 依赖文件 $requirementsFile 不存在" -ForegroundColor Red
    exit 1
}

# 检查FFmpeg
Write-Host ""
Write-Host "🎬 检查FFmpeg..." -ForegroundColor Blue

try {
    $ffmpegVersion = ffmpeg -version 2>$null | Select-Object -First 1
    if ($ffmpegVersion) {
        Write-Host "✅ FFmpeg已安装: $ffmpegVersion" -ForegroundColor Green
    } else {
        throw "ffmpeg not found"
    }
} catch {
    Write-Host "⚠️ 未检测到FFmpeg" -ForegroundColor Yellow
    Write-Host "📖 FFmpeg Windows安装指南:" -ForegroundColor Cyan
    Write-Host "  1. 访问 https://ffmpeg.org/download.html#build-windows" -ForegroundColor White
    Write-Host "  2. 下载预编译的Windows二进制文件" -ForegroundColor White
    Write-Host "  3. 解压到任意目录（推荐: C:\ffmpeg）" -ForegroundColor White
    Write-Host "  4. 将 C:\ffmpeg\bin 添加到系统环境变量 PATH" -ForegroundColor White
    Write-Host "  5. 重启PowerShell或命令提示符" -ForegroundColor White
    Write-Host ""
    Write-Host "或者使用包管理器安装:" -ForegroundColor Cyan
    Write-Host "  Chocolatey: choco install ffmpeg" -ForegroundColor White
    Write-Host "  Scoop: scoop install ffmpeg" -ForegroundColor White
    Write-Host "  winget: winget install Gyan.FFmpeg" -ForegroundColor White
}

# 运行测试询问
Write-Host ""
$runTest = Read-Host "是否运行基础测试? [y/N]"

if ($runTest -eq "y" -or $runTest -eq "Y") {
    Write-Host "🧪 运行基础测试..." -ForegroundColor Green
    if (Test-Path "test_phase3.py") {
        python test_phase3.py
    } else {
        Write-Host "⚠️ 测试文件 test_phase3.py 不存在" -ForegroundColor Yellow
    }
}

# 完成安装
Write-Host ""
Write-Host "🎉 安装完成!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📖 使用说明:" -ForegroundColor Yellow
Write-Host "1. 激活虚拟环境:" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. 运行程序:" -ForegroundColor White
Write-Host "   python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. 停用虚拟环境:" -ForegroundColor White
Write-Host "   deactivate" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 更多信息请查看项目文档和README文件" -ForegroundColor Blue
