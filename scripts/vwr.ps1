#!/usr/bin/env powershell
# ============================================================
# 智能视频水印去除工具 - 统一脚本入口（Windows PowerShell）
# ============================================================
# 目标：
# - 将 scripts/ 目录脚本整合为单一交互式入口，降低维护成本
# - 通过菜单提供 setup/run/test/quality/coverage/perf/build/clean/ci 等常用操作
#
# 用法：
#   直接运行：.\scripts\vwr.ps1
#   在菜单中选择：环境初始化 / 启动程序 / 运行测试 / 清理缓存与临时文件
# ============================================================

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$LegacyArgs = @()
)

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Global:VwrLogFile = $null
$script:Arg1 = ""
$script:Arg2 = ""
$script:Quick = $false
$script:Dev = $false
$script:Python = "3.12.10"
$script:TorchBackend = "auto"
$script:DefaultIndex = ""
$script:IndexStrategy = "first-index"
$script:AutoFix = $false
$script:SkipChecks = $false
$script:Fix = $false
$script:Check = "all"
$script:Coverage = $false
$script:Performance = $false
$script:Report = $false
$script:MinCoverage = 80.0
$script:FailOnLow = $false
$script:OpenReport = $false
$script:Iterations = 5
$script:MemoryProfile = $false
$script:GPUProfile = $false
$script:PerfReportPath = ""
$script:SkipTests = $false
$script:Force = $false
$script:SkipPerformance = $false
$script:SkipCoverage = $false
$script:OutputFile = ""
$script:ArtifactsDir = "ci-artifacts"
$script:TimeoutMinutes = 30
$script:CleanScope = "all"
$script:DefaultIndexIsBound = $false
$script:UvExecutablePath = $null

function Reset-ExecutionOptions {
    $script:Arg1 = ""
    $script:Arg2 = ""
    $script:Quick = $false
    $script:Dev = $false
    $script:Python = "3.12.10"
    $script:TorchBackend = "auto"
    $script:DefaultIndex = ""
    $script:IndexStrategy = "first-index"
    $script:AutoFix = $false
    $script:SkipChecks = $false
    $script:Fix = $false
    $script:Check = "all"
    $script:Coverage = $false
    $script:Performance = $false
    $script:Report = $false
    $script:MinCoverage = 80.0
    $script:FailOnLow = $false
    $script:OpenReport = $false
    $script:Iterations = 5
    $script:MemoryProfile = $false
    $script:GPUProfile = $false
    $script:PerfReportPath = ""
    $script:SkipTests = $false
    $script:Force = $false
    $script:SkipPerformance = $false
    $script:SkipCoverage = $false
    $script:OutputFile = ""
    $script:ArtifactsDir = "ci-artifacts"
    $script:TimeoutMinutes = 30
    $script:CleanScope = "all"
    $script:DefaultIndex = ""
    $script:DefaultIndexIsBound = $false
}

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

function Resolve-UvExecutablePath {
    # 重要：不要用 `Get-Command uv` 的默认行为，因为它可能命中用户在 Profile 里定义的 alias/function。
    # 这里显式只接受可执行命令（Application / ExternalScript），确保不会走到被包装的 `uv` 函数，
    # 从而避免被注入坏参数（例如 `--cache-dir` 空值）。
    $commands = @(Get-Command "uv" -All -ErrorAction SilentlyContinue)
    foreach ($command in $commands) {
        $commandType = [string]$command.CommandType
        if ($commandType -notin @("Application", "ExternalScript")) {
            continue
        }

        foreach ($path in @($command.Source, $command.Definition)) {
            if ($path -and ([string]$path).Trim()) {
                return ([string]$path).Trim()
            }
        }
    }
    return $null
}

function Get-UvExecutablePath {
    if ($script:UvExecutablePath -and (Test-Path $script:UvExecutablePath)) {
        return $script:UvExecutablePath
    }

    $resolved = Resolve-UvExecutablePath
    if (-not $resolved) {
        Ensure-Uv
        $resolved = Resolve-UvExecutablePath
    }

    if (-not $resolved) {
        throw "未找到 uv 可执行文件。请确认已安装 uv 且 PATH 可用（例如：winget install --id=astral-sh.uv -e）。"
    }

    $script:UvExecutablePath = $resolved
    return $resolved
}

function Invoke-UvCommand {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Arguments)

    $uvExe = Get-UvExecutablePath
    & $uvExe @Arguments
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
    return (Join-Path $ProjectRoot ".cache/uv")
}

function Get-UvCacheArgs {
    $cacheDir = Resolve-UvCacheDir
    if ($cacheDir -is [array]) {
        $cacheDir = $cacheDir | Where-Object {
            $null -ne $_ -and ([string]$_).Trim()
        } | Select-Object -Last 1
    }

    $cacheDir = [string]$cacheDir
    if (-not $cacheDir -or -not $cacheDir.Trim()) {
        Write-Warn "未解析到有效的 uv 缓存目录，将使用 uv 默认缓存。"
        return @()
    }

    $cacheDir = $cacheDir.Trim()
    if (-not (Test-Path $cacheDir)) {
        New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
    }

    Write-Debug "uv 缓存目录：$cacheDir"

    # 兼容修复：部分 PowerShell Profile/环境脚本会把 UV_CACHE_DIR 设置为“空字符串”。
    # uv 在解析环境变量时会直接报：a value is required for '--cache-dir <CACHE_DIR>' but none was supplied。
    # 为避免这种“坏环境”导致脚本不可用，这里强制将进程级缓存目录写成有效路径。
    $env:UV_CACHE_DIR = $cacheDir
    $env:VWR_UV_CACHE_DIR = $cacheDir
    return @("--cache-dir=$cacheDir")
}

function Test-PythonDistributionInstalled {
    param(
        [string]$PythonPath,
        [string]$DistributionName
    )

    if (-not $PythonPath -or -not (Test-Path $PythonPath)) {
        return $false
    }

    $probeCode = @'
import importlib.metadata as metadata
import sys

distribution_name = sys.argv[1]
try:
    metadata.version(distribution_name)
except metadata.PackageNotFoundError:
    raise SystemExit(1)
except Exception:
    raise SystemExit(2)
raise SystemExit(0)
'@

    Write-Debug "执行命令：python -c <metadata probe> $DistributionName"
    & $PythonPath -c $probeCode $DistributionName *> $null
    Write-Debug "依赖探针结果：$DistributionName -> EXIT=$LASTEXITCODE"
    return ($LASTEXITCODE -eq 0)
}

function Get-VenvSitePackagesDir {
    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Root)) {
        throw "虚拟环境目录不存在：$($venv.Root)"
    }

    $windowsSitePackages = Join-Path $venv.Root "Lib/site-packages"
    if (Test-Path $windowsSitePackages) {
        return $windowsSitePackages
    }

    $posixLibRoot = Join-Path $venv.Root "lib"
    if (Test-Path $posixLibRoot) {
        $posixCandidates = Get-ChildItem -Path $posixLibRoot -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName "site-packages" } |
            Where-Object { Test-Path $_ }
        if ($posixCandidates.Count -gt 0) {
            return $posixCandidates[0]
        }
    }

    return $windowsSitePackages
}

function Test-IsEditablePermissionFailure {
    param([object[]]$CommandOutput)

    if (-not $CommandOutput -or $CommandOutput.Count -eq 0) {
        return $false
    }

    $joinedOutput = (($CommandOutput | ForEach-Object { [string]$_ }) -join "`n").ToLowerInvariant()
    $hasPermissionSignal = (
        $joinedOutput.Contains("permissionerror") -or
        $joinedOutput.Contains("winerror 5") -or
        $joinedOutput.Contains("拒绝访问")
    )
    if (-not $hasPermissionSignal) {
        return $false
    }

    return (
        $joinedOutput.Contains("build_editable") -or
        $joinedOutput.Contains("egg-info") -or
        $joinedOutput.Contains("temporarydirectory") -or
        $joinedOutput.Contains("tempfile")
    )
}

