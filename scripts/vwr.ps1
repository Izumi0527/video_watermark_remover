#!/usr/bin/env powershell
# ============================================================
# 智能视频水印去除工具 - 统一脚本入口（Windows PowerShell）
# ============================================================
# 目标：
# - 将 scripts/ 目录脚本整合为单一入口，降低维护成本
# - 提供 setup/run/test/quality/coverage/perf/build/clean/ci 等常用命令
#
# 用法：
#   .\scripts\vwr.ps1 help
#   .\scripts\vwr.ps1 setup -Dev -TorchBackend cpu -DefaultIndex "https://pypi.tuna.tsinghua.edu.cn/simple"
#   .\scripts\vwr.ps1 run -AutoFix
#   .\scripts\vwr.ps1 test unit -Quick
# ============================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("help", "setup", "run", "quality", "test", "coverage", "perf", "build", "clean", "ci")]
    [string]$Command = "help",

    [Parameter(Position = 1)]
    [string]$Arg1 = "",

    [Parameter(Position = 2)]
    [string]$Arg2 = "",

    [Parameter()]
    [switch]$Quick,

    # setup
    [Parameter()]
    [switch]$Dev,

    [Parameter()]
    [string]$Python = "3.12.10",

    [Parameter()]
    [ValidateSet("auto", "cpu", "cu118", "cu121", "cu124", "cu126", "cu128", "cu129", "cu130")]
    [string]$TorchBackend = "auto",

    [Parameter()]
    [string]$DefaultIndex = "",

    [Parameter()]
    [ValidateSet("first-index", "unsafe-first-match", "unsafe-best-match")]
    [string]$IndexStrategy = "first-index",

    # run
    [Parameter()]
    [switch]$AutoFix,

    [Parameter()]
    [switch]$SkipChecks,

    # quality
    [Parameter()]
    [switch]$Fix,

    [Parameter()]
    [ValidateSet("all", "format", "style", "type", "security")]
    [string]$Check = "all",

    # test/coverage/perf
    [Parameter()]
    [switch]$Coverage,

    [Parameter()]
    [switch]$Performance,

    [Parameter()]
    [switch]$Report,

    # coverage
    [Parameter()]
    [double]$MinCoverage = 80.0,

    [Parameter()]
    [switch]$FailOnLow,

    [Parameter()]
    [switch]$OpenReport,

    # perf
    [Parameter()]
    [int]$Iterations = 5,

    [Parameter()]
    [switch]$MemoryProfile,

    [Parameter()]
    [switch]$GPUProfile,

    [Parameter()]
    [string]$PerfReportPath = "",

    # build
    [Parameter()]
    [switch]$SkipTests,

    # clean
    [Parameter()]
    [switch]$Force,

    # ci
    [Parameter()]
    [switch]$SkipPerformance,

    [Parameter()]
    [switch]$SkipCoverage,

    [Parameter()]
    [string]$OutputFile = "",

    [Parameter()]
    [string]$ArtifactsDir = "ci-artifacts",

    [Parameter()]
    [int]$TimeoutMinutes = 30
)

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Global:VwrLogFile = $null
$script:DefaultIndexIsBound = $PSBoundParameters.ContainsKey("DefaultIndex")

function Initialize-Log {
    if ($Global:VwrLogFile) {
        return
    }

    $logsDir = Join-Path $ProjectRoot "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }

    $date = Get-Date -Format "yyyyMMdd"
    $Global:VwrLogFile = Join-Path $logsDir "vwr_$date.log"
}

function Write-LogLine {
    param(
        [string]$Level,
        [string]$Message
    )

    if (-not $Global:VwrLogFile) {
        return
    }

    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $Global:VwrLogFile -Value "[$ts] [$Level] $Message" -Encoding UTF8
}

function Write-Line {
    param(
        [string]$Prefix,
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::White,
        [string]$LevelForLog = ""
    )

    if ($LevelForLog) {
        Write-LogLine -Level $LevelForLog -Message $Message
    }

    Write-Host $Prefix -NoNewline -ForegroundColor $Color
    Write-Host $Message -ForegroundColor $Color
}

function Write-Info([string]$Message) { Write-Line -Prefix "[i] " -Message $Message -Color Cyan -LevelForLog "INFO" }
function Write-Ok([string]$Message) { Write-Line -Prefix "[✓] " -Message $Message -Color Green -LevelForLog "SUCCESS" }
function Write-Warn([string]$Message) { Write-Line -Prefix "[!] " -Message $Message -Color Yellow -LevelForLog "WARNING" }
function Write-Err([string]$Message) { Write-Line -Prefix "[✗] " -Message $Message -Color Red -LevelForLog "ERROR" }

function Is-VerboseEnabled {
    return ($VerbosePreference -eq "Continue")
}

function Write-Debug([string]$Message) {
    if (Is-VerboseEnabled) {
        Write-Line -Prefix "[→] " -Message $Message -Color DarkGray -LevelForLog "DEBUG"
    } else {
        Write-LogLine -Level "DEBUG" -Message $Message
    }
}

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-LogLine -Level "INFO" -Message "========== $Title =========="
}

