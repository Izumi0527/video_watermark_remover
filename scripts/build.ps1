# 智能视频水印去除工具 - 构建发布脚本
# 打包生成可执行文件

# 设置错误处理
$ErrorActionPreference = "Stop"

Write-Host "📦 构建发布版本..." -ForegroundColor Yellow

# 检查 .venv 是否存在
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 虚拟环境不存在，请先运行: .\scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

# 激活 Windows 虚拟环境
Write-Host "🔄 激活虚拟环境..." -ForegroundColor Blue
. .\.venv\Scripts\Activate.ps1

# 安装打包工具
Write-Host "🔧 安装打包工具..." -ForegroundColor Cyan
uv pip install PyInstaller>=5.0.0

# 清理之前的构建
Write-Host "🧹 清理构建目录..." -ForegroundColor Magenta
if (Test-Path "build") { Remove-Item -Path "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item -Path "dist" -Recurse -Force }
Get-ChildItem -Path "." -Filter "*.spec" | Remove-Item -Force

# 运行测试确保代码正常
Write-Host "🧪 运行测试确保代码质量..." -ForegroundColor Green
.\scripts\test.ps1

# 使用PyInstaller打包
Write-Host "📦 使用PyInstaller打包..." -ForegroundColor Yellow
$iconPath = "app\assets\icons\app.ico"
if (-not (Test-Path $iconPath)) {
    Write-Host "⚠️ 图标文件不存在，将使用默认图标" -ForegroundColor Yellow
    pyinstaller --onefile `
                --windowed `
                --name="智能水印去除工具" `
                --add-data="app;app" `
                --add-data="models;models" `
                --hidden-import="PyQt6" `
                --hidden-import="cv2" `
                --hidden-import="numpy" `
                main.py
} else {
    pyinstaller --onefile `
                --windowed `
                --name="智能水印去除工具" `
                --icon="$iconPath" `
                --add-data="app;app" `
                --add-data="models;models" `
                --hidden-import="PyQt6" `
                --hidden-import="cv2" `
                --hidden-import="numpy" `
                main.py
}

# 创建发布目录
Write-Host "📁 创建发布包..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "release" -Force | Out-Null
Copy-Item -Path "dist\*" -Destination "release" -Recurse -Force
if (Test-Path "README.md") { Copy-Item -Path "README.md" -Destination "release" }
if (Test-Path "requirements.txt") { Copy-Item -Path "requirements.txt" -Destination "release" }

# 创建版本信息
Write-Host "📝 生成版本信息..." -ForegroundColor Blue
$versionInfo = @"
智能视频水印去除工具
版本: v0.3.0-optimized
构建时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Python版本: $(python --version)
构建环境: 现代化 uv + .venv 环境
操作系统: Windows (PowerShell)
"@

$versionInfo | Out-File -FilePath "release\VERSION.txt" -Encoding UTF8

Write-Host ""
Write-Host "🎉 构建完成！" -ForegroundColor Green
Write-Host "📦 发布文件位于: release\ 目录" -ForegroundColor Yellow
Write-Host "📊 构建日志已保存到 logs\ 目录" -ForegroundColor Cyan