function Install-EditableProjectFallback {
    $srcDir = Resolve-ProjectSrcDir
    if (-not $srcDir) {
        throw "未找到 src/app/__init__.py，无法写入 editable fallback。"
    }

    $sitePackagesDir = Get-VenvSitePackagesDir
    if (-not (Test-Path $sitePackagesDir)) {
        New-Item -ItemType Directory -Path $sitePackagesDir -Force | Out-Null
    }

    $pthPath = Join-Path $sitePackagesDir "video_watermark_remover_local_editable.pth"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($pthPath, ($srcDir + [Environment]::NewLine), $utf8NoBom)
    return $pthPath
}

function Resolve-ProjectSrcDir {
    $srcDir = Join-Path $ProjectRoot "src"
    $appInit = Join-Path $srcDir "app/__init__.py"
    if ((Test-Path $srcDir) -and (Test-Path $appInit)) {
        return $srcDir
    }
    return ""
}

function Resolve-SetupDependencyStateDir {
    $stateDir = Join-Path $ProjectRoot ".cache/setup-state"
    if (-not (Test-Path $stateDir)) {
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    }
    return $stateDir
}

function Get-SetupDependencyStatePath {
    param(
        [ValidateSet("prod", "dev")]
        [string]$DependencySet
    )

    $fileName = if ($DependencySet -eq "dev") { "dev.json" } else { "prod.json" }
    return (Join-Path (Resolve-SetupDependencyStateDir) $fileName)
}

function Get-RequirementsSignature {
    param([string]$RequirementsFile)

    if (-not (Test-Path $RequirementsFile)) {
        throw "依赖文件不存在：$RequirementsFile"
    }

    $projectRootResolved = (Resolve-Path $ProjectRoot).Path
    $visited = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $sections = [System.Collections.Generic.List[string]]::new()

    $walk = {
        param([string]$TargetPath)

        $resolved = (Resolve-Path $TargetPath).Path
        if ($visited.Contains($resolved)) {
            return
        }
        $visited.Add($resolved) | Out-Null

        $content = Get-Content -LiteralPath $resolved -Raw -Encoding UTF8
        $relative = [System.IO.Path]::GetRelativePath($projectRootResolved, $resolved).Replace("\", "/")
        $sections.Add(("FILE:{0}`n{1}`n" -f $relative, $content)) | Out-Null

        foreach ($rawLine in ($content -split "`r?`n")) {
            $line = $rawLine.Trim()
            if (-not $line -or $line.StartsWith("#")) {
                continue
            }
            if ($line -match "^(?:-r|--requirement)\s+(.+)$") {
                $includePath = $Matches[1].Trim()
                $includeFullPath = Join-Path ([System.IO.Path]::GetDirectoryName($resolved)) $includePath
                & $walk $includeFullPath
            }
        }
    }

    & $walk $RequirementsFile

    $payload = [string]::Join("`n---`n", $sections)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
        $hashBytes = $sha256.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hashBytes)).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

function Read-SetupDependencyState {
    param(
        [ValidateSet("prod", "dev")]
        [string]$DependencySet
    )

    $statePath = Get-SetupDependencyStatePath -DependencySet $DependencySet
    if (-not (Test-Path $statePath)) {
        return $null
    }

    try {
        return (Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        Write-Warn "依赖状态文件读取失败：$statePath，原因：$($_.Exception.Message)"
        return $null
    }
}

function Write-SetupDependencyState {
    param(
        [string]$RequirementsFile,
        [ValidateSet("prod", "dev")]
        [string]$DependencySet
    )

    $venv = Get-VenvInfo
    $pythonVersion = ""
    if (Test-Path $venv.Python) {
        $pythonVersion = Get-PythonSemVerFromText -Text (& $venv.Python --version 2>$null)
    }

    $payload = [ordered]@{
        DependencySet = $DependencySet
        RequirementsFile = $RequirementsFile
        Signature = (Get-RequirementsSignature -RequirementsFile $RequirementsFile)
        PythonPath = $venv.Python
        PythonVersion = $pythonVersion
        UpdatedAt = (Get-Date).ToString("o")
    }

    $statePath = Get-SetupDependencyStatePath -DependencySet $DependencySet
    ($payload | ConvertTo-Json -Depth 5) | Out-File -LiteralPath $statePath -Encoding UTF8
    Write-Debug "已刷新依赖状态：$DependencySet -> $statePath"
}

function Get-SetupDependencyProbePackages {
    param(
        [ValidateSet("prod", "dev")]
        [string]$DependencySet
    )

    $packages = [ordered]@{}
    foreach ($packageName in @("PyQt6", "numpy", "Pillow", "torch")) {
        $packages[$packageName] = $true
    }

    if ($DependencySet -eq "dev") {
        foreach ($packageName in @("pytest", "black", "mypy")) {
            $packages[$packageName] = $true
        }
    }

    return @($packages.Keys)
}

function Test-SetupDependencyProbePackages {
    param([string[]]$PackageNames)

    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        return [pscustomobject]@{
            Passed = $false
            MissingPackages = @("python")
        }
    }

    $missingPackages = [System.Collections.Generic.List[string]]::new()
    foreach ($packageName in $PackageNames) {
        if (-not (Test-PythonDistributionInstalled -PythonPath $venv.Python -DistributionName $packageName)) {
            $missingPackages.Add($packageName) | Out-Null
        }
    }

    return [pscustomobject]@{
        Passed = ($missingPackages.Count -eq 0)
        MissingPackages = @($missingPackages)
    }
}

function Test-SetupDependencyState {
    param(
        [string]$RequirementsFile,
        [ValidateSet("prod", "dev")]
        [string]$DependencySet
    )

    $result = [ordered]@{
        Satisfied = $false
        Reason = "state_missing"
        MissingPackages = @()
    }

    if (-not (Test-Path $RequirementsFile)) {
        $result["Reason"] = "requirements_missing"
        return [pscustomobject]$result
    }

    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        $result["Reason"] = "venv_missing"
        return [pscustomobject]$result
    }

    $state = Read-SetupDependencyState -DependencySet $DependencySet
    if ($null -eq $state) {
        return [pscustomobject]$result
    }

    $currentSignature = Get-RequirementsSignature -RequirementsFile $RequirementsFile
    if (-not $state.Signature -or ($state.Signature -ne $currentSignature)) {
        $result["Reason"] = "signature_mismatch"
        return [pscustomobject]$result
    }

    if ($state.PythonPath -and ($state.PythonPath -ne $venv.Python)) {
        $result["Reason"] = "python_mismatch"
        return [pscustomobject]$result
    }

    $probePackages = Get-SetupDependencyProbePackages -DependencySet $DependencySet
    if ($probePackages.Count -gt 0) {
        $probeResult = Test-SetupDependencyProbePackages -PackageNames $probePackages
        if (-not $probeResult.Passed) {
            $result["Reason"] = "probe_missing"
            $result["MissingPackages"] = @($probeResult.MissingPackages)
            return [pscustomobject]$result
        }
    }

    $result["Satisfied"] = $true
    $result["Reason"] = "state_match"
    return [pscustomobject]$result
}

function New-RunScopedDirectory {
    param(
        [string]$BaseDir,
        [string]$Prefix
    )

    if (-not (Test-Path $BaseDir)) {
        New-Item -ItemType Directory -Path $BaseDir -Force | Out-Null
    }

    $dirName = "{0}-{1}-{2}" -f $Prefix, (Get-Date -Format "yyyyMMdd-HHmmss"), $PID
    $path = Join-Path $BaseDir $dirName
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
    return $path
}