function Get-VenvInfo {
    $venvRoot = Join-Path $ProjectRoot ".venv"
    $venvPython = Join-Path $venvRoot "Scripts/python.exe"
    $venvActivate = Join-Path $venvRoot "Scripts/Activate.ps1"
    return @{
        Root = $venvRoot
        Python = $venvPython
        Activate = $venvActivate
    }
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-IsChinaLikeEnv {
    try {
        $culture = (Get-Culture).Name
        if ($culture -eq "zh-CN") { return $true }
        if ($culture -like "zh-*") { return $true }
    } catch {
        # ignore
    }

    try {
        $tz = Get-TimeZone
        if ($tz.Id -eq "China Standard Time") { return $true }
        if ($tz.StandardName -like "*中国*") { return $true }
    } catch {
        # ignore
    }

    return $false
}

function Resolve-UvDefaultIndex {
    param(
        [string]$UserValue,
        [bool]$UserProvided
    )

    # 如果用户显式传了 -DefaultIndex（哪怕是空字符串），则尊重用户输入
    if ($UserProvided) {
        if ($null -eq $UserValue) {
            return ""
        }
        return $UserValue
    }

    foreach ($candidate in @(
        $env:VWR_UV_DEFAULT_INDEX,
        $env:UV_DEFAULT_INDEX,
        $env:PIP_INDEX_URL
    )) {
        if ($candidate -and $candidate.Trim()) {
            return $candidate.Trim()
        }
    }

    # 中国环境下默认使用镜像，以提升 uv/pip 的下载速度（可通过 -DefaultIndex 或 env:UV_DEFAULT_INDEX 覆盖）
    if (Test-IsChinaLikeEnv) {
        return "https://pypi.tuna.tsinghua.edu.cn/simple"
    }

    return ""
}

function Resolve-UvCacheDir {
    foreach ($candidate in @($env:VWR_UV_CACHE_DIR, $env:UV_CACHE_DIR)) {
        if ($candidate -and $candidate.Trim()) {
            return $candidate.Trim()
        }
    }
    return ""
}

function Get-PythonSemVerFromText {
    param([string]$Text)

    if (-not $Text) {
        return ""
    }

    $t = $Text.Trim()

    if ($t -match "Python\s+(\d+\.\d+\.\d+)") {
        return $Matches[1]
    }

    if ($t -match "(\d+\.\d+\.\d+)") {
        return $Matches[1]
    }

    return $t
}

function Test-IsPythonVersionSelector {
    param([string]$Selector)

    if (-not $Selector) {
        return $false
    }

    return ($Selector.Trim() -match "^\d+(\.\d+){1,2}$")
}

function Test-PythonVersionMatchesSelector {
    param(
        [string]$CurrentVersion,
        [string]$Selector
    )

    if (-not $Selector) {
        return $true
    }
    if (-not $CurrentVersion) {
        return $false
    }

    $sel = $Selector.Trim()
    $cur = $CurrentVersion.Trim()

    if ($sel -match "^\d+\.\d+\.\d+$") {
        return ($cur -eq $sel)
    }

    if ($sel -match "^\d+\.\d+$") {
        if ($cur -eq $sel) {
            return $true
        }
        return $cur.StartsWith("$sel.")
    }

    return $false
}

function Ensure-Uv {
    if (Test-CommandExists "uv") {
        Write-Debug "已检测到 uv：$(& uv --version 2>$null)"
        return
    }

    Write-Warn "未检测到 uv，准备安装（推荐 winget，失败则回退 pip）"

    if (Test-CommandExists "winget") {
        try {
            Write-Info "使用 winget 安装 uv..."
            & winget install --id "astral-sh.uv" -e --accept-package-agreements --accept-source-agreements | Out-Host
        } catch {
            Write-Warn "winget 安装 uv 失败：$($_.Exception.Message)"
        }
    } else {
        Write-Debug "未检测到 winget"
    }

    if (-not (Test-CommandExists "uv")) {
        # 尝试使用官方安装脚本（通常比 pip 更快，且不依赖 Python 环境）
        try {
            Write-Info "尝试使用官方安装脚本安装 uv..."
            $cmd = "irm https://astral.sh/uv/install.ps1 | iex"
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $cmd | Out-Host
        } catch {
            Write-Warn "官方安装脚本执行失败：$($_.Exception.Message)"
        }
    }

    if (-not (Test-CommandExists "uv")) {
        if (-not (Test-CommandExists "python")) {
            throw "无法安装 uv：未找到 uv 且系统中未找到 python。请先安装 uv（winget）或 python。"
        }

        Write-Info "使用 pip 安装 uv（可能较慢）..."
        $pipArgs = @("-m", "pip", "install", "--upgrade", "uv")
        $pipIndex = Resolve-UvDefaultIndex -UserValue $DefaultIndex -UserProvided:$script:DefaultIndexIsBound
        if ($pipIndex) {
            $pipArgs += @("-i", $pipIndex)
            Write-Debug "pip 镜像：$pipIndex"
        }

        & python @pipArgs | Out-Host
    }

    if (-not (Test-CommandExists "uv")) {
        throw "uv 安装失败。请手动安装：winget install --id=astral-sh.uv -e 或 python -m pip install uv"
    }

    Write-Ok "uv 安装完成：$(& uv --version 2>$null)"
}

function Ensure-Venv {
    param([string]$PythonSelector)

    $venv = Get-VenvInfo
    if (Test-Path $venv.Python) {
        $currentRaw = & $venv.Python --version 2>$null
        $currentVer = Get-PythonSemVerFromText -Text $currentRaw

        if (-not $PythonSelector) {
            Write-Ok "虚拟环境已存在：.venv (Python $currentVer)"
            return
        }

        if (Test-IsPythonVersionSelector -Selector $PythonSelector) {
            if (Test-PythonVersionMatchesSelector -CurrentVersion $currentVer -Selector $PythonSelector) {
                Write-Ok "虚拟环境已存在：.venv (Python $currentVer)"
                return
            }

            Write-Warn "检测到 .venv Python=$currentVer，与期望=$PythonSelector 不一致，需要重新创建 .venv（将删除现有虚拟环境）"
            try {
                $activeVenv = $null
                $targetVenv = $null

                if ($env:VIRTUAL_ENV) {
                    $activeVenv = (Resolve-Path $env:VIRTUAL_ENV -ErrorAction SilentlyContinue).Path
                }
                $targetVenv = (Resolve-Path $venv.Root -ErrorAction SilentlyContinue).Path

                if ($activeVenv -and $targetVenv -and ($activeVenv -eq $targetVenv)) {
                    Write-Warn "检测到当前终端已激活 .venv，重建可能失败。建议先执行 deactivate 或重新打开 PowerShell。"
                }
            } catch {
                # ignore
            }
            if (-not $Force) {
                $ans = Read-Host "是否继续重建 .venv？(y/N)"
                if ($ans -ne "y" -and $ans -ne "Y") {
                    throw "已取消重建 .venv。你可以删除 .venv 后重试，或添加 -Force 跳过确认。"
                }
            }

            Ensure-Uv

            Write-Info "重新创建虚拟环境：.venv (Python $PythonSelector)"
            $uvArgs = @("venv", "-c", "--python", $PythonSelector, ".venv")
            Write-Debug ("执行命令：uv " + ($uvArgs -join " "))
            & uv @uvArgs | Out-Host

            if (-not (Test-Path $venv.Python)) {
                throw "虚拟环境重建失败：未找到 $($venv.Python)"
            }

            $newRaw = & $venv.Python --version 2>$null
            $newVer = Get-PythonSemVerFromText -Text $newRaw
            Write-Ok "虚拟环境已重建：.venv (Python $newVer)"
            return
        }

        Write-Ok "虚拟环境已存在：.venv (Python $currentVer)"
        Write-Warn "已忽略 -Python '$PythonSelector' 的版本校验（非版本号选择器）。如需切换解释器，请先删除 .venv 后重建。"
        return
    }

    Ensure-Uv

    # 清理旧的 legacy venv（不带点）
    $legacyVenv = Join-Path $ProjectRoot "venv"
    if (Test-Path $legacyVenv) {
        Write-Warn "检测到旧虚拟环境目录 venv，将删除（推荐迁移到 .venv）"
        Remove-Item -Path $legacyVenv -Recurse -Force
    }

    Write-Info "创建虚拟环境：.venv"
    $uvArgs = @("venv", ".venv")
    if ($PythonSelector) {
        $uvArgs += @("--python", $PythonSelector)
        Write-Debug "指定 Python：$PythonSelector"
    }

    Write-Debug ("执行命令：uv " + ($uvArgs -join " "))
    & uv @uvArgs | Out-Host
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境创建失败：未找到 $($venv.Python)"
    }

    $createdRaw = & $venv.Python --version 2>$null
    $createdVer = Get-PythonSemVerFromText -Text $createdRaw
    Write-Ok "虚拟环境创建完成：.venv (Python $createdVer)"
}

