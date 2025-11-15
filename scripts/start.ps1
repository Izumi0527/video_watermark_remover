# ============================================================
# 智能视频水印去除工具 - 启动脚本
# ============================================================
# 功能：
#   - 环境检查（Python、依赖、FFmpeg、配置文件）
#   - 详细日志记录（logs/log_YYYYMMDD.log）
#   - 错误诊断和自动修复
#   - 彩色终端输出
# 用法：
#   .\scripts\start.ps1 [-AutoFix] [-Verbose] [-SkipChecks]
# 参数：
#   -AutoFix: 自动修复检测到的问题
#   -Verbose: 显示详细调试信息
#   -SkipChecks: 跳过环境检查（不推荐）
# ============================================================

param(
    [switch]$AutoFix = $false,
    [switch]$Verbose = $false,
    [switch]$SkipChecks = $false
)

# ============================================================
# 全局配置
# ============================================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDate = Get-Date -Format "yyyyMMdd"
$LogTime = Get-Date -Format "HH:mm:ss"
$LogFile = Join-Path $ProjectRoot "logs\log_$LogDate.log"

# 确保日志目录存在
$LogsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# ============================================================
# 日志函数
# ============================================================

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [ConsoleColor]$Color = [ConsoleColor]::White,
        [switch]$NoConsole
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"

    # 写入日志文件
    Add-Content -Path $LogFile -Value $logMessage -Encoding UTF8

    # 控制台输出
    if (-not $NoConsole) {
        $prefix = switch ($Level) {
            "SUCCESS" { "[✓] " }
            "ERROR"   { "[✗] " }
            "WARNING" { "[!] " }
            "INFO"    { "[i] " }
            "DEBUG"   { "[→] " }
            default   { "    " }
        }
        Write-Host $prefix -NoNewline -ForegroundColor $Color
        Write-Host $Message -ForegroundColor $Color
    }
}

function Write-Success {
    param([string]$Message)
    Write-Log -Message $Message -Level "SUCCESS" -Color Green
}

function Write-Error-Log {
    param([string]$Message)
    Write-Log -Message $Message -Level "ERROR" -Color Red
}

function Write-Warning-Log {
    param([string]$Message)
    Write-Log -Message $Message -Level "WARNING" -Color Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Log -Message $Message -Level "INFO" -Color Cyan
}

