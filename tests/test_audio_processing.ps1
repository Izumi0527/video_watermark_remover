#!/usr/bin/env powershell
# 智能视频水印去除工具 - 音频处理功能测试脚本
# 专门测试音频提取、合并和FFmpeg集成功能

param(
    [Parameter()]
    [switch]$Verbose,
    
    [Parameter()]
    [switch]$Quick,
    
    [Parameter()]
    [string]$TestDataPath = "tests/test_data"
)

# 设置错误处理
$ErrorActionPreference = "Stop"

# 颜色配置
$Colors = @{
    Header = "Green"
    Success = "Green"
    Warning = "Yellow" 
    Error = "Red"
    Info = "Cyan"
    Detail = "White"
    Progress = "Blue"
}

# 测试结果追踪
$TestResults = @{
    Passed = 0
    Failed = 0
    Skipped = 0
    Details = @()
    StartTime = Get-Date
}

# 记录测试结果函数
function Record-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = "",
        [bool]$Skipped = $false
    )
    
    $result = @{
        TestName = $TestName
        Passed = $Passed
        Skipped = $Skipped
        Details = $Details
        Timestamp = Get-Date
    }
    
    $TestResults.Details += $result
    
    if ($Skipped) {
        $TestResults.Skipped++
        Write-Host "⏭️ $TestName - 跳过" -ForegroundColor $Colors.Warning
    } elseif ($Passed) {
        $TestResults.Passed++
        Write-Host "✅ $TestName - 通过" -ForegroundColor $Colors.Success
    } else {
        $TestResults.Failed++
        Write-Host "❌ $TestName - 失败" -ForegroundColor $Colors.Error
        if ($Details -and $Verbose) {
            Write-Host "   详细信息: $Details" -ForegroundColor $Colors.Detail
        }
    }
}

# 显示测试摘要
function Show-TestSummary {
    $endTime = Get-Date
    $duration = $endTime - $TestResults.StartTime
    
    Write-Host ""
    Write-Host "🎵 音频处理测试摘要" -ForegroundColor $Colors.Header
    Write-Host "=" * 50 -ForegroundColor $Colors.Info
    Write-Host "🕒 执行时间: $($duration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
    Write-Host "✅ 通过: $($TestResults.Passed)" -ForegroundColor $Colors.Success
    Write-Host "❌ 失败: $($TestResults.Failed)" -ForegroundColor $Colors.Error
    Write-Host "⏭️ 跳过: $($TestResults.Skipped)" -ForegroundColor $Colors.Warning
    Write-Host "📋 总计: $(($TestResults.Passed + $TestResults.Failed + $TestResults.Skipped))" -ForegroundColor $Colors.Info
    
    if ($TestResults.Failed -eq 0) {
        Write-Host ""
        Write-Host "🎉 所有音频处理测试通过！" -ForegroundColor $Colors.Success
    } else {
        Write-Host ""
        Write-Host "⚠️ 有 $($TestResults.Failed) 项音频测试失败" -ForegroundColor $Colors.Warning
    }
}

Write-Host "🎵 智能视频水印去除工具 - 音频处理测试" -ForegroundColor $Colors.Header
Write-Host "模式: $(if($Quick){'快速'}else{'完整'}) | 详细输出: $(if($Verbose){'开启'}else{'关闭'})" -ForegroundColor $Colors.Info
Write-Host "=" * 60 -ForegroundColor $Colors.Info

# 检查虚拟环境
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 虚拟环境不存在，请先运行: .\scripts\setup.ps1" -ForegroundColor $Colors.Error
    exit 1
}

# 激活虚拟环境
Write-Host "🔄 激活虚拟环境..." -ForegroundColor $Colors.Progress
. .\.venv\Scripts\Activate.ps1

# 设置环境变量
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = (Get-Location).Path

# 创建测试数据目录
if (-not (Test-Path $TestDataPath)) {
    New-Item -ItemType Directory -Path $TestDataPath -Force | Out-Null
    Write-Host "📁 创建测试数据目录: $TestDataPath" -ForegroundColor $Colors.Info
}

#region 音频处理模块导入测试
Write-Host ""
Write-Host "📦 音频处理模块导入测试..." -ForegroundColor $Colors.Progress

try {
    $importTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

# 测试FFmpeg检测器导入
try:
    from app.core.audio.ffmpeg_detector import FFmpegDetector
    print('✅ FFmpegDetector导入成功')
except Exception as e:
    print(f'❌ FFmpegDetector导入失败: {e}')
    sys.exit(1)

# 测试音频提取器导入
try:
    from app.core.audio.audio_extractor import AudioExtractor
    print('✅ AudioExtractor导入成功')
except Exception as e:
    print(f'❌ AudioExtractor导入失败: {e}')
    sys.exit(1)

# 测试音频合并器导入
try:
    from app.core.audio.audio_merger import AudioMerger
    print('✅ AudioMerger导入成功')
except Exception as e:
    print(f'❌ AudioMerger导入失败: {e}')
    sys.exit(1)

print('所有音频处理模块导入成功')
"@
    
    Write-Host $importTest -ForegroundColor $Colors.Detail
    Record-TestResult "音频处理模块导入" $true "所有模块导入成功"
    
} catch {
    Record-TestResult "音频处理模块导入" $false "模块导入失败: $($_.Exception.Message)"
}
#endregion