function Invoke-UvPipInstall {
    param(
        [string]$RequirementsFile,
        [string]$TorchBackendValue,
        [string]$DefaultIndexValue,
        [string]$IndexStrategyValue
    )

    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请先运行：.\\scripts\\vwr.ps1 setup"
    }

    if (-not (Test-Path $RequirementsFile)) {
        throw "依赖文件不存在：$RequirementsFile"
    }

    Ensure-Uv

    $uvArgs = @("pip", "install", "--python", $venv.Python, "-r", $RequirementsFile)
    if ($TorchBackendValue) { $uvArgs += @("--torch-backend", $TorchBackendValue) }
    $effectiveDefaultIndex = Resolve-UvDefaultIndex -UserValue $DefaultIndexValue -UserProvided:$script:DefaultIndexIsBound
    if ($effectiveDefaultIndex) {
        if (-not $DefaultIndexValue) {
            Write-Info "默认索引：$effectiveDefaultIndex（可用 -DefaultIndex 覆盖）"
        }
        $uvArgs += @("--default-index", $effectiveDefaultIndex)
    }
    if ($IndexStrategyValue) { $uvArgs += @("--index-strategy", $IndexStrategyValue) }

    $cacheDir = Resolve-UvCacheDir
    if ($cacheDir) {
        $uvArgs += @("--cache-dir", $cacheDir)
        Write-Debug "uv 缓存目录：$cacheDir"
    }

    Write-Info "开始安装依赖（uv）..."
    Write-Debug ("执行命令：uv " + ($uvArgs -join " "))
    & uv @uvArgs | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "依赖安装失败（退出码：$LASTEXITCODE）。可尝试：-TorchBackend cpu 或设置 -DefaultIndex 镜像。"
    }

    Write-Ok "依赖安装完成"
}

function Install-EditableProject {
    param([switch]$NoDeps)

    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请先运行：.\\scripts\\vwr.ps1 setup"
    }

    Ensure-Uv

    $uvArgs = @("pip", "install", "--python", $venv.Python, "-e", ".")
    if ($NoDeps) {
        $uvArgs += "--no-deps"
    }

    Write-Info "开始安装当前项目（editable）..."
    Write-Debug ("执行命令：uv " + ($uvArgs -join " "))
    & uv @uvArgs | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "当前项目 editable 安装失败（退出码：$LASTEXITCODE）。"
    }

    Write-Ok "当前项目已安装为 editable"
}

function Assert-ProjectImportable {
    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请先运行：.\\scripts\\vwr.ps1 setup"
    }

    $appPath = (& $venv.Python -c "import app; import main; print(app.__file__)" 2>$null | Select-Object -Last 1)
    if ($LASTEXITCODE -ne 0 -or -not $appPath) {
        throw "项目导入验证失败：无法导入 app/main。请重新运行：.\\scripts\\vwr.ps1 setup"
    }

    return $appPath.Trim()
}

function Assert-DevTools {
    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请先运行：.\\scripts\\vwr.ps1 setup -Dev"
    }

    $check = & $venv.Python -m pytest --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "未检测到 pytest（开发依赖）。请先运行：.\\scripts\\vwr.ps1 setup -Dev"
    }
}