function Write-Debug-Log {
    param([string]$Message)
    if ($Verbose) {
        Write-Log -Message $Message -Level "DEBUG" -Color DarkGray
    } else {
        Write-Log -Message $Message -Level "DEBUG" -Color DarkGray -NoConsole
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Log -Message "========== $Title ==========" -Level "INFO" -NoConsole
}

# ============================================================
# 启动脚本
# ============================================================

Clear-Host
Write-Section "智能视频水印去除工具 - 启动"

Write-Info "项目路径: $ProjectRoot"
Write-Info "日志文件: $LogFile"
Write-Info "启动时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Log -Message "脚本参数: AutoFix=$AutoFix, Verbose=$Verbose, SkipChecks=$SkipChecks" -Level "DEBUG" -NoConsole

# ============================================================
# 系统信息收集
# ============================================================

Write-Section "系统信息"

$osInfo = Get-CimInstance Win32_OperatingSystem
$computerInfo = Get-CimInstance Win32_ComputerSystem

Write-Info "操作系统: $($osInfo.Caption) ($($osInfo.Version))"
Write-Info "计算机名: $($computerInfo.Name)"
Write-Info "用户名: $env:USERNAME"
Write-Info "工作目录: $PWD"

Write-Debug-Log "系统架构: $($osInfo.OSArchitecture)"
Write-Debug-Log "物理内存: $([math]::Round($computerInfo.TotalPhysicalMemory / 1GB, 2)) GB"
Write-Debug-Log "处理器: $($computerInfo.NumberOfProcessors) 个"

# 切换到项目根目录
Set-Location $ProjectRoot
Write-Debug-Log "已切换到项目根目录: $ProjectRoot"

# ============================================================
# 环境检查
# ============================================================

$checksPassed = $true
$issuesFound = @()
$fixes = @()

# 全局变量：Python 路径
$activePython = "python"  # 默认使用全局 Python
$venvPath = Join-Path $ProjectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not $SkipChecks) {
    Write-Section "环境检查"

    # ------------------------------------------------------------
    # 1. 检查 uv（必需，用于包管理）
    # ------------------------------------------------------------

    Write-Info "检查 uv 包管理器（必需）..."

    try {
        $uvVersion = & uv --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "uv 已安装: $uvVersion"
            Write-Debug-Log "uv 路径: $(& where.exe uv 2>$null | Select-Object -First 1)"
            Write-Info "将使用 uv 进行所有包管理操作（比 pip 快 10-100 倍）"
        } else {
            throw "uv 未找到"
        }
    }
    catch {
        Write-Error-Log "uv 未安装（必需工具）"
        Write-Error-Log "本项目要求使用 uv 进行包管理"
        $issuesFound += "uv 未安装"
        $fixes += "安装 uv: pip install uv"
        $fixes += "或访问: https://github.com/astral-sh/uv"
        $checksPassed = $false

        Write-Host ""
        Write-Host "════════════════════════════════════════" -ForegroundColor Red
        Write-Host "  安装 uv 的方法：" -ForegroundColor Yellow
        Write-Host "════════════════════════════════════════" -ForegroundColor Red
        Write-Host ""
        Write-Host "  方法 1 (推荐): " -ForegroundColor Cyan -NoNewline
        Write-Host "pip install uv" -ForegroundColor White
        Write-Host ""
        Write-Host "  方法 2: " -ForegroundColor Cyan -NoNewline
        Write-Host "winget install --id=astral-sh.uv -e" -ForegroundColor White
        Write-Host ""
        Write-Host "  方法 3: " -ForegroundColor Cyan -NoNewline
        Write-Host "PowerShell 脚本" -ForegroundColor White
        Write-Host "  powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "════════════════════════════════════════" -ForegroundColor Red
        Write-Host ""

        # uv 是必需的，如果未安装则无法继续
        Write-Error-Log "请先安装 uv 后再运行此脚本"
        Write-Log -Message "启动失败: uv 未安装" -Level "ERROR" -NoConsole
        exit 1
    }

    # ------------------------------------------------------------
    # 2. 检查虚拟环境（优先级最高）
    # ------------------------------------------------------------

    Write-Info "检查 Python 虚拟环境..."

    $venvExists = $false

    if (Test-Path $venvPath) {
        if (Test-Path $venvPython) {
            $venvExists = $true
            $activePython = $venvPython  # 使用虚拟环境的 Python
            Write-Success "虚拟环境已创建: .venv"
            Write-Debug-Log "虚拟环境路径: $venvPath"

            # 检查虚拟环境中的 Python 版本
            try {
                $venvPythonVersion = & $venvPython --version 2>&1
                Write-Success "虚拟环境 Python 版本: $venvPythonVersion"
                Write-Info "将使用虚拟环境的 Python 进行后续检查"
            }
            catch {
                Write-Warning-Log "无法获取虚拟环境 Python 版本: $_"
            }
        } else {
            Write-Warning-Log "虚拟环境目录存在但不完整（缺少 python.exe）"
            $issuesFound += "虚拟环境损坏"
            $fixes += "重新创建虚拟环境: uv venv .venv"
            $checksPassed = $false
        }
    } else {
        Write-Warning-Log "虚拟环境未创建"
        $issuesFound += "虚拟环境不存在"
        $fixes += "创建虚拟环境: uv venv .venv"

        if ($AutoFix) {
            Write-Info "正在使用 uv 自动创建虚拟环境..."
            try {
                Write-Debug-Log "执行命令: uv venv .venv"
                & uv venv .venv

                if ($LASTEXITCODE -eq 0) {
                    Write-Success "虚拟环境创建成功"
                    # 更新路径
                    if (Test-Path $venvPython) {
                        $venvExists = $true
                        $activePython = $venvPython
                        Write-Debug-Log "已更新 activePython: $activePython"
                    }
                } else {
                    throw "uv venv 失败（退出代码: $LASTEXITCODE）"
                }
            }
            catch {
                Write-Error-Log "自动创建虚拟环境失败: $_"
                $checksPassed = $false
            }
        } else {
            $checksPassed = $false
        }
    }

    # ------------------------------------------------------------
    # 3. 检查 Python 环境（使用 activePython）
    # ------------------------------------------------------------

    Write-Info "检查 Python 环境..."
    if ($venvExists) {
        Write-Info "使用虚拟环境的 Python: $activePython"
    } else {
        Write-Info "使用全局 Python"
    }

    try {
        $pythonVersion = & $activePython --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Python 已安装: $pythonVersion"
            Write-Debug-Log "Python 路径: $activePython"

            # 检查 Python 版本
            if ($pythonVersion -match "Python (\d+)\.(\d+)") {
                $majorVersion = [int]$matches[1]
                $minorVersion = [int]$matches[2]

                if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
                    Write-Warning-Log "Python 版本过低（需要 3.8+），当前: $pythonVersion"
                    $issuesFound += "Python 版本过低"
                    $fixes += "请安装 Python 3.8 或更高版本: https://www.python.org/downloads/"
                    $checksPassed = $false
                } else {
                    Write-Debug-Log "Python 版本符合要求: $majorVersion.$minorVersion"
                }
            }
        } else {
            throw "Python 未找到"
        }
    }
    catch {
        Write-Error-Log "Python 未安装或未添加到 PATH"
        Write-Error-Log "错误详情: $_"
        $issuesFound += "Python 未安装"
        $fixes += "请安装 Python 3.8+: https://www.python.org/downloads/"
        $checksPassed = $false
    }

    # ------------------------------------------------------------
    # 4. 检查依赖包（使用 uv pip）
    # ------------------------------------------------------------

    Write-Info "检查 Python 依赖包..."
    Write-Info "使用 uv 进行包管理"

    $requirementsFile = Join-Path $ProjectRoot "requirements.txt"

    if (Test-Path $requirementsFile) {
        Write-Debug-Log "requirements.txt 文件存在"

        if ($venvExists) {
            # 检查关键依赖
            $keyPackages = @("PyQt6", "opencv-python", "numpy", "Pillow")
            $missingPackages = @()

            foreach ($package in $keyPackages) {
                # 使用 uv pip show 检查包
                $installed = & uv pip show $package 2>&1

                if ($LASTEXITCODE -ne 0) {
                    $missingPackages += $package
                    Write-Warning-Log "缺少依赖包: $package"
                } else {
                    Write-Debug-Log "已安装: $package"
                }
            }

            if ($missingPackages.Count -gt 0) {
                Write-Warning-Log "检测到 $($missingPackages.Count) 个缺失的关键依赖包"
                $issuesFound += "缺失依赖包: $($missingPackages -join ', ')"
                $fixes += "安装依赖: uv pip install -r requirements.txt"

                if ($AutoFix) {
                    Write-Info "正在使用 uv 自动安装依赖包..."
                    try {
                        Write-Debug-Log "执行命令: uv pip install -r $requirementsFile"
                        & uv pip install -r $requirementsFile

                        if ($LASTEXITCODE -eq 0) {
                            Write-Success "依赖包安装成功"
                        } else {
                            throw "uv pip install 失败（退出代码: $LASTEXITCODE）"
                        }
                    }
                    catch {
                        Write-Error-Log "自动安装依赖失败: $_"
                        $checksPassed = $false
                    }
                } else {
                    $checksPassed = $false
                }
            } else {
                Write-Success "所有关键依赖包已安装"
            }
        } else {
            Write-Warning-Log "虚拟环境不存在，跳过依赖包检查"
        }
    } else {
        Write-Error-Log "requirements.txt 文件不存在"
        $issuesFound += "缺少 requirements.txt"
        $checksPassed = $false
    }

    # ------------------------------------------------------------
    # 5. 检查 FFmpeg
    # ------------------------------------------------------------

    Write-Info "检查 FFmpeg..."

    try {
        $ffmpegVersion = & ffmpeg -version 2>&1 | Select-Object -First 1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "FFmpeg 已安装: $($ffmpegVersion -replace 'ffmpeg version ', '')"
            Write-Debug-Log "FFmpeg 路径: $(& where.exe ffmpeg 2>$null | Select-Object -First 1)"
        } else {
            throw "FFmpeg 未找到"
        }
    }
    catch {
        Write-Warning-Log "FFmpeg 未安装或未添加到 PATH"
        Write-Warning-Log "注意: 音频处理功能将不可用"
        $issuesFound += "FFmpeg 未安装"
        $fixes += "安装 FFmpeg: https://ffmpeg.org/download.html 或使用 winget install ffmpeg"
    }

    # ------------------------------------------------------------
    # 6. 检查配置文件
    # ------------------------------------------------------------

    Write-Info "检查配置文件..."

    $configFile = Join-Path $ProjectRoot "config.ini"
    $configExample = Join-Path $ProjectRoot "config.ini.example"

    if (Test-Path $configFile) {
        Write-Success "配置文件已存在: config.ini"
        Write-Debug-Log "配置文件路径: $configFile"
    } elseif (Test-Path $configExample) {
        Write-Warning-Log "配置文件不存在，但找到模板文件"
        $issuesFound += "配置文件不存在"
        $fixes += "从模板创建配置文件: copy config.ini.example config.ini"

        if ($AutoFix) {
            Write-Info "正在从模板创建配置文件..."
            try {
                Copy-Item $configExample $configFile
                Write-Success "配置文件创建成功"
            }
            catch {
                Write-Error-Log "自动创建配置文件失败: $_"
                $checksPassed = $false
            }
        } else {
            $checksPassed = $false
        }
    } else {
        Write-Error-Log "配置文件和模板文件都不存在"
        $issuesFound += "缺少配置文件和模板"
        $checksPassed = $false
    }

    # ------------------------------------------------------------
    # 7. 检查主程序文件
    # ------------------------------------------------------------

    Write-Info "检查主程序文件..."

    $mainFile = Join-Path $ProjectRoot "main.py"

    if (Test-Path $mainFile) {
        Write-Success "主程序文件存在: main.py"
        Write-Debug-Log "主程序路径: $mainFile"
    } else {
        Write-Error-Log "主程序文件不存在: main.py"
        $issuesFound += "缺少主程序文件"
        $checksPassed = $false
    }

    # ------------------------------------------------------------
    # 8. 检查应用模块
    # ------------------------------------------------------------

    Write-Info "检查应用模块..."

    $appDir = Join-Path $ProjectRoot "app"

    if (Test-Path $appDir) {
        $criticalModules = @("__init__.py", "core", "ui", "config", "utils")
        $missingModules = @()

        foreach ($module in $criticalModules) {
            $modulePath = Join-Path $appDir $module
            if (-not (Test-Path $modulePath)) {
                $missingModules += $module
                Write-Warning-Log "缺少模块: app\$module"
            } else {
                Write-Debug-Log "模块存在: app\$module"
            }
        }

        if ($missingModules.Count -eq 0) {
            Write-Success "所有核心模块完整"
        } else {
            Write-Error-Log "缺少 $($missingModules.Count) 个核心模块"
            $issuesFound += "缺少核心模块: $($missingModules -join ', ')"
            $checksPassed = $false
        }
    } else {
        Write-Error-Log "应用目录不存在: app"
        $issuesFound += "缺少应用目录"
        $checksPassed = $false
    }

    # ------------------------------------------------------------
    # 检查结果汇总
    # ------------------------------------------------------------

    Write-Section "检查结果"

    if ($checksPassed) {
        Write-Success "所有环境检查通过！"
        Write-Log -Message "环境检查: 全部通过" -Level "SUCCESS" -NoConsole
    } else {
        Write-Error-Log "发现 $($issuesFound.Count) 个问题："
        foreach ($issue in $issuesFound) {
            Write-Host "  • " -NoNewline -ForegroundColor Red
            Write-Host $issue -ForegroundColor Red
            Write-Log -Message "问题: $issue" -Level "ERROR" -NoConsole
        }

        Write-Host ""
        Write-Warning-Log "修复建议："
        foreach ($fix in $fixes) {
            Write-Host "  → " -NoNewline -ForegroundColor Yellow
            Write-Host $fix -ForegroundColor Yellow
            Write-Log -Message "修复建议: $fix" -Level "WARNING" -NoConsole
        }

        Write-Host ""
        Write-Info "提示: 使用 -AutoFix 参数可自动修复部分问题"
        Write-Host ""
        Write-Error-Log "环境检查未通过，无法启动应用"
        Write-Log -Message "启动失败: 环境检查未通过" -Level "ERROR" -NoConsole
        exit 1
    }
}

