# ============================================================
# 清除项目缓存脚本
# ============================================================
# 功能：清除 Python 项目中的各种缓存和临时文件
# 用法：.\scripts\clean-cache.ps1 [-Force]
# 参数：
#   -Force: 跳过确认提示，直接清理
# ============================================================

param(
    [switch]$Force = $false
)

# 设置错误处理
$ErrorActionPreference = "Continue"

# 获取项目根目录（脚本所在目录的上级目录）
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# 切换到项目根目录
Set-Location $ProjectRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  智能视频水印去除工具 - 缓存清理脚本" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "项目目录: " -NoNewline
Write-Host $ProjectRoot -ForegroundColor Yellow
Write-Host ""

# 定义要清理的内容
$CleanupTargets = @(
    @{
        Name = "Python 字节码缓存 (__pycache__)"
        Pattern = "__pycache__"
        Type = "Directory"
        Color = "Yellow"
    },
    @{
        Name = "Python 编译文件 (*.pyc)"
        Pattern = "*.pyc"
        Type = "File"
        Color = "Yellow"
    },
    @{
        Name = "Python 编译文件 (*.pyo)"
        Pattern = "*.pyo"
        Type = "File"
        Color = "Yellow"
    },
    @{
        Name = "MyPy 类型检查缓存"
        Pattern = ".mypy_cache"
        Type = "Directory"
        Color = "Magenta"
    },
    @{
        Name = "Pytest 测试缓存"
        Pattern = ".pytest_cache"
        Type = "Directory"
        Color = "Magenta"
    },
    @{
        Name = "Coverage 覆盖率报告"
        Pattern = ".coverage"
        Type = "File"
        Color = "Magenta"
    },
    @{
        Name = "Coverage 数据文件 (.coverage.*)"
        Pattern = ".coverage.*"
        Type = "File"
        Color = "Magenta"
    },
    @{
        Name = "日志文件 (logs/*.log)"
        Pattern = "logs\*.log"
        Type = "File"
        Color = "Blue"
    },
    @{
        Name = "测试报告 JSON (*_test_report.json)"
        Pattern = "*_test_report.json"
        Type = "File"
        Color = "Blue"
    },
    @{
        Name = "测试报告 HTML (*_test_report.html)"
        Pattern = "*_test_report.html"
        Type = "File"
        Color = "Blue"
    },
    @{
        Name = "临时文件 (*.tmp)"
        Pattern = "*.tmp"
        Type = "File"
        Color = "Gray"
    },
    @{
        Name = "备份文件 (*.bak)"
        Pattern = "*.bak"
        Type = "File"
        Color = "Gray"
    },
    @{
        Name = "备份文件 (*.backup)"
        Pattern = "*.backup"
        Type = "File"
        Color = "Gray"
    },
    @{
        Name = "缓存文件 (*.cache)"
        Pattern = "*.cache"
        Type = "File"
        Color = "Gray"
    }
)

# 扫描要清理的项
Write-Host "正在扫描缓存文件..." -ForegroundColor Cyan
Write-Host ""

$ItemsToClean = @()
$TotalSize = 0