function Use-ScopedProjectRuntimeEnv {
    param([switch]$ForPytest)

    $snapshot = @{}
    foreach ($name in @("PYTHONPATH", "UV_CACHE_DIR", "VWR_UV_CACHE_DIR", "TEMP", "TMP")) {
        $snapshot[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    }

    $srcDir = Resolve-ProjectSrcDir
    if ($srcDir) {
        $currentPyPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
        if (-not $currentPyPath) {
            [Environment]::SetEnvironmentVariable("PYTHONPATH", $srcDir, "Process")
        } else {
            $parts = $currentPyPath -split [IO.Path]::PathSeparator
            if ($parts -notcontains $srcDir) {
                [Environment]::SetEnvironmentVariable(
                    "PYTHONPATH",
                    ($srcDir + [IO.Path]::PathSeparator + $currentPyPath),
                    "Process"
                )
            }
        }
    }

    $uvCacheDir = Resolve-UvCacheDir
    if ($uvCacheDir) {
        if (-not (Test-Path $uvCacheDir)) {
            New-Item -ItemType Directory -Path $uvCacheDir -Force | Out-Null
        }
        [Environment]::SetEnvironmentVariable("UV_CACHE_DIR", $uvCacheDir, "Process")
        [Environment]::SetEnvironmentVariable("VWR_UV_CACHE_DIR", $uvCacheDir, "Process")
    }

    $tempRoot = Join-Path $ProjectRoot ".cache/tmp"
    $runTempDir = New-RunScopedDirectory -BaseDir $tempRoot -Prefix "run"
    [Environment]::SetEnvironmentVariable("TEMP", $runTempDir, "Process")
    [Environment]::SetEnvironmentVariable("TMP", $runTempDir, "Process")

    if ($ForPytest) {
        $pytestRoot = Join-Path $ProjectRoot ".cache/pytest"
        $snapshot["PYTEST_BASETEMP"] = New-RunScopedDirectory -BaseDir $pytestRoot -Prefix "pytest"
    }

    return $snapshot
}

function Restore-ScopedProjectRuntimeEnv {
    param([hashtable]$Snapshot)

    foreach ($entry in $Snapshot.GetEnumerator()) {
        if ($entry.Key -eq "PYTEST_BASETEMP") {
            continue
        }
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
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
    $uvExe = Resolve-UvExecutablePath
    if ($uvExe) {
        $script:UvExecutablePath = $uvExe
        Write-Debug "已检测到 uv：$(Invoke-UvCommand @('--version') 2>$null)"
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

    if (-not (Resolve-UvExecutablePath)) {
        # 尝试使用官方安装脚本（通常比 pip 更快，且不依赖 Python 环境）
        try {
            Write-Info "尝试使用官方安装脚本安装 uv..."
            $cmd = "irm https://astral.sh/uv/install.ps1 | iex"
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $cmd | Out-Host
        } catch {
            Write-Warn "官方安装脚本执行失败：$($_.Exception.Message)"
        }
    }

    if (-not (Resolve-UvExecutablePath)) {
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

    $uvExe = Resolve-UvExecutablePath
    if (-not $uvExe) {
        throw "uv 安装失败。请手动安装：winget install --id=astral-sh.uv -e 或 python -m pip install uv"
    }

    $script:UvExecutablePath = $uvExe
    Write-Ok "uv 安装完成：$(Invoke-UvCommand @('--version') 2>$null)"
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
            Invoke-UvCommand @uvArgs | Out-Host

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
    Invoke-UvCommand @uvArgs | Out-Host
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
        throw "虚拟环境不存在，请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]。"
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

    $uvArgs += @(Get-UvCacheArgs)

    Write-Info "开始安装依赖（uv）..."
    Write-Debug ("执行命令：uv " + ($uvArgs -join " "))
    Invoke-UvCommand @uvArgs | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "依赖安装失败（退出码：$LASTEXITCODE）。可尝试：-TorchBackend cpu 或设置 -DefaultIndex 镜像。"
    }

    Write-Ok "依赖安装完成"
}

function Install-EditableProject {
    param([switch]$NoDeps)

    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]。"
    }

    Ensure-Uv

    $uvArgs = @("pip", "install", "--python", $venv.Python, "-e", ".")
    if ($NoDeps) {
        $uvArgs += "--no-deps"
    }
    $uvArgs += @(Get-UvCacheArgs)

    Write-Info "开始安装当前项目（editable）..."
    Write-Debug ("执行命令：uv " + ($uvArgs -join " "))
    $editableOutput = @()
    Invoke-UvCommand @uvArgs 2>&1 | Tee-Object -Variable editableOutput | Out-Host
    if ($LASTEXITCODE -ne 0) {
        if (Test-IsEditablePermissionFailure -CommandOutput $editableOutput) {
            $pthPath = Install-EditableProjectFallback
            Write-Warn "标准 editable 安装命中已知权限异常，已切换为本地 .pth 桥接：$pthPath"
            Write-Ok "当前项目已通过本地 .pth 桥接接入虚拟环境"
            return
        }
        throw "当前项目 editable 安装失败（退出码：$LASTEXITCODE）。"
    }

    Write-Ok "当前项目已安装为 editable"
}

function Assert-ProjectImportable {
    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]。"
    }

    $envSnapshot = Use-ScopedProjectRuntimeEnv
    try {
        $appPath = (& $venv.Python -c "import app; from app.entrypoints import main as _entrypoint; print(app.__file__)" 2>$null | Select-Object -Last 1)
    } finally {
        Restore-ScopedProjectRuntimeEnv -Snapshot $envSnapshot
    }

    if ($LASTEXITCODE -ne 0 -or -not $appPath) {
        throw "项目导入验证失败：无法导入 app/app.entrypoints。请先清理根目录残留 app 目录，然后重新运行 .\\scripts\\vwr.ps1 并在菜单中选择[环境初始化]。"
    }

    return $appPath.Trim()
}

function Test-ProjectImportable {
    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        return $false
    }

    $envSnapshot = Use-ScopedProjectRuntimeEnv
    try {
        & $venv.Python -c "import app; from app.entrypoints import main as _entrypoint" *> $null
        return ($LASTEXITCODE -eq 0)
    } finally {
        Restore-ScopedProjectRuntimeEnv -Snapshot $envSnapshot
    }
}

function Ensure-ProjectImportable {
    param([switch]$AutoFixSetup)

    if (Test-ProjectImportable) {
        return
    }

    if ($AutoFixSetup) {
        Write-Warn "当前环境尚未完成项目安装，AutoFix 将重新执行 setup..."
        Invoke-Setup
        if (Test-ProjectImportable) {
            return
        }
    }

    throw "当前环境尚未完成项目安装，请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]。"
}

function Assert-DevTools {
    $venv = Get-VenvInfo
    if (-not (Test-Path $venv.Python)) {
        throw "虚拟环境不存在，请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]，然后开启[安装开发依赖]。"
    }

    $check = & $venv.Python -m pytest --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "未检测到 pytest（开发依赖）。请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]，然后开启[安装开发依赖]。"
    }
}

function Get-LamaTorchScriptDownloadUrl {
    return "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"
}

function Show-LamaTorchScriptHint {
    $url = Get-LamaTorchScriptDownloadUrl
    Write-Info "LaMa TorchScript 模型下载（big-lama.pt）：$url"
    Write-Info '下载后可设置：$env:VWR_LAMA_MODEL_PATH="C:/path/to/big-lama.pt"'
}