function Show-Help {
    Write-Host "🎛️ 智能视频水印去除工具 - 统一脚本入口 (vwr.ps1)" -ForegroundColor Green
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host ""
    Write-Host "用法：" -ForegroundColor Cyan
    Write-Host "  .\\scripts\\vwr.ps1 <command> [args] [options]" -ForegroundColor White
    Write-Host ""
    Write-Host "命令：" -ForegroundColor Cyan
    Write-Host "  setup     创建 .venv 并安装依赖（-Dev 安装开发依赖）" -ForegroundColor White
    Write-Host "  run       环境检查后启动 main.py（-AutoFix 自动修复）" -ForegroundColor White
    Write-Host "  quality   代码质量检查（black/flake8/mypy/bandit）" -ForegroundColor White
    Write-Host "  test      运行测试（pytest + 可选 PowerShell 测试脚本）" -ForegroundColor White
    Write-Host "  coverage  覆盖率报告（pytest-cov）" -ForegroundColor White
    Write-Host "  perf      性能基准测试（JSON 报告）" -ForegroundColor White
    Write-Host "  build     PyInstaller 打包（release/）" -ForegroundColor White
    Write-Host "  clean     清理缓存（-Force 跳过确认）" -ForegroundColor White
    Write-Host "  ci        CI 模式（JSON 输出）" -ForegroundColor White
    Write-Host ""
}

function Invoke-Setup {
    Write-Section "环境配置 (setup)"
    Ensure-Venv -PythonSelector $Python

    $requirementsFile = if ($Dev) { "requirements-dev.txt" } else { "requirements.txt" }
    Write-Info "依赖清单：$requirementsFile"

    Invoke-UvPipInstall -RequirementsFile $requirementsFile -TorchBackendValue $TorchBackend -DefaultIndexValue $DefaultIndex -IndexStrategyValue $IndexStrategy
    Install-EditableProject -NoDeps
    $appPath = Assert-ProjectImportable

    $venv = Get-VenvInfo
    $pyVer = & $venv.Python --version 2>&1
    Write-Ok "Python：$pyVer"
    Write-Ok "导入验证：$appPath"
    Write-Ok "完成：可运行 .\\scripts\\vwr.ps1 run"
}

function Test-KeyPackages {
    param([switch]$FixIfMissing)

    $venv = Get-VenvInfo
    $requirementsFile = Join-Path $ProjectRoot "requirements.txt"

    if (-not (Test-Path $requirementsFile)) {
        Write-Warn "未找到 requirements.txt，跳过依赖检查"
        return $true
    }

    Ensure-Uv

    $keyPackages = @("PyQt6", "opencv-python", "numpy", "Pillow", "torch", "ultralytics")
    $missing = @()

    foreach ($pkg in $keyPackages) {
        & uv pip show --python $venv.Python $pkg *> $null
        if ($LASTEXITCODE -ne 0) {
            $missing += $pkg
        }
    }

    if ($missing.Count -eq 0) {
        Write-Ok "关键依赖检查通过（$($keyPackages.Count) 项）"
        return $true
    }

    Write-Warn ("缺失关键依赖：" + ($missing -join ", "))
    Write-Info "建议修复：.\\scripts\\vwr.ps1 setup"

    if ($FixIfMissing) {
        Write-Info "AutoFix：尝试自动安装 requirements.txt ..."
        Invoke-UvPipInstall -RequirementsFile "requirements.txt" -TorchBackendValue $TorchBackend -DefaultIndexValue $DefaultIndex -IndexStrategyValue $IndexStrategy

        foreach ($pkg in $missing) {
            & uv pip show --python $venv.Python $pkg *> $null
            if ($LASTEXITCODE -ne 0) {
                Write-Err "自动修复后仍缺失：$pkg"
                return $false
            }
        }
        Write-Ok "AutoFix：依赖已修复"
        return $true
    }

    return $false
}

function Invoke-Run {
    Initialize-Log
    Write-Section "启动应用 (run)"

    Ensure-Uv
    $venv = Get-VenvInfo

    if (-not (Test-Path $venv.Python)) {
        if ($AutoFix) {
            Write-Warn "虚拟环境不存在，AutoFix 将执行 setup..."
            Invoke-Setup
        } else {
            throw "虚拟环境不存在，请先运行：.\\scripts\\vwr.ps1 setup"
        }
    }

    if (-not $SkipChecks) {
        Write-Section "环境检查"

        $pyVer = & $venv.Python --version 2>&1
        Write-Info "Python：$pyVer"

        $depsOk = Test-KeyPackages -FixIfMissing:$AutoFix
        if (-not $depsOk) {
            throw "依赖检查未通过"
        }

        # FFmpeg
        if (Test-CommandExists "ffmpeg") {
            $ff = & ffmpeg -version 2>$null | Select-Object -First 1
            Write-Ok "FFmpeg：$ff"
        } else {
            Write-Warn "未检测到 FFmpeg（音频保留功能需要）。请安装后确保 ffmpeg 在 PATH 中。"
        }

        # 配置文件（与 ConfigManager 默认路径保持一致）
        $configExample = Join-Path $ProjectRoot "config.ini.example"
        $configIni = $null

        try {
            $configIni = (& $venv.Python -c "from app.config.config_manager import ConfigManager; print(ConfigManager.get_config_path())" 2>$null | Select-Object -First 1).Trim()
        } catch {
            $configIni = $null
        }

        if (-not $configIni) {
            # 兜底：按 app/config/config_manager.py 的 Windows fallback 规则构造
            $fallbackDir = Join-Path $env:USERPROFILE "AppData/Local/YourOrg/VideoWatermarkRemover"
            $configIni = Join-Path $fallbackDir "config.ini"
        }

        $configDir = Split-Path -Parent $configIni
        if ($configDir -and -not (Test-Path $configDir)) {
            New-Item -ItemType Directory -Path $configDir -Force | Out-Null
        }

        if (-not (Test-Path $configIni)) {
            if ((Test-Path $configExample) -and $AutoFix) {
                Copy-Item -Path $configExample -Destination $configIni -Force
                Write-Ok "AutoFix：已从 config.ini.example 生成配置文件：$configIni"
            } else {
                Write-Warn "未找到配置文件：$configIni（可从 config.ini.example 复制生成）"
            }
        } else {
            Write-Ok "配置文件：$configIni"
        }
    } else {
        Write-Warn "已跳过环境检查（-SkipChecks）"
    }

    Write-Section "运行 main.py"

    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONPATH = (Get-Location).Path

    $mainPy = Join-Path $ProjectRoot "main.py"
    if (-not (Test-Path $mainPy)) {
        throw "未找到 main.py：$mainPy"
    }

    Write-Info "项目路径：$ProjectRoot"
    Write-Info "日志文件：$Global:VwrLogFile"
    Write-Info "启动命令：$($venv.Python) $mainPy"
    Write-Host ""

    & $venv.Python $mainPy
    exit $LASTEXITCODE
}