# ============================================================
# 激活虚拟环境并启动应用
# ============================================================

Write-Section "启动应用"

$venvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
$mainPy = Join-Path $ProjectRoot "main.py"

if (Test-Path $venvActivate) {
    Write-Info "激活虚拟环境..."
    Write-Debug-Log "激活脚本路径: $venvActivate"

    try {
        # 激活虚拟环境
        & $venvActivate
        Write-Success "虚拟环境已激活"
        Write-Debug-Log "当前 Python: $(& python -c 'import sys; print(sys.executable)')"
    }
    catch {
        Write-Error-Log "激活虚拟环境失败: $_"
        Write-Log -Message "启动失败: 无法激活虚拟环境" -Level "ERROR" -NoConsole
        exit 1
    }
} else {
    Write-Warning-Log "虚拟环境激活脚本不存在，使用全局 Python"
}

# 启动应用
Write-Info "正在启动应用..."
Write-Info "主程序: $mainPy"
Write-Info "Python: $activePython"
Write-Info "包管理器: uv"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  应用启动中..." -ForegroundColor Green
Write-Host "  按 Ctrl+C 可终止应用" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Log -Message "应用启动: $activePython $mainPy" -Level "INFO" -NoConsole

try {
    # 启动应用（使用 activePython）
    & $activePython $mainPy

    $exitCode = $LASTEXITCODE

    Write-Host ""
    if ($exitCode -eq 0) {
        Write-Success "应用正常退出"
        Write-Log -Message "应用退出: 退出代码 $exitCode" -Level "SUCCESS" -NoConsole
    } else {
        Write-Warning-Log "应用退出，退出代码: $exitCode"
        Write-Log -Message "应用退出: 退出代码 $exitCode" -Level "WARNING" -NoConsole
    }
}
catch {
    Write-Error-Log "应用启动失败: $_"
    Write-Error-Log "异常类型: $($_.Exception.GetType().FullName)"
    Write-Error-Log "异常堆栈: $($_.ScriptStackTrace)"
    Write-Log -Message "启动失败: $_" -Level "ERROR" -NoConsole

    Write-Host ""
    Write-Section "错误诊断"

    Write-Info "正在分析错误..."

    # 错误诊断
    $errorMessage = $_.Exception.Message

    if ($errorMessage -match "ModuleNotFoundError|ImportError") {
        Write-Error-Log "检测到 Python 模块导入错误"
        Write-Info "可能的原因："
        Write-Host "  1. 依赖包未安装" -ForegroundColor Yellow
        Write-Host "  2. 虚拟环境未正确激活" -ForegroundColor Yellow
        Write-Host ""
        Write-Info "建议修复步骤："
        Write-Host "  → uv pip install -r requirements.txt" -ForegroundColor Cyan
    }
    elseif ($errorMessage -match "FileNotFoundError") {
        Write-Error-Log "检测到文件未找到错误"
        Write-Info "可能的原因："
        Write-Host "  1. 配置文件缺失" -ForegroundColor Yellow
        Write-Host "  2. 资源文件缺失" -ForegroundColor Yellow
        Write-Host ""
        Write-Info "建议修复步骤："
        Write-Host "  → 检查 config.ini 文件是否存在" -ForegroundColor Cyan
        Write-Host "  → 从模板创建: copy config.ini.example config.ini" -ForegroundColor Cyan
    }
    elseif ($errorMessage -match "PermissionError") {
        Write-Error-Log "检测到权限错误"
        Write-Info "可能的原因："
        Write-Host "  1. 文件被其他程序占用" -ForegroundColor Yellow
        Write-Host "  2. 没有读写权限" -ForegroundColor Yellow
        Write-Host ""
        Write-Info "建议修复步骤："
        Write-Host "  → 关闭可能占用文件的程序" -ForegroundColor Cyan
        Write-Host "  → 使用管理员权限运行" -ForegroundColor Cyan
    }
    else {
        Write-Warning-Log "无法自动诊断错误类型"
        Write-Info "请查看日志文件获取详细信息: $LogFile"
    }

    Write-Host ""
    exit 1
}

# ============================================================
# 清理和退出
# ============================================================

Write-Host ""
Write-Section "清理"

Write-Info "日志已保存到: $LogFile"
Write-Success "脚本执行完成"
Write-Log -Message "========== 脚本执行完成 ==========" -Level "INFO" -NoConsole

exit 0