function Resolve-ConfigOptionValue {
    param(
        [string]$ConfigPath,
        [string[]]$OptionNames
    )

    $result = @{
        Value = ""
        OptionName = ""
    }

    if (-not $ConfigPath -or -not (Test-Path $ConfigPath)) {
        return $result
    }

    try {
        foreach ($line in Get-Content -Path $ConfigPath -Encoding UTF8) {
            $trimmed = [string]$line
            if (-not $trimmed) {
                continue
            }

            foreach ($optionName in $OptionNames) {
                $pattern = '^\s*' + [regex]::Escape($optionName) + '\s*=\s*(.+?)\s*$'
                if ($trimmed -match $pattern) {
                    $resolvedValue = [string]$Matches[1]
                    if ($resolvedValue -and $resolvedValue.Trim()) {
                        $result.Value = $resolvedValue.Trim()
                        $result.OptionName = $optionName
                        return $result
                    }
                }
            }
        }
    } catch {
        Write-Debug "读取配置项失败：$($_.Exception.Message)"
    }

    return $result
}

function Get-LamaCommonAssetCandidates {
    return @(
        (Join-Path $ProjectRoot "models/big-lama.pt"),
        (Join-Path $ProjectRoot "models/lama/big-lama.pt")
    )
}

function Resolve-LamaStartupAssetRef {
    param([string]$ConfigPath)

    if ($env:VWR_LAMA_MODEL_PATH -and $env:VWR_LAMA_MODEL_PATH.Trim()) {
        return @{
            Path = $env:VWR_LAMA_MODEL_PATH.Trim()
            Source = "VWR_LAMA_MODEL_PATH"
        }
    }

    $configValue = Resolve-ConfigOptionValue -ConfigPath $ConfigPath -OptionNames @("lama_model_path", "lama_model_dir")
    if ($configValue.Value) {
        return @{
            Path = $configValue.Value
            Source = "config:$($configValue.OptionName)"
        }
    }

    foreach ($candidate in Get-LamaCommonAssetCandidates) {
        if (Test-Path $candidate) {
            return @{
                Path = $candidate
                Source = "project:$([System.IO.Path]::GetFileName($candidate))"
            }
        }
    }

    return @{
        Path = ""
        Source = ""
    }
}

function Resolve-LegacyInpaintingStartupAssetRef {
    param([string]$ConfigPath)

    if ($env:VWR_INPAINTING_MODEL_PATH -and $env:VWR_INPAINTING_MODEL_PATH.Trim()) {
        return @{
            Path = $env:VWR_INPAINTING_MODEL_PATH.Trim()
            Source = "VWR_INPAINTING_MODEL_PATH"
        }
    }

    $configValue = Resolve-ConfigOptionValue -ConfigPath $ConfigPath -OptionNames @("inpainting_model_path")
    if ($configValue.Value) {
        return @{
            Path = $configValue.Value
            Source = "config:$($configValue.OptionName)"
        }
    }

    return @{
        Path = ""
        Source = ""
    }
}

function Resolve-LamaTorchScriptAssetStatus {
    param([string]$AssetRef)

    if (-not $AssetRef -or -not $AssetRef.Trim()) {
        return @{
            Status = "missing"
            ResolvedPath = ""
            Detail = ""
        }
    }

    if (-not (Test-Path $AssetRef)) {
        return @{
            Status = "path_missing"
            ResolvedPath = $AssetRef
            Detail = ""
        }
    }

    $item = Get-Item -LiteralPath $AssetRef -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        return @{
            Status = "path_missing"
            ResolvedPath = $AssetRef
            Detail = ""
        }
    }

    if ($item.PSIsContainer) {
        foreach ($candidate in @(
                (Join-Path $item.FullName "big-lama.pt"),
                (Join-Path $item.FullName "lama.pt"),
                (Join-Path $item.FullName "model.pt"),
                (Join-Path $item.FullName "models/big-lama.pt"),
                (Join-Path $item.FullName "models/lama.pt"),
                (Join-Path $item.FullName "models/model.pt")
            )) {
            if (Test-Path $candidate) {
                return @{
                    Status = "ready"
                    ResolvedPath = $candidate
                    Detail = "directory_candidate"
                }
            }
        }

        return @{
            Status = "directory_missing_torchscript"
            ResolvedPath = $item.FullName
            Detail = ""
        }
    }

    $suffix = $item.Extension.ToLowerInvariant()
    if ($suffix -in @(".pt", ".jit", ".ts")) {
        return @{
            Status = "ready"
            ResolvedPath = $item.FullName
            Detail = ""
        }
    }

    if ($suffix -in @(".pth", ".ckpt")) {
        return @{
            Status = "unsupported_format"
            ResolvedPath = $item.FullName
            Detail = "当前 LaMa runner 仅支持 TorchScript .pt/.jit/.ts 文件。"
        }
    }

    return @{
        Status = "unsupported_format"
        ResolvedPath = $item.FullName
        Detail = "无法识别的 LaMa 资产文件类型。"
    }
}

function Resolve-LegacyInpaintingAssetStatus {
    param([string]$AssetRef)

    if (-not $AssetRef -or -not $AssetRef.Trim()) {
        return @{
            Status = "missing"
            ResolvedPath = ""
        }
    }

    if (-not (Test-Path $AssetRef)) {
        return @{
            Status = "path_missing"
            ResolvedPath = $AssetRef
        }
    }

    $item = Get-Item -LiteralPath $AssetRef -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        return @{
            Status = "path_missing"
            ResolvedPath = $AssetRef
        }
    }

    if ($item.PSIsContainer) {
        return @{
            Status = "directory_path"
            ResolvedPath = $item.FullName
        }
    }

    return @{
        Status = "ready"
        ResolvedPath = $item.FullName
    }
}

function Show-StartupInpaintingPrecheck {
    param([string]$ConfigPath)

    $lamaRef = Resolve-LamaStartupAssetRef -ConfigPath $ConfigPath
    $lamaStatus = Resolve-LamaTorchScriptAssetStatus -AssetRef $lamaRef.Path
    switch ($lamaStatus.Status) {
        "ready" {
            Write-Ok "LaMa 启动前检查：已发现可直接用于 LaMa 的 TorchScript 模型：$($lamaStatus.ResolvedPath)"
        }
        "path_missing" {
            Write-Warn "LaMa 启动前检查：$($lamaRef.Source) 指向的路径不存在：$($lamaStatus.ResolvedPath)"
            Show-LamaTorchScriptHint
        }
        "directory_missing_torchscript" {
            Write-Warn "LaMa 启动前检查：目录中未发现可用的 TorchScript 模型：$($lamaStatus.ResolvedPath)"
            Show-LamaTorchScriptHint
        }
        "unsupported_format" {
            $detail = $lamaStatus.Detail
            if (-not $detail) {
                $detail = "请改用 TorchScript big-lama.pt。"
            }
            Write-Warn "LaMa 启动前检查：资产格式不受支持：$($lamaStatus.ResolvedPath)；$detail"
            Show-LamaTorchScriptHint
        }
        default {
            Write-Info "LaMa 启动前检查：未检测到可用的 TorchScript 模型，如需启用 LaMa 深度修复，请先准备 big-lama.pt。"
            Show-LamaTorchScriptHint
        }
    }

    $legacyRef = Resolve-LegacyInpaintingStartupAssetRef -ConfigPath $ConfigPath
    $legacyStatus = Resolve-LegacyInpaintingAssetStatus -AssetRef $legacyRef.Path
    switch ($legacyStatus.Status) {
        "ready" {
            Write-Ok "旧 GPU U-Net 启动前检查：已发现候选权重：$($legacyStatus.ResolvedPath)"
        }
        "path_missing" {
            Write-Warn "旧 GPU U-Net 启动前检查：$($legacyRef.Source) 指向的路径不存在：$($legacyStatus.ResolvedPath)"
            Write-Info '如需启用旧 GPU U-Net，可设置：$env:VWR_INPAINTING_MODEL_PATH="C:/path/to/model.pth"'
        }
        "directory_path" {
            Write-Warn "旧 GPU U-Net 启动前检查：当前路径是目录，请改为权重文件路径：$($legacyStatus.ResolvedPath)"
            Write-Info '如需启用旧 GPU U-Net，可设置：$env:VWR_INPAINTING_MODEL_PATH="C:/path/to/model.pth"'
        }
        default {
            Write-Info '旧 GPU U-Net 启动前检查：未检测到候选权重；如需启用，可设置：$env:VWR_INPAINTING_MODEL_PATH="C:/path/to/model.pth"'
        }
    }
}