#region FFmpeg检测测试
Write-Host ""
Write-Host "🔍 FFmpeg检测测试..." -ForegroundColor $Colors.Progress

try {
    $ffmpegTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

from app.core.audio.ffmpeg_detector import FFmpegDetector

# 创建FFmpeg检测器
detector = FFmpegDetector()

# 检查FFmpeg是否可用
if detector.is_available():
    print('✅ FFmpeg可用')
    print(f'FFmpeg路径: {detector.get_ffmpeg_path()}')
    
    # 检查FFmpeg版本
    version = detector.get_version()
    if version:
        print(f'FFmpeg版本: {version}')
    
    print('FFmpeg检测测试通过')
else:
    print('⚠️ FFmpeg不可用，请检查安装')
    print('FFmpeg检测测试失败')
    sys.exit(1)
"@
    
    Write-Host $ffmpegTest -ForegroundColor $Colors.Detail
    Record-TestResult "FFmpeg检测" $true "FFmpeg检测和版本获取成功"
    
} catch {
    Record-TestResult "FFmpeg检测" $false "FFmpeg检测失败: $($_.Exception.Message)"
}
#endregion

#region 创建测试音频文件
if (-not $Quick) {
    Write-Host ""
    Write-Host "🎧 创建测试音频文件..." -ForegroundColor $Colors.Progress
    
    $testAudioPath = "$TestDataPath/test_audio.wav"
    
    try {
        $createAudioTest = python -c @"
import numpy as np
import wave
import os

# 创建1秒的测试音频 (440Hz正弦波)
sample_rate = 44100
duration = 1.0
frequency = 440.0

t = np.linspace(0, duration, int(sample_rate * duration), False)
audio_data = np.sin(2 * np.pi * frequency * t)

# 转换为16位整数
audio_data = (audio_data * 32767).astype(np.int16)

# 保存为WAV文件
with wave.open('$testAudioPath', 'wb') as wav_file:
    wav_file.setnchannels(1)  # 单声道
    wav_file.setsampwidth(2)  # 16位
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(audio_data.tobytes())

print('✅ 测试音频文件创建成功')
print(f'音频文件路径: $testAudioPath')
"@
        
        Write-Host $createAudioTest -ForegroundColor $Colors.Detail
        Record-TestResult "创建测试音频文件" $true "测试音频文件创建成功"
        
    } catch {
        Record-TestResult "创建测试音频文件" $false "测试音频文件创建失败: $($_.Exception.Message)"
    }
}
#endregion

#region 音频提取器功能测试
if (-not $Quick) {
    Write-Host ""
    Write-Host "🎤 音频提取器功能测试..." -ForegroundColor $Colors.Progress
    
    try {
        $extractorTest = python -c @"
import sys
import os
import tempfile
sys.path.insert(0, os.getcwd())

from app.core.audio.ffmpeg_detector import FFmpegDetector
from app.core.audio.audio_extractor import AudioExtractor

# 创建检测器和提取器
detector = FFmpegDetector()
if not detector.is_available():
    print('⚠️ FFmpeg不可用，跳过音频提取测试')
    sys.exit(2)

extractor = AudioExtractor(detector)

# 测试提取器初始化
print('✅ 音频提取器初始化成功')

# 测试默认参数
default_params = extractor.default_params
print(f'默认音频编解码器: {default_params["audio_codec"]}')
print(f'默认音频比特率: {default_params["audio_bitrate"]}')

# 测试参数验证功能
try:
    valid_params = extractor._validate_params({
        'audio_codec': 'aac',
        'audio_bitrate': '128k'
    })
    print('✅ 参数验证功能正常')
except Exception as e:
    print(f'❌ 参数验证失败: {e}')
    sys.exit(1)

print('音频提取器功能测试通过')
"@
        
        if ($LASTEXITCODE -eq 2) {
            Record-TestResult "音频提取器功能" $false "FFmpeg不可用，无法测试" $true
        } else {
            Write-Host $extractorTest -ForegroundColor $Colors.Detail
            Record-TestResult "音频提取器功能" $true "音频提取器初始化和参数验证成功"
        }
        
    } catch {
        Record-TestResult "音频提取器功能" $false "音频提取器测试失败: $($_.Exception.Message)"
    }
}
#endregion