foreach ($target in $CleanupTargets) {
    $items = @()

    if ($target.Type -eq "Directory") {
        $items = Get-ChildItem -Path $ProjectRoot -Recurse -Directory -Filter $target.Pattern -ErrorAction SilentlyContinue
    }
    else {
        $items = Get-ChildItem -Path $ProjectRoot -Recurse -File -Filter $target.Pattern -ErrorAction SilentlyContinue
    }

    if ($items.Count -gt 0) {
        $size = 0
        foreach ($item in $items) {
            if ($target.Type -eq "Directory") {
                $size += (Get-ChildItem -Path $item.FullName -Recurse -File -ErrorAction SilentlyContinue |
                          Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            }
            else {
                $size += $item.Length
            }
        }

        $TotalSize += $size
        $sizeInMB = [math]::Round($size / 1MB, 2)

        Write-Host "  [✓] " -NoNewline -ForegroundColor Green
        Write-Host $target.Name -NoNewline -ForegroundColor $target.Color
        Write-Host ": " -NoNewline
        Write-Host "$($items.Count) 项" -NoNewline -ForegroundColor White
        Write-Host " ($sizeInMB MB)" -ForegroundColor DarkGray

        $ItemsToClean += @{
            Target = $target
            Items = $items
            Size = $size
        }
    }
    else {
        Write-Host "  [ ] " -NoNewline -ForegroundColor DarkGray
        Write-Host $target.Name -NoNewline -ForegroundColor DarkGray
        Write-Host ": 0 项" -ForegroundColor DarkGray
    }
}

Write-Host ""

# 如果没有找到要清理的项
if ($ItemsToClean.Count -eq 0) {
    Write-Host "✓ 未发现需要清理的缓存文件！" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# 显示总计
$totalItems = ($ItemsToClean | ForEach-Object { $_.Items.Count } | Measure-Object -Sum).Sum
$totalSizeInMB = [math]::Round($TotalSize / 1MB, 2)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  总计: " -NoNewline -ForegroundColor White
Write-Host "$totalItems 项" -NoNewline -ForegroundColor Yellow
Write-Host ", 约 " -NoNewline -ForegroundColor White
Write-Host "$totalSizeInMB MB" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 如果没有 -Force 参数，询问确认
if (-not $Force) {
    $confirmation = Read-Host "是否继续清理？(y/N)"
    if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
        Write-Host ""
        Write-Host "已取消清理操作。" -ForegroundColor Yellow
        Write-Host ""
        exit 0
    }
}

# 执行清理
Write-Host ""
Write-Host "开始清理..." -ForegroundColor Cyan
Write-Host ""

$cleanedCount = 0
$failedCount = 0
$cleanedSize = 0

foreach ($cleanItem in $ItemsToClean) {
    $target = $cleanItem.Target
    $items = $cleanItem.Items

    Write-Host "正在清理 " -NoNewline
    Write-Host $target.Name -NoNewline -ForegroundColor $target.Color
    Write-Host "..." -NoNewline

    $currentCleaned = 0
    $currentFailed = 0

    foreach ($item in $items) {
        try {
            # 在删除前检查文件/目录是否存在（避免竞态条件）
            if (-not (Test-Path $item.FullName)) {
                # 文件/目录已不存在（可能被之前的操作删除了）
                continue
            }

            if ($target.Type -eq "Directory") {
                Remove-Item -Path $item.FullName -Recurse -Force -ErrorAction Stop
            }
            else {
                Remove-Item -Path $item.FullName -Force -ErrorAction Stop
            }
            $currentCleaned++
        }
        catch {
            $currentFailed++
            Write-Host ""
            Write-Host "  [!] 清理失败: $($item.FullName)" -ForegroundColor Red
            Write-Host "      错误信息: $($_.Exception.Message)" -ForegroundColor DarkRed
        }
    }

    $cleanedCount += $currentCleaned
    $failedCount += $currentFailed
    $cleanedSize += $cleanItem.Size

    if ($currentFailed -eq 0) {
        Write-Host " 完成 ($currentCleaned 项)" -ForegroundColor Green
    }
    else {
        Write-Host " 部分完成 ($currentCleaned 成功, $currentFailed 失败)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  清理完成！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  成功清理: " -NoNewline
Write-Host "$cleanedCount 项" -ForegroundColor Green
if ($failedCount -gt 0) {
    Write-Host "  清理失败: " -NoNewline
    Write-Host "$failedCount 项" -ForegroundColor Red
}
Write-Host "  释放空间: " -NoNewline
Write-Host "$([math]::Round($cleanedSize / 1MB, 2)) MB" -ForegroundColor Yellow
Write-Host ""

# 显示建议
if ($failedCount -gt 0) {
    Write-Host "提示: 部分文件清理失败，可能被其他程序占用。" -ForegroundColor Yellow
    Write-Host "      请关闭相关程序后重试，或使用管理员权限运行此脚本。" -ForegroundColor Yellow
    Write-Host ""
}

exit 0