function Test-ConfigHasLamaModelPath {
    param([string]$ConfigPath)

    if (-not $ConfigPath -or -not (Test-Path $ConfigPath)) {
        return $false
    }

    try {
        foreach ($line in Get-Content -Path $ConfigPath -Encoding UTF8) {
            $trimmed = [string]$line
            if (-not $trimmed) {
                continue
            }
            if ($trimmed -match '^\s*(lama_model_path|lama_model_dir)\s*=\s*(.+?)\s*$') {
                if ($Matches[2] -and $Matches[2].Trim()) {
                    return $true
                }
            }
        }
    } catch {
        Write-Debug "读取 LaMa 配置提示失败：$($_.Exception.Message)"
    }

    return $false
}

function Test-ShouldShowLamaTorchScriptHint {
    param([string]$ConfigPath)

    if ($env:VWR_LAMA_MODEL_PATH -and $env:VWR_LAMA_MODEL_PATH.Trim()) {
        return $false
    }

    if (Test-ConfigHasLamaModelPath -ConfigPath $ConfigPath) {
        return $false
    }

    foreach ($candidate in @(
            (Join-Path $ProjectRoot "models/big-lama.pt"),
            (Join-Path $ProjectRoot "models/lama/big-lama.pt")
        )) {
        if (Test-Path $candidate) {
            return $false
        }
    }

    return $true
}

function Show-Help {
    Write-Host "🎛️ 智能视频水印去除工具 - 纯交互式脚本入口 (vwr.ps1)" -ForegroundColor Green
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host ""
    Write-Host "用法：" -ForegroundColor Cyan
    Write-Host "  直接运行：.\\scripts\\vwr.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "菜单功能：" -ForegroundColor Cyan
    Write-Host "  1. 环境初始化：创建 .venv 并安装依赖" -ForegroundColor White
    Write-Host "  2. 启动程序：环境检查后启动 main.py" -ForegroundColor White
    Write-Host "  3. 代码质量检查：black / flake8 / mypy / bandit" -ForegroundColor White
    Write-Host "  4. 运行测试：pytest + 可选 PowerShell 测试脚本" -ForegroundColor White
    Write-Host "  5. 覆盖率分析：pytest-cov" -ForegroundColor White
    Write-Host "  6. 性能测试：生成 JSON 报告" -ForegroundColor White
    Write-Host "  7. 打包构建：PyInstaller 输出 release/" -ForegroundColor White
    Write-Host "  8. 清理缓存与临时文件：basic / temp / all / deep" -ForegroundColor White
    Write-Host "  9. CI 模式：运行质量、单测与可选门禁" -ForegroundColor White
    Write-Host ""
    Write-Host "提示：" -ForegroundColor Cyan
    Write-Host "  脚本已移除旧式尾参命令，请勿再使用 .\\scripts\\vwr.ps1 help/setup/run/test ..." -ForegroundColor White
    Write-Host "  如需查看帮助，可在主菜单输入 H" -ForegroundColor White
    Write-Host ""
    Write-Host "LaMa TorchScript 权重：" -ForegroundColor Cyan
    Write-Host ("  下载：{0}" -f (Get-LamaTorchScriptDownloadUrl)) -ForegroundColor White
    Write-Host '  环境变量：$env:VWR_LAMA_MODEL_PATH="C:/path/to/big-lama.pt"' -ForegroundColor White
    Write-Host ""
}

function Show-InteractiveMenuHeader {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  智能视频水印去除工具 - 交互式菜单" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. 环境初始化" -ForegroundColor White
    Write-Host "  2. 启动程序" -ForegroundColor White
    Write-Host "  3. 代码质量检查" -ForegroundColor White
    Write-Host "  4. 运行测试" -ForegroundColor White
    Write-Host "  5. 覆盖率分析" -ForegroundColor White
    Write-Host "  6. 性能测试" -ForegroundColor White
    Write-Host "  7. 打包构建" -ForegroundColor White
    Write-Host "  8. 清理缓存与临时文件" -ForegroundColor White
    Write-Host "  9. CI 模式" -ForegroundColor White
    Write-Host "  H. 查看帮助" -ForegroundColor White
    Write-Host "  0. 退出" -ForegroundColor White
    Write-Host ""
}

function Read-ChoiceValue {
    param(
        [string]$Prompt,
        [string[]]$AllowedValues,
        [string]$DefaultValue = ""
    )

    while ($true) {
        $suffix = if ($DefaultValue) { " [$DefaultValue]" } else { "" }
        $answer = Read-Host "$Prompt$suffix"
        if ([string]::IsNullOrWhiteSpace($answer) -and $DefaultValue) {
            return $DefaultValue
        }

        $normalized = ([string]$answer).Trim()
        foreach ($candidate in $AllowedValues) {
            if ($normalized.ToUpperInvariant() -eq $candidate.ToUpperInvariant()) {
                return $candidate
            }
        }

        Write-Warn ("输入无效，可选值：{0}" -f ($AllowedValues -join "/"))
    }
}

function Read-YesNo {
    param(
        [string]$Prompt,
        [bool]$Default = $true
    )

    $defaultLabel = if ($Default) { "Y/n" } else { "y/N" }
    while ($true) {
        $answer = Read-Host "$Prompt ($defaultLabel)"
        if ([string]::IsNullOrWhiteSpace($answer)) {
            return $Default
        }

        $normalized = ([string]$answer).Trim().ToUpperInvariant()
        if ($normalized -in @("Y", "YES")) {
            return $true
        }
        if ($normalized -in @("N", "NO")) {
            return $false
        }

        Write-Warn "请输入 Y 或 N"
    }
}

function Read-TextWithDefault {
    param(
        [string]$Prompt,
        [string]$DefaultValue = ""
    )

    $suffix = if ($DefaultValue) { " [$DefaultValue]" } else { "" }
    $answer = Read-Host "$Prompt$suffix"
    if ([string]::IsNullOrWhiteSpace($answer)) {
        return $DefaultValue
    }
    return ([string]$answer).Trim()
}

function Show-LegacyCliRemovedNotice {
    Write-Host ""
    Write-Host "当前脚本已改为纯交互模式，请直接运行：.\\scripts\\vwr.ps1" -ForegroundColor Yellow
    Write-Host "不再支持旧式尾参命令：help/setup/run/test/quality/coverage/perf/build/clean/ci" -ForegroundColor Yellow
    Write-Host ""
}

function Invoke-InteractiveSetup {
    $script:Dev = Read-YesNo -Prompt "是否安装开发依赖" -Default $false
    $script:Python = Read-TextWithDefault -Prompt "Python 版本" -DefaultValue "3.12.10"
    $script:TorchBackend = Read-ChoiceValue -Prompt "Torch 后端：1.auto 2.cpu 3.cu121 4.cu124 5.cu126 6.cu128 7.cu130" -AllowedValues @("1", "2", "3", "4", "5", "6", "7") -DefaultValue "1"
    $script:TorchBackend = switch ($script:TorchBackend) {
        "1" { "auto" }
        "2" { "cpu" }
        "3" { "cu121" }
        "4" { "cu124" }
        "5" { "cu126" }
        "6" { "cu128" }
        default { "cu130" }
    }

    $indexChoice = Read-ChoiceValue -Prompt "索引源：1.自动 2.清华镜像 3.自定义" -AllowedValues @("1", "2", "3") -DefaultValue "1"
    switch ($indexChoice) {
        "1" {
            $script:DefaultIndex = ""
            $script:DefaultIndexIsBound = $false
        }
        "2" {
            $script:DefaultIndex = "https://pypi.tuna.tsinghua.edu.cn/simple"
            $script:DefaultIndexIsBound = $true
        }
        "3" {
            $script:DefaultIndex = Read-TextWithDefault -Prompt "请输入自定义索引 URL"
            $script:DefaultIndexIsBound = $true
        }
    }

    $strategyChoice = Read-ChoiceValue -Prompt "索引策略：1.first-index 2.unsafe-first-match 3.unsafe-best-match" -AllowedValues @("1", "2", "3") -DefaultValue "1"
    $script:IndexStrategy = switch ($strategyChoice) {
        "1" { "first-index" }
        "2" { "unsafe-first-match" }
        default { "unsafe-best-match" }
    }

    Invoke-Setup
}