function Invoke-Quality {
    Write-Section "代码质量检查 (quality)"
    Assert-DevTools

    $venv = Get-VenvInfo

    $targets = @()
    if (Test-Path "app") { $targets += "app" }
    if (Test-Path "main.py") { $targets += "main.py" }
    if (Test-Path "tests") { $targets += "tests" }

    if ($targets.Count -eq 0) {
        throw "未找到需要检查的目标（app/main.py/tests）"
    }

    $failed = $false

    if ($Check -eq "all" -or $Check -eq "format") {
        Write-Info "Black：$(if($Fix){'格式化'}else{'检查'})"
        $blackArgs = @()
        if (-not $Fix) {
            $blackArgs += @("--check", "--diff")
        }
        if (Is-VerboseEnabled) {
            $blackArgs += "--verbose"
        }
        $blackArgs += $targets

        & $venv.Python -m black @blackArgs | Out-Host
        if ($LASTEXITCODE -ne 0) {
            $failed = $true
            Write-Err "Black 未通过"
            if (-not $Fix) {
                Write-Info "可运行：.\\scripts\\vwr.ps1 quality -Fix"
            }
        } else {
            Write-Ok "Black 通过"
        }
    }

    if ($Check -eq "all" -or $Check -eq "style") {
        Write-Info "Flake8：检查"
        $flakeArgs = @()
        $flakeArgs += $targets
        if ($Quick) {
            $flakeArgs += @("--select=E9,F63,F7,F82")
        }

        & $venv.Python -m flake8 @flakeArgs | Out-Host
        if ($LASTEXITCODE -ne 0) {
            $failed = $true
            Write-Err "Flake8 未通过"
        } else {
            Write-Ok "Flake8 通过"
        }
    }

    if (-not $Quick -and ($Check -eq "all" -or $Check -eq "type")) {
        Write-Info "MyPy：检查"
        & $venv.Python -m mypy "app" "main.py" | Out-Host
        if ($LASTEXITCODE -ne 0) {
            $failed = $true
            Write-Err "MyPy 未通过"
        } else {
            Write-Ok "MyPy 通过"
        }
    } elseif ($Quick -and ($Check -eq "all" -or $Check -eq "type")) {
        Write-Warn "Quick 模式：跳过 MyPy"
    }

    if (-not $Quick -and ($Check -eq "all" -or $Check -eq "security")) {
        Write-Info "Bandit：安全检查"
        & $venv.Python -m bandit -r "app" "main.py" | Out-Host
        if ($LASTEXITCODE -ne 0) {
            $failed = $true
            Write-Err "Bandit 未通过"
        } else {
            Write-Ok "Bandit 通过"
        }
    } elseif ($Quick -and ($Check -eq "all" -or $Check -eq "security")) {
        Write-Warn "Quick 模式：跳过安全检查"
    }

    if ($failed) {
        throw "代码质量检查未通过"
    }

    Write-Ok "代码质量检查完成"
}

function Save-SimpleJsonReport {
    param(
        [string]$Prefix,
        [hashtable]$Data
    )

    if (-not $Report) {
        return
    }

    $logsDir = Join-Path $ProjectRoot "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }

    $path = Join-Path $logsDir ("{0}_{1}.json" -f $Prefix, (Get-Date -Format "yyyyMMdd_HHmmss"))
    ($Data | ConvertTo-Json -Depth 6) | Out-File -FilePath $path -Encoding UTF8
    Write-Ok "报告已保存：$path"
}

function Invoke-Pytest {
    param([string[]]$PytestArgs)

    Assert-DevTools
    $venv = Get-VenvInfo

    # 先做一次关键依赖探测，避免 pytest 在收集阶段抛出难以理解的 ImportError
    $depsOk = Test-KeyPackages
    if (-not $depsOk) {
        Write-Err "关键依赖未安装或不完整，无法运行 pytest。请先运行：.\\scripts\\vwr.ps1 setup -Dev（可加 -TorchBackend cpu / -DefaultIndex 镜像提速）"
        return 2
    }

    $finalArgs = @()
    $finalArgs += $PytestArgs
    $finalArgs += "--color=yes"

    Write-Debug ("pytest 参数：" + ($finalArgs -join " "))
    & $venv.Python -m pytest @finalArgs | Out-Host
    return $LASTEXITCODE
}

function Invoke-PowerShellScriptFile {
    param(
        [string]$ScriptPath,
        [string[]]$ScriptArgs = @()
    )

    if (-not (Test-Path $ScriptPath)) {
        throw "脚本不存在：$ScriptPath"
    }

    $psExe = "powershell.exe"
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) + $ScriptArgs

    Write-Debug ("执行 PowerShell 子进程：" + ($argList -join " "))
    $proc = Start-Process -FilePath $psExe -ArgumentList $argList -Wait -PassThru -NoNewWindow
    return $proc.ExitCode
}