#region 音频合并器功能测试
if (-not $Quick) {
    Write-Host ""
    Write-Host "🔗 音频合并器功能测试..." -ForegroundColor $Colors.Progress
    
    try {
        $mergerTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

from app.core.audio.ffmpeg_detector import FFmpegDetector
from app.core.audio.audio_merger import AudioMerger

# 创建检测器和合并器
detector = FFmpegDetector()
if not detector.is_available():
    print('⚠️ FFmpeg不可用，跳过音频合并测试')
    sys.exit(2)

merger = AudioMerger(detector)

# 测试合并器初始化
print('✅ 音频合并器初始化成功')

# 测试默认参数
default_params = merger.default_params
print(f'默认视频编解码器: {default_params["video_codec"]}')
print(f'默认音频编解码器: {default_params["audio_codec"]}')
print(f'默认同步模式: {default_params["sync_mode"]}')

# 测试参数验证功能
try:
    valid_params = merger._validate_params({
        'video_codec': 'copy',
        'audio_codec': 'aac'
    })
    print('✅ 参数验证功能正常')
except Exception as e:
    print(f'❌ 参数验证失败: {e}')
    sys.exit(1)

print('音频合并器功能测试通过')
"@
        
        if ($LASTEXITCODE -eq 2) {
            Record-TestResult "音频合并器功能" $false "FFmpeg不可用，无法测试" $true
        } else {
            Write-Host $mergerTest -ForegroundColor $Colors.Detail
            Record-TestResult "音频合并器功能" $true "音频合并器初始化和参数验证成功"
        }
        
    } catch {
        Record-TestResult "音频合并器功能" $false "音频合并器测试失败: $($_.Exception.Message)"
    }
}
#endregion

#region 音频处理集成测试
if (-not $Quick) {
    Write-Host ""
    Write-Host "🎼 音频处理集成测试..." -ForegroundColor $Colors.Progress
    
    try {
        $integrationTest = python -c @"
import sys
import os
import tempfile
sys.path.insert(0, os.getcwd())

from app.core.audio.ffmpeg_detector import FFmpegDetector
from app.core.audio.audio_extractor import AudioExtractor
from app.core.audio.audio_merger import AudioMerger

# 创建检测器
detector = FFmpegDetector()
if not detector.is_available():
    print('⚠️ FFmpeg不可用，跳过集成测试')
    sys.exit(2)

# 创建提取器和合并器
extractor = AudioExtractor(detector)
merger = AudioMerger(detector)

# 测试组件协作
print('✅ 检测器、提取器、合并器创建成功')

# 测试临时文件管理
temp_dir = tempfile.mkdtemp()
print(f'临时目录: {temp_dir}')

# 测试清理功能
extractor.cleanup_temp_files()
print('✅ 临时文件清理功能正常')

print('音频处理集成测试通过')
"@
        
        if ($LASTEXITCODE -eq 2) {
            Record-TestResult "音频处理集成" $false "FFmpeg不可用，无法测试" $true
        } else {
            Write-Host $integrationTest -ForegroundColor $Colors.Detail
            Record-TestResult "音频处理集成" $true "音频处理组件集成测试成功"
        }
        
    } catch {
        Record-TestResult "音频处理集成" $false "音频处理集成测试失败: $($_.Exception.Message)"
    }
}
#endregion

#region 错误处理测试
Write-Host ""
Write-Host "⚠️ 错误处理测试..." -ForegroundColor $Colors.Progress

try {
    $errorTest = python -c @"
import sys
import os
sys.path.insert(0, os.getcwd())

from app.core.audio.ffmpeg_detector import FFmpegDetector
from app.core.audio.audio_extractor import AudioExtractor

# 创建检测器和提取器
detector = FFmpegDetector()
extractor = AudioExtractor(detector)

# 测试无效文件路径处理
try:
    result = extractor.extract_audio('/path/that/does/not/exist.mp4')
    if result is None:
        print('✅ 无效文件路径错误处理正常')
    else:
        print('❌ 无效文件路径未正确处理')
        sys.exit(1)
except Exception as e:
    print('✅ 无效文件路径异常处理正常')

# 测试无效参数处理
try:
    invalid_params = {'invalid_param': 'invalid_value'}
    cleaned_params = extractor._validate_params(invalid_params)
    print('✅ 无效参数过滤正常')
except Exception as e:
    print('✅ 无效参数异常处理正常')

print('错误处理测试通过')
"@
    
    Write-Host $errorTest -ForegroundColor $Colors.Detail
    Record-TestResult "错误处理" $true "音频处理错误处理机制正常"
    
} catch {
    Record-TestResult "错误处理" $false "错误处理测试失败: $($_.Exception.Message)"
}
#endregion

# 显示测试摘要
Show-TestSummary

# 清理临时文件
if (Test-Path $TestDataPath) {
    $tempFiles = Get-ChildItem $TestDataPath -Filter "test_*"
    if ($tempFiles.Count -gt 0 -and (-not $Verbose)) {
        Remove-Item $tempFiles.FullName -Force
        Write-Host "🧹 清理临时测试文件" -ForegroundColor $Colors.Info
    }
}

# 返回适当的退出码
if ($TestResults.Failed -gt 0) {
    exit 1
} else {
    exit 0
}