function Invoke-InteractiveRun {
    $script:AutoFix = Read-YesNo -Prompt "是否自动修复常见问题" -Default $true
    $script:SkipChecks = Read-YesNo -Prompt "是否跳过启动前检查" -Default $false
    Invoke-Run
}

function Invoke-InteractiveQuality {
    $checkChoice = Read-ChoiceValue -Prompt "检查类型：1.all 2.format 3.style 4.type 5.security" -AllowedValues @("1", "2", "3", "4", "5") -DefaultValue "1"
    $script:Check = switch ($checkChoice) {
        "1" { "all" }
        "2" { "format" }
        "3" { "style" }
        "4" { "type" }
        default { "security" }
    }
    $script:Fix = Read-YesNo -Prompt "是否自动修复" -Default $false
    $script:Quick = Read-YesNo -Prompt "是否启用快速模式" -Default $false
    Invoke-Quality
}

function Invoke-InteractiveTest {
    $typeChoice = Read-ChoiceValue -Prompt "测试类型：1.unit 2.integration 3.all 4.audio 5.preferences 6.e2e 7.quality" -AllowedValues @("1", "2", "3", "4", "5", "6", "7") -DefaultValue "1"
    $script:Arg1 = switch ($typeChoice) {
        "1" { "unit" }
        "2" { "integration" }
        "3" { "all" }
        "4" { "audio" }
        "5" { "preferences" }
        "6" { "e2e" }
        default { "quality" }
    }
    $script:Quick = Read-YesNo -Prompt "是否启用快速模式" -Default $true
    $script:Coverage = Read-YesNo -Prompt "是否附带覆盖率分析" -Default $false
    $script:Performance = Read-YesNo -Prompt "是否附带性能测试" -Default $false
    $script:Report = Read-YesNo -Prompt "是否保存 JSON 报告" -Default $false
    Invoke-Test
}

function Invoke-InteractiveCoverage {
    $script:MinCoverage = [double](Read-TextWithDefault -Prompt "最低覆盖率阈值" -DefaultValue "80")
    $script:FailOnLow = Read-YesNo -Prompt "低于阈值时是否失败" -Default $false
    $script:OpenReport = Read-YesNo -Prompt "是否自动打开 HTML 报告" -Default $false
    $script:Quick = Read-YesNo -Prompt "是否启用快速模式" -Default $false
    Invoke-Coverage
}

function Invoke-InteractivePerf {
    $script:Quick = Read-YesNo -Prompt "是否启用快速模式" -Default $true
    $script:Iterations = [int](Read-TextWithDefault -Prompt "迭代次数" -DefaultValue "5")
    $script:MemoryProfile = Read-YesNo -Prompt "是否采集内存信息" -Default $false
    $script:GPUProfile = Read-YesNo -Prompt "是否采集 GPU 信息" -Default $false
    Invoke-Perf
}

function Invoke-InteractiveBuild {
    $script:SkipTests = Read-YesNo -Prompt "是否跳过构建前测试" -Default $false
    $script:Quick = Read-YesNo -Prompt "是否启用快速模式" -Default $false
    Invoke-Build
}

function Invoke-InteractiveClean {
    $scopeChoice = Read-ChoiceValue -Prompt "清理级别：1.basic 2.temp 3.all 4.deep" -AllowedValues @("1", "2", "3", "4") -DefaultValue "3"
    $script:CleanScope = switch ($scopeChoice) {
        "1" { "basic" }
        "2" { "temp" }
        "3" { "all" }
        default { "deep" }
    }
    Invoke-Clean -Scope $script:CleanScope
}

function Invoke-InteractiveCI {
    $script:Quick = Read-YesNo -Prompt "是否启用快速模式" -Default $false
    $script:SkipCoverage = Read-YesNo -Prompt "是否跳过覆盖率检查" -Default $false
    $script:SkipPerformance = Read-YesNo -Prompt "是否跳过性能测试" -Default $false
    $script:TimeoutMinutes = [int](Read-TextWithDefault -Prompt "CI 超时时间（分钟）" -DefaultValue "30")
    Invoke-CI
}

function Start-InteractiveMenu {
    while ($true) {
        Reset-ExecutionOptions
        Show-InteractiveMenuHeader
        $choice = Read-ChoiceValue -Prompt "请输入选项" -AllowedValues @("1", "2", "3", "4", "5", "6", "7", "8", "9", "H", "0") -DefaultValue "0"

        switch ($choice.ToUpperInvariant()) {
            "1" { Invoke-InteractiveSetup }
            "2" { Invoke-InteractiveRun }
            "3" { Invoke-InteractiveQuality }
            "4" { Invoke-InteractiveTest }
            "5" { Invoke-InteractiveCoverage }
            "6" { Invoke-InteractivePerf }
            "7" { Invoke-InteractiveBuild }
            "8" { Invoke-InteractiveClean }
            "9" { Invoke-InteractiveCI }
            "H" { Show-Help }
            "0" {
                Write-Info "已退出交互式菜单"
                return
            }
        }
    }
}

function Invoke-Setup {
    Write-Section "环境配置 (setup)"
    Ensure-Venv -PythonSelector $Python

    $requirementsFile = if ($Dev) { "requirements-dev.txt" } else { "requirements.txt" }
    $dependencySet = if ($Dev) { "dev" } else { "prod" }
    Write-Info "依赖清单：$requirementsFile"

    $dependencyState = Test-SetupDependencyState -RequirementsFile $requirementsFile -DependencySet $dependencySet
    if ($dependencyState.Satisfied) {
        Write-Ok "检测到依赖已满足，跳过重复安装：$requirementsFile"
    } else {
        Write-Info "依赖状态未命中：$($dependencyState.Reason)，执行安装：$requirementsFile"
        if ($dependencyState.MissingPackages.Count -gt 0) {
            Write-Debug ("缺失探针包：" + ($dependencyState.MissingPackages -join ", "))
        }

        Invoke-UvPipInstall -RequirementsFile $requirementsFile -TorchBackendValue $TorchBackend -DefaultIndexValue $DefaultIndex -IndexStrategyValue $IndexStrategy
        Write-SetupDependencyState -RequirementsFile "requirements.txt" -DependencySet "prod"
        if ($Dev) {
            Write-SetupDependencyState -RequirementsFile "requirements-dev.txt" -DependencySet "dev"
        }
    }

    Install-EditableProject -NoDeps
    $appPath = Assert-ProjectImportable

    $venv = Get-VenvInfo
    $pyVer = & $venv.Python --version 2>&1
    Write-Ok "Python：$pyVer"
    Write-Ok "导入验证：$appPath"
    Write-Ok "完成：可重新运行 .\\scripts\\vwr.ps1，并在菜单中选择[启动程序]。"
}