function Invoke-Test {
    Write-Section "测试执行 (test)"

    $type = if ($Arg1) { $Arg1 } else { "all" }
    $type = $type.ToLowerInvariant()

    $validTypes = @("unit", "integration", "quality", "audio", "e2e", "preferences", "all")
    if ($validTypes -notcontains $type) {
        throw "未知测试类型：$type。可选：$($validTypes -join ', ')"
    }

    $start = Get-Date
    $reportData = @{
        Command = "test"
        Type = $type
        Quick = [bool]$Quick
        Coverage = [bool]$Coverage
        Performance = [bool]$Performance
        StartTime = $start
        Results = @{}
    }

    if ($type -eq "quality") {
        Invoke-Quality
        $reportData.Results.quality = @{ exitCode = 0 }
        Save-SimpleJsonReport -Prefix "test_report" -Data $reportData
        return
    }

    $exitCode = 0

    if ($type -eq "unit") {
        $pytestArgs = @("tests/unit", "-v")
        if ($Quick) { $pytestArgs += @("-m", "not slow") }
        $exitCode = Invoke-Pytest -PytestArgs $pytestArgs
        $reportData.Results.unit = @{ exitCode = $exitCode }
    } elseif ($type -eq "integration") {
        $pytestArgs = @("tests/integration", "-v")
        if ($Quick) { $pytestArgs += @("-m", "not slow") }
        $exitCode = Invoke-Pytest -PytestArgs $pytestArgs
        if ($exitCode -eq 5) {
            Write-Warn "未收集到任何集成测试（pytest 退出码 5）。请确认依赖已安装，或检查 tests/integration 下是否存在 test_*.py。"
            $exitCode = 0
        }
        $reportData.Results.integration = @{ exitCode = $exitCode }
    } elseif ($type -eq "all") {
        $pytestArgs = @("tests", "-v")
        if ($Quick) { $pytestArgs += @("-m", "not slow") }
        $exitCode = Invoke-Pytest -PytestArgs $pytestArgs
        $reportData.Results.pytest = @{ exitCode = $exitCode }

        if (-not $Quick) {
            $psArgs = @()
            if (Is-VerboseEnabled) { $psArgs += "-Verbose" }
            if ($Quick) { $psArgs += "-Quick" }

            foreach ($psTest in @(
                    @{ name = "audio"; path = "tests/e2e/ps1/test_audio_processing.ps1" },
                    @{ name = "preferences"; path = "tests/e2e/ps1/test_user_preferences.ps1" },
                    @{ name = "e2e"; path = "tests/e2e/ps1/test_end_to_end.ps1" }
                )) {
                if (Test-Path $psTest.path) {
                    Write-Info "运行 PowerShell 测试：$($psTest.path)"
                    $code = Invoke-PowerShellScriptFile -ScriptPath $psTest.path -ScriptArgs $psArgs
                    $reportData.Results[$psTest.name] = @{ exitCode = $code }
                    if ($code -ne 0) {
                        $exitCode = $code
                    }
                } else {
                    Write-Warn "未找到 PowerShell 测试脚本：$($psTest.path)"
                }
            }
        } else {
            Write-Warn "Quick 模式：跳过 PowerShell 端到端/音频/偏好测试"
        }
    } elseif ($type -in @("audio", "preferences", "e2e")) {
        $scriptPath = switch ($type) {
            "audio" { "tests/e2e/ps1/test_audio_processing.ps1" }
            "preferences" { "tests/e2e/ps1/test_user_preferences.ps1" }
            "e2e" { "tests/e2e/ps1/test_end_to_end.ps1" }
        }

        $psArgs = @()
        if (Is-VerboseEnabled) { $psArgs += "-Verbose" }
        if ($Quick) { $psArgs += "-Quick" }

        Write-Info "运行 PowerShell 测试：$scriptPath"
        $exitCode = Invoke-PowerShellScriptFile -ScriptPath $scriptPath -ScriptArgs $psArgs
        $reportData.Results[$type] = @{ exitCode = $exitCode }
    }

    if ($Coverage) {
        try {
            Invoke-Coverage
            $reportData.Results.coverage = @{ exitCode = 0 }
        } catch {
            $reportData.Results.coverage = @{ exitCode = 1; error = $_.Exception.Message }
            $exitCode = 1
        }
    }

    if ($Performance) {
        try {
            Invoke-Perf
            $reportData.Results.performance = @{ exitCode = 0 }
        } catch {
            $reportData.Results.performance = @{ exitCode = 1; error = $_.Exception.Message }
            $exitCode = 1
        }
    }

    $end = Get-Date
    $reportData.EndTime = $end
    $reportData.DurationSeconds = ($end - $start).TotalSeconds
    $reportData.ExitCode = $exitCode

    Save-SimpleJsonReport -Prefix "test_report" -Data $reportData

    if ($exitCode -ne 0) {
        throw "测试失败（退出码：$exitCode）"
    }

    Write-Ok "测试完成"
}

function Invoke-Coverage {
    Write-Section "覆盖率分析 (coverage)"
    Assert-DevTools

    $logsDir = Join-Path $ProjectRoot "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }

    $covHtmlDir = Join-Path $logsDir "htmlcov"
    if (Test-Path $covHtmlDir) {
        Remove-Item -Path $covHtmlDir -Recurse -Force
    }

    $pytestArgs = @(
        "tests",
        "-v",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:$covHtmlDir"
    )
    if ($Quick) {
        $pytestArgs += @("-m", "not slow", "-x")
    }
    if ($FailOnLow) {
        $pytestArgs += "--cov-fail-under=$MinCoverage"
    }

    $exitCode = Invoke-Pytest -PytestArgs $pytestArgs
    if ($exitCode -ne 0) {
        if ($FailOnLow) {
            throw "覆盖率未达标或测试失败（退出码：$exitCode）"
        }
        Write-Warn "覆盖率测试存在失败（退出码：$exitCode），但已尝试生成报告"
    }

    $indexHtml = Join-Path $covHtmlDir "index.html"
    if (Test-Path $indexHtml) {
        Write-Ok "覆盖率报告：$indexHtml"
        if ($OpenReport) {
            Start-Process $indexHtml | Out-Null
            Write-Info "已打开覆盖率报告"
        }
    } else {
        Write-Warn "未找到 HTML 覆盖率报告（可能未安装 pytest-cov 或运行失败）"
    }
}