function Test-KeyPackages {
    param([switch]$FixIfMissing)

    $venv = Get-VenvInfo
    $requirementsFile = Join-Path $ProjectRoot "requirements.txt"

    if (-not (Test-Path $requirementsFile)) {
        Write-Warn "未找到 requirements.txt，跳过依赖检查"
        return $true
    }

    $keyPackages = @("PyQt6", "opencv-python", "numpy", "Pillow", "torch", "ultralytics")
    $missing = @()

    foreach ($pkg in $keyPackages) {
        if (-not (Test-PythonDistributionInstalled -PythonPath $venv.Python -DistributionName $pkg)) {
            $missing += $pkg
        }
    }

    if ($missing.Count -eq 0) {
        Write-Ok "关键依赖检查通过（$($keyPackages.Count) 项）"
        return $true
    }

    Write-Warn ("缺失关键依赖：" + ($missing -join ", "))
    Write-Info "建议修复：重新运行 .\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]。"

    if ($FixIfMissing) {
        Write-Info "AutoFix：尝试自动安装 requirements.txt ..."
        Invoke-UvPipInstall -RequirementsFile "requirements.txt" -TorchBackendValue $TorchBackend -DefaultIndexValue $DefaultIndex -IndexStrategyValue $IndexStrategy

        foreach ($pkg in $missing) {
            if (-not (Test-PythonDistributionInstalled -PythonPath $venv.Python -DistributionName $pkg)) {
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
            throw "虚拟环境不存在，请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]。"
        }
    }

    Ensure-ProjectImportable -AutoFixSetup:$AutoFix

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

        Write-Section "深度修复模型体检"
        Show-StartupInpaintingPrecheck -ConfigPath $configIni
    } else {
        Write-Warn "已跳过环境检查（-SkipChecks）"
    }

    Write-Section "运行 main.py"

    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

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
    Ensure-ProjectImportable

    $venv = Get-VenvInfo

    if (-not $env:BLACK_CACHE_DIR) {
        $env:BLACK_CACHE_DIR = Join-Path $ProjectRoot ".cache/black"
    }
    if (-not (Test-Path $env:BLACK_CACHE_DIR)) {
        New-Item -ItemType Directory -Path $env:BLACK_CACHE_DIR -Force | Out-Null
    }

    $targets = @()
    if (Test-Path "src/app") { $targets += "src/app" }
    if (Test-Path "main.py") { $targets += "main.py" }
    if (Test-Path "tests") { $targets += "tests" }

    if ($targets.Count -eq 0) {
        throw "未找到需要检查的目标（src/app/main.py/tests）"
    }

    $failed = $false

    if ($Check -eq "all" -or $Check -eq "format") {
        Write-Info "Black：$(if($Fix){'格式化'}else{'检查'})"
        $blackArgs = @("--line-length", "100")
        if ($Quick) {
            $blackArgs += @("--workers", "1")
        }
        if (-not $Fix) {
            $blackArgs += "--check"
            if (-not $Quick) {
                $blackArgs += "--diff"
            }
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
                Write-Info "可重新运行 .\\scripts\\vwr.ps1，并在菜单中选择[代码质量检查]，然后开启[自动修复]。"
            }
        } else {
            Write-Ok "Black 通过"
        }
    }

    if ($Check -eq "all" -or $Check -eq "style") {
        Write-Info "Flake8：检查"
        $flakeArgs = @()
        if ($Quick) {
            $flakeArgs += @("--jobs", "1")
        }
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
        & $venv.Python -m mypy "src/app" "main.py" | Out-Host
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
        & $venv.Python -m bandit -r "src/app" "main.py" | Out-Host
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
    $envSnapshot = Use-ScopedProjectRuntimeEnv -ForPytest
    try {
        Ensure-ProjectImportable
        $venv = Get-VenvInfo

        # 先做一次关键依赖探测，避免 pytest 在收集阶段抛出难以理解的 ImportError
        $depsOk = Test-KeyPackages
        if (-not $depsOk) {
            Write-Err "关键依赖未安装或不完整，无法运行 pytest。请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]，然后开启[安装开发依赖]。"
            return 2
        }

        $finalArgs = @()
        $finalArgs += $PytestArgs
        if ($envSnapshot.ContainsKey("PYTEST_BASETEMP")) {
            $finalArgs += @("--basetemp", $envSnapshot["PYTEST_BASETEMP"])
        }
        $finalArgs += "--color=yes"

        Write-Debug ("pytest 参数：" + ($finalArgs -join " "))
        & $venv.Python -m pytest @finalArgs | Out-Host
        return $LASTEXITCODE
    } finally {
        Restore-ScopedProjectRuntimeEnv -Snapshot $envSnapshot
    }
}

function Invoke-PowerShellScriptFile {
    param(
        [string]$ScriptPath,
        [string[]]$ScriptArgs = @()
    )

    if (-not (Test-Path $ScriptPath)) {
        throw "脚本不存在：$ScriptPath"
    }

    $pwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue
    $psExe = if ($pwshCommand) { $pwshCommand.Source } else { "powershell.exe" }
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) + $ScriptArgs

    Write-Debug ("执行 PowerShell 子进程：{0} {1}" -f $psExe, ($argList -join " "))
    $proc = Start-Process -FilePath $psExe -ArgumentList $argList -Wait -PassThru -NoNewWindow
    return $proc.ExitCode
}

function Invoke-Test {
    Write-Section "测试执行 (test)"
    Write-Info "测试主分层：unit → tests/unit，integration → tests/integration，e2e → tests/e2e/ps1/*.ps1"

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
        throw "虚拟环境不存在，请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]。"
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
        throw "虚拟环境不存在，请直接运行：.\\scripts\\vwr.ps1，并在菜单中选择[环境初始化]，然后开启[安装开发依赖]。"
    }

    Ensure-ProjectImportable
    Ensure-Uv

    Write-Info "确保 PyInstaller 已安装..."
    $uvArgs = @("pip", "install", "--python", $venv.Python, "PyInstaller>=5.0.0")
    $uvArgs += @(Get-UvCacheArgs)
    Write-Debug ("执行命令：uv " + ($uvArgs -join " "))
    Invoke-UvCommand @uvArgs | Out-Host
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

    $iconPath = Join-Path $ProjectRoot "src/app/assets/icons/app.ico"
    $pyInstallerArgs = @(
        "--onefile",
        "--windowed",
        "--name=智能水印去除工具",
        "--add-data=src/app;app",
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

function Resolve-CleanTargets {
    param(
        [ValidateSet("basic", "temp", "all", "deep")]
        [string]$Scope = "all"
    )

    $targets = [System.Collections.Generic.List[object]]::new()

    if ($Scope -in @("basic", "all", "deep")) {
        foreach ($target in @(
                @{ Type = "dir"; Path = ".mypy_cache" },
                @{ Type = "dir"; Path = ".pytest_cache" },
                @{ Type = "file"; Path = ".coverage" },
                @{ Type = "glob"; Path = ".coverage.*" },
                @{ Type = "glob"; Path = "logs/*.log" }
            )) {
            $targets.Add([pscustomobject]$target) | Out-Null
        }
    }

    if ($Scope -in @("temp", "all", "deep")) {
        foreach ($target in @(
                @{ Type = "dir"; Path = ".cache/tmp" },
                @{ Type = "dir"; Path = ".cache/pytest" },
                @{ Type = "dir"; Path = ".cache/tests" },
                @{ Type = "dir"; Path = ".pytest_tmp" },
                @{ Type = "dir"; Path = ".tmp_test_harness" },
                @{ Type = "glob"; Path = "pytest-cache-files-*" },
                @{ Type = "glob"; Path = ".tmp_*" },
                @{ Type = "glob"; Path = "tmp_*" },
                @{ Type = "dir"; Path = "test_output" },
                @{ Type = "dir"; Path = "tests/.cache" },
                @{ Type = "dir"; Path = "tests/test_data/runtime_tmp" }
            )) {
            $targets.Add([pscustomobject]$target) | Out-Null
        }
    }

    if ($Scope -eq "deep") {
        foreach ($target in @(
                @{ Type = "dir"; Path = ".uv-cache" },
                @{ Type = "dir"; Path = ".cache/uv" },
                @{ Type = "dir"; Path = ".cache/setup-state" },
                @{ Type = "dir"; Path = "src/video_watermark_remover.egg-info" }
            )) {
            $targets.Add([pscustomobject]$target) | Out-Null
        }
    }

    return @($targets)
}

function New-CleanFailureRecord {
    param(
        [string]$Path,
        [string]$Message
    )

    return [pscustomobject]@{
        Path = $Path
        Message = $Message
    }
}

function New-CleanResult {
    param(
        [int]$RemovedCount = 0,
        [object[]]$Failures = @()
    )

    return [pscustomobject]@{
        RemovedCount = $RemovedCount
        Failures = @($Failures)
    }
}

function Merge-CleanResult {
    param(
        [pscustomobject]$BaseResult,
        [pscustomobject]$DeltaResult
    )

    return [pscustomobject]@{
        RemovedCount = ($BaseResult.RemovedCount + $DeltaResult.RemovedCount)
        Failures = @($BaseResult.Failures) + @($DeltaResult.Failures)
    }
}

function Remove-CleanLiteralPath {
    param(
        [string]$LiteralPath,
        [bool]$Recurse = $false
    )

    if (-not (Test-Path $LiteralPath)) {
        return (New-CleanResult)
    }

    try {
        Remove-Item -LiteralPath $LiteralPath -Recurse:$Recurse -Force -ErrorAction Stop
        return (New-CleanResult -RemovedCount 1)
    } catch {
        return (New-CleanResult -Failures @(
                (New-CleanFailureRecord -Path $LiteralPath -Message $_.Exception.Message)
            ))
    }
}

function Remove-CleanDirectoryWithFallback {
    param([string]$Path)

    $directResult = Remove-CleanLiteralPath -LiteralPath $Path -Recurse $true
    if ($directResult.Failures.Count -eq 0) {
        return $directResult
    }

    $children = @()
    try {
        $children = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction Stop)
    } catch {
        return $directResult
    }

    $result = New-CleanResult
    foreach ($child in $children) {
        $childResult = Remove-CleanLiteralPath -LiteralPath $child.FullName -Recurse ([bool]$child.PSIsContainer)
        $result = Merge-CleanResult -BaseResult $result -DeltaResult $childResult
    }

    if (Test-Path $Path) {
        $remainingItems = @()
        try {
            $remainingItems = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction Stop)
        } catch {
            $remainingItems = @("__unknown__")
        }

        if ($remainingItems.Count -eq 0) {
            $rootResult = Remove-CleanLiteralPath -LiteralPath $Path -Recurse $true
            $result = Merge-CleanResult -BaseResult $result -DeltaResult $rootResult
        } else {
            $hasRootFailure = @($result.Failures | Where-Object { $_.Path -eq $Path }).Count -gt 0
            if (-not $hasRootFailure) {
                $result = Merge-CleanResult -BaseResult $result -DeltaResult (
                    New-CleanResult -Failures @(
                        (New-CleanFailureRecord -Path $Path -Message "目录未完全清理，请检查权限或占用进程。")
                    )
                )
            }
        }
    }

    return $result
}

function Remove-CleanGlobTarget {
    param([string]$Path)

    $parent = Split-Path -Path $Path -Parent
    $filter = Split-Path -Path $Path -Leaf
    $searchRoot = if ($parent) { Join-Path $ProjectRoot $parent } else { $ProjectRoot }
    if (-not (Test-Path $searchRoot)) {
        return (New-CleanResult)
    }

    $result = New-CleanResult
    $items = @(Get-ChildItem -Path $searchRoot -Filter $filter -Force -ErrorAction SilentlyContinue)
    foreach ($item in $items) {
        $itemResult = Remove-CleanLiteralPath -LiteralPath $item.FullName -Recurse ([bool]$item.PSIsContainer)
        $result = Merge-CleanResult -BaseResult $result -DeltaResult $itemResult
    }

    return $result
}

function Remove-CleanTarget {
    param([pscustomobject]$Target)

    switch ($Target.Type) {
        "dir" {
            return (Remove-CleanDirectoryWithFallback -Path $Target.Path)
        }
        "file" {
            return (Remove-CleanLiteralPath -LiteralPath $Target.Path -Recurse $false)
        }
        "glob" {
            return (Remove-CleanGlobTarget -Path $Target.Path)
        }
    }

    return (New-CleanResult)
}

function Invoke-Clean {
    param(
        [ValidateSet("basic", "temp", "all", "deep")]
        [string]$Scope = "",
        [switch]$SkipConfirm
    )

    if (-not $Scope) {
        $Scope = if ($script:CleanScope) { $script:CleanScope } else { "all" }
    }

    Write-Section "缓存清理 (clean)"
    Write-Info "清理级别：$Scope"

    $targets = Resolve-CleanTargets -Scope $Scope

    Write-Info "将清理以下内容："
    foreach ($t in $targets) {
        Write-Host ("  - " + $t.Path) -ForegroundColor White
    }
    Write-Host "  - 递归清理：__pycache__、*.pyc、*.pyo（仅 src/tests 目录）" -ForegroundColor White

    if (-not $SkipConfirm) {
        $confirmed = Read-YesNo -Prompt "是否继续清理" -Default $false
        if (-not $confirmed) {
            Write-Warn "已取消清理"
            return
        }
    }

    $removedCount = 0
    $failures = @()
    foreach ($t in $targets) {
        $result = Remove-CleanTarget -Target $t
        $removedCount += $result.RemovedCount
        $failures += @($result.Failures)
    }

    $rootPycacheResult = Remove-CleanLiteralPath -LiteralPath "__pycache__" -Recurse $true
    $removedCount += $rootPycacheResult.RemovedCount
    $failures += @($rootPycacheResult.Failures)

    foreach ($rootBytecode in @(
            (Join-Path $ProjectRoot "*.pyc"),
            (Join-Path $ProjectRoot "*.pyo")
        )) {
        $result = Remove-CleanGlobTarget -Path $rootBytecode
        $removedCount += $result.RemovedCount
        $failures += @($result.Failures)
    }

    foreach ($scopePath in @("src", "tests")) {
        if (-not (Test-Path $scopePath)) {
            continue
        }

        Get-ChildItem -Path $scopePath -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
            $result = Remove-CleanLiteralPath -LiteralPath $_.FullName -Recurse $true
            $removedCount += $result.RemovedCount
            $failures += @($result.Failures)
        }

        Get-ChildItem -Path $scopePath -Recurse -File -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue | ForEach-Object {
            $result = Remove-CleanLiteralPath -LiteralPath $_.FullName -Recurse $false
            $removedCount += $result.RemovedCount
            $failures += @($result.Failures)
        }
    }

    if ($failures.Count -gt 0) {
        foreach ($failure in @($failures | Select-Object -First 5)) {
            Write-Warn "清理失败：$($failure.Path) - $($failure.Message)"
        }

        if ($failures.Count -gt 5) {
            Write-Warn "还有 $($failures.Count - 5) 项失败未展开显示"
        }

        Write-Warn "清理完成：成功 $removedCount 项，失败 $($failures.Count) 项，已继续处理其余项。"
        return
    }

    Write-Ok "清理完成，共处理 $removedCount 项"
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
    if ($LegacyArgs.Count -gt 0) {
        Show-LegacyCliRemovedNotice
        exit 1
    }

    Start-InteractiveMenu
    exit 0
} catch {
    Write-Host "[✗] $($_.Exception.Message)" -ForegroundColor Red
    if (Is-VerboseEnabled) { Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray }
    exit 1
}