function Invoke-Perf {
    Write-Section "性能基准测试 (perf)"

    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请先运行：.\\scripts\\vwr.ps1 setup"
    }

    $logsDir = Join-Path $ProjectRoot "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }

    $reportPath = $PerfReportPath
    if (-not $reportPath) {
        $reportPath = Join-Path $logsDir ("performance_report_{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
    }

    $pyCode = @"
import json
import platform
import sys
import time
from pathlib import Path

def cpu_task(n: int) -> int:
    total = 0
    for i in range(n):
        total += (i * i) % 97
    return total

def main() -> int:
    report_path = Path(sys.argv[1])
    iterations = int(sys.argv[2])
    quick = sys.argv[3] == "1"
    gpu_profile = sys.argv[4] == "1"
    memory_profile = sys.argv[5] == "1"

    report_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()

    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": {
            "iterations": iterations,
            "quick": quick,
            "gpu_profile": gpu_profile,
            "memory_profile": memory_profile,
        },
        "system": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "benchmarks": {},
        "gpu": {},
        "memory": {},
    }

    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        data["system"].update({
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "memory_total": vm.total,
            "memory_available": vm.available,
        })
    except Exception as e:
        data["system"]["psutil_error"] = str(e)

    n = 600_000 if quick else 2_000_000
    durations = []
    for _ in range(max(1, iterations)):
        t0 = time.time()
        cpu_task(n)
        durations.append(time.time() - t0)
    data["benchmarks"]["cpu_task"] = {
        "n": n,
        "iterations": len(durations),
        "avg_seconds": sum(durations) / len(durations),
        "min_seconds": min(durations),
        "max_seconds": max(durations),
    }

    if gpu_profile:
        try:
            import torch  # type: ignore
            data["gpu"]["torch_version"] = getattr(torch, "__version__", None)
            data["gpu"]["cuda_available"] = bool(torch.cuda.is_available())
            if torch.cuda.is_available():
                data["gpu"]["device_count"] = int(torch.cuda.device_count())
                data["gpu"]["device_name"] = torch.cuda.get_device_name(0)
        except Exception as e:
            data["gpu"]["error"] = str(e)

    if memory_profile:
        try:
            import os
            import psutil  # type: ignore
            p = psutil.Process(os.getpid())
            data["memory"]["rss"] = int(p.memory_info().rss)
        except Exception as e:
            data["memory"]["error"] = str(e)

    data["duration_seconds"] = time.time() - start
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(str(report_path))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"@

    $quickFlag = if ($Quick) { "1" } else { "0" }
    $gpuFlag = if ($GPUProfile) { "1" } else { "0" }
    $memFlag = if ($MemoryProfile) { "1" } else { "0" }

    Write-Info "生成报告：$reportPath"
    & $venv.Python -c $pyCode $reportPath $Iterations $quickFlag $gpuFlag $memFlag | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "性能测试失败（退出码：$LASTEXITCODE）"
    }

    Write-Ok "性能报告已生成"
}

function Invoke-Build {
    Write-Section "构建发布 (build)"

    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请先运行：.\\scripts\\vwr.ps1 setup -Dev"
    }

    Ensure-Uv

    Write-Info "确保 PyInstaller 已安装..."
    & uv pip install --python $venv.Python "PyInstaller>=5.0.0" | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "安装 PyInstaller 失败（退出码：$LASTEXITCODE）"
    }

    if (-not $SkipTests) {
        Write-Info "构建前测试：$(if($Quick){'unit+Quick'}else{'unit'})"
        $pytestArgs = @("tests/unit", "-v")
        if ($Quick) { $pytestArgs += @("-m", "not slow") }
        $code = Invoke-Pytest -PytestArgs $pytestArgs
        if ($code -ne 0) {
            throw "构建前测试失败（退出码：$code）。可使用 -SkipTests 跳过。"
        }
    } else {
        Write-Warn "已跳过构建前测试（-SkipTests）"
    }

    foreach ($p in @("build", "dist", "release")) {
        if (Test-Path $p) {
            Remove-Item -Path $p -Recurse -Force
        }
    }
    Get-ChildItem -Path $ProjectRoot -Filter "*.spec" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

    $iconPath = Join-Path $ProjectRoot "app/assets/icons/app.ico"
    $pyInstallerArgs = @(
        "--onefile",
        "--windowed",
        "--name=智能水印去除工具",
        "--add-data=app;app",
        "--add-data=models;models",
        "--hidden-import=PyQt6",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "main.py"
    )
    if (Test-Path $iconPath) {
        $pyInstallerArgs = @("--icon=$iconPath") + $pyInstallerArgs
    } else {
        Write-Warn "未找到图标文件：$iconPath（将使用默认图标）"
    }

    Write-Info "开始打包（PyInstaller）..."
    & $venv.Python -m PyInstaller @pyInstallerArgs | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 打包失败（退出码：$LASTEXITCODE）"
    }

    New-Item -ItemType Directory -Path "release" -Force | Out-Null
    Copy-Item -Path "dist/*" -Destination "release" -Recurse -Force
    if (Test-Path "README.md") { Copy-Item -Path "README.md" -Destination "release" -Force }
    if (Test-Path "requirements.txt") { Copy-Item -Path "requirements.txt" -Destination "release" -Force }

    $versionInfo = @"
智能视频水印去除工具
构建时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Python版本: $(& $venv.Python --version 2>&1)
构建环境: uv + .venv
操作系统: Windows PowerShell
"@
    $versionInfo | Out-File -FilePath "release/VERSION.txt" -Encoding UTF8

    Write-Ok "构建完成：release/ 目录"
}

function Invoke-Clean {
    Write-Section "缓存清理 (clean)"

    $targets = @(
        @{ type = "dir"; path = ".mypy_cache" },
        @{ type = "dir"; path = ".pytest_cache" },
        @{ type = "file"; path = ".coverage" },
        @{ type = "glob"; path = ".coverage.*" },
        @{ type = "glob"; path = "logs/*.log" }
    )

    Write-Info "将清理以下内容："
    foreach ($t in $targets) {
        Write-Host ("  - " + $t.path) -ForegroundColor White
    }
    Write-Host "  - 递归清理：__pycache__、*.pyc、*.pyo（仅 app/tests 目录）" -ForegroundColor White

    if (-not $Force) {
        $ans = Read-Host "是否继续清理？(y/N)"
        if ($ans -ne "y" -and $ans -ne "Y") {
            Write-Warn "已取消清理"
            return
        }
    }

    foreach ($t in $targets) {
        try {
            if ($t.type -eq "dir" -and (Test-Path $t.path)) {
                Remove-Item -Path $t.path -Recurse -Force
            } elseif ($t.type -eq "file" -and (Test-Path $t.path)) {
                Remove-Item -Path $t.path -Force
            } elseif ($t.type -eq "glob") {
                Get-ChildItem -Path $ProjectRoot -Filter $t.path -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Warn "清理失败：$($t.path) - $($_.Exception.Message)"
        }
    }

    foreach ($scope in @("app", "tests")) {
        if (Test-Path $scope) {
            Get-ChildItem -Path $scope -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
                Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }
            Get-ChildItem -Path $scope -Recurse -File -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue | ForEach-Object {
                Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
            }
        }
    }

    Write-Ok "清理完成"
}

function Invoke-CI {
    Initialize-Log
    Write-Section "CI 模式 (ci)"

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)

    $results = @{
        Timestamp = Get-Date
        Success = $false
        Steps = @()
        Params = @{
            Quick = [bool]$Quick
            SkipCoverage = [bool]$SkipCoverage
            SkipPerformance = [bool]$SkipPerformance
            MinCoverage = $MinCoverage
        }
    }

    function Add-StepResult {
        param(
            [string]$Name,
            [bool]$Passed,
            [string]$Details = ""
        )

        $results.Steps += @{
            Name = $Name
            Passed = $Passed
            Details = $Details
            Timestamp = Get-Date
        }
    }

    $overallOk = $true

    if ((Get-Date) -gt $deadline) { throw "CI 超时" }
    try {
        Invoke-Quality
        Add-StepResult -Name "quality" -Passed $true
    } catch {
        $overallOk = $false
        Add-StepResult -Name "quality" -Passed $false -Details $_.Exception.Message
    }

    if ((Get-Date) -gt $deadline) { throw "CI 超时" }
    try {
        $pytestArgs = @("tests/unit", "-v")
        if ($Quick) { $pytestArgs += @("-m", "not slow") }
        $code = Invoke-Pytest -PytestArgs $pytestArgs
        if ($code -ne 0) { throw "pytest 失败（退出码：$code）" }
        Add-StepResult -Name "unit" -Passed $true
    } catch {
        $overallOk = $false
        Add-StepResult -Name "unit" -Passed $false -Details $_.Exception.Message
    }

    if (-not $SkipCoverage) {
        if ((Get-Date) -gt $deadline) { throw "CI 超时" }
        $oldFailOnLow = $FailOnLow
        $script:FailOnLow = $true
        try {
            Invoke-Coverage
            Add-StepResult -Name "coverage" -Passed $true
        } catch {
            $overallOk = $false
            Add-StepResult -Name "coverage" -Passed $false -Details $_.Exception.Message
        } finally {
            $script:FailOnLow = $oldFailOnLow
        }
    } else {
        Add-StepResult -Name "coverage" -Passed $true -Details "skipped"
    }

    if (-not $SkipPerformance) {
        if ((Get-Date) -gt $deadline) { throw "CI 超时" }
        try {
            Invoke-Perf
            Add-StepResult -Name "perf" -Passed $true
        } catch {
            $overallOk = $false
            Add-StepResult -Name "perf" -Passed $false -Details $_.Exception.Message
        }
    } else {
        Add-StepResult -Name "perf" -Passed $true -Details "skipped"
    }

    $results.Success = $overallOk

    $out = $OutputFile
    if (-not $out) {
        $out = Join-Path $ArtifactsDir "ci-results.json"
    }

    $outDir = Split-Path -Parent $out
    if ($outDir -and (-not (Test-Path $outDir))) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    ($results | ConvertTo-Json -Depth 8) | Out-File -FilePath $out -Encoding UTF8
    Write-Ok "CI 结果已写入：$out"

    try {
        if (-not (Test-Path $ArtifactsDir)) {
            New-Item -ItemType Directory -Path $ArtifactsDir -Force | Out-Null
        }
        if (Test-Path "logs") {
            Copy-Item -Path "logs" -Destination (Join-Path $ArtifactsDir "logs") -Recurse -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Warn "收集制品失败：$($_.Exception.Message)"
    }

    if (-not $overallOk) {
        throw "CI 未通过"
    }
}

try {
    switch ($Command) {
        "help" { Show-Help; exit 0 }
        "setup" { Invoke-Setup; exit 0 }
        "run" { Invoke-Run; exit 0 }
        "quality" { Invoke-Quality; exit 0 }
        "test" { Invoke-Test; exit 0 }
        "coverage" { Invoke-Coverage; exit 0 }
        "perf" { Invoke-Perf; exit 0 }
        "build" { Invoke-Build; exit 0 }
        "clean" { Invoke-Clean; exit 0 }
        "ci" { Invoke-CI; exit 0 }
        default { throw "未知命令：$Command" }
    }
} catch {
    Write-Host "[✗] $($_.Exception.Message)" -ForegroundColor Red
    if (Is-VerboseEnabled) { Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray }
    exit 1
}
