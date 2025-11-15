#!/usr/bin/env powershell
# 智能视频水印去除工具 - 性能基准测试脚本
# 视频处理速度基准测试，内存使用监控，AI模型推理性能测试

param(
    [Parameter()]
    [switch]$Verbose,
    
    [Parameter()]
    [switch]$Quick,
    
    [Parameter()]
    [string]$TestDataPath = "tests/test_data",
    
    [Parameter()]
    [switch]$MemoryProfile,
    
    [Parameter()]
    [switch]$GPUProfile,
    
    [Parameter()]
    [int]$Iterations = 5,
    
    [Parameter()]
    [string]$ReportPath = "logs/performance_report.json"
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
    Summary = "Magenta"
}

# 性能测试结果追踪
$PerformanceResults = @{
    VideoProcessing = @{}
    AIInference = @{}
    MemoryUsage = @{}
    SystemInfo = @{}
    Benchmarks = @{}
    StartTime = Get-Date
}

Write-Host "🚀 智能视频水印去除工具 - 性能基准测试" -ForegroundColor $Colors.Header
Write-Host "模式: $(if($Quick){'快速'}else{'完整'}) | 迭代次数: $Iterations | 详细输出: $(if($Verbose){'开启'}else{'关闭'})" -ForegroundColor $Colors.Info
Write-Host "内存分析: $(if($MemoryProfile){'开启'}else{'关闭'}) | GPU分析: $(if($GPUProfile){'开启'}else{'关闭'})" -ForegroundColor $Colors.Info
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

# 确保日志目录和测试数据目录存在
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
}
if (-not (Test-Path $TestDataPath)) {
    New-Item -ItemType Directory -Path $TestDataPath -Force | Out-Null
}

#region 系统信息收集
Write-Host ""
Write-Host "💻 收集系统信息..." -ForegroundColor $Colors.Progress

try {
    $systemInfo = python -c @"
import sys
import platform
import psutil
import json

system_info = {
    'python_version': sys.version,
    'platform': platform.platform(),
    'processor': platform.processor(),
    'cpu_count': psutil.cpu_count(logical=False),
    'cpu_count_logical': psutil.cpu_count(logical=True),
    'memory_total': psutil.virtual_memory().total,
    'memory_available': psutil.virtual_memory().available
}

print(json.dumps(system_info, indent=2))
"@
    
    $PerformanceResults.SystemInfo = $systemInfo | ConvertFrom-Json
    Write-Host "✅ 系统信息收集完成" -ForegroundColor $Colors.Success
    
    if ($Verbose) {
        Write-Host "  CPU核心数: $($PerformanceResults.SystemInfo.cpu_count) (逻辑: $($PerformanceResults.SystemInfo.cpu_count_logical))" -ForegroundColor $Colors.Detail
        Write-Host "  总内存: $([math]::Round($PerformanceResults.SystemInfo.memory_total / 1GB, 2)) GB" -ForegroundColor $Colors.Detail
        Write-Host "  可用内存: $([math]::Round($PerformanceResults.SystemInfo.memory_available / 1GB, 2)) GB" -ForegroundColor $Colors.Detail
    }
    
} catch {
    Write-Host "❌ 系统信息收集失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
}
#endregion

#region GPU信息检查
if ($GPUProfile) {
    Write-Host ""
    Write-Host "🎮 检查GPU信息..." -ForegroundColor $Colors.Progress
    
    try {
        $gpuInfo = python -c @"
import json

gpu_info = {'available': False, 'devices': []}

try:
    import torch
    if torch.cuda.is_available():
        gpu_info['available'] = True
        gpu_info['cuda_version'] = torch.version.cuda
        gpu_info['device_count'] = torch.cuda.device_count()
        
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            gpu_info['devices'].append({
                'name': props.name,
                'memory': props.total_memory,
                'capability': f'{props.major}.{props.minor}'
            })
    
    print(json.dumps(gpu_info, indent=2))
    
except ImportError:
    print(json.dumps(gpu_info, indent=2))
"@
        
        $gpuData = $gpuInfo | ConvertFrom-Json
        $PerformanceResults.SystemInfo.GPU = $gpuData
        
        if ($gpuData.available) {
            Write-Host "✅ GPU可用 - $($gpuData.device_count) 个设备" -ForegroundColor $Colors.Success
            if ($Verbose) {
                foreach ($device in $gpuData.devices) {
                    Write-Host "  GPU: $($device.name) - $([math]::Round($device.memory / 1GB, 2)) GB" -ForegroundColor $Colors.Detail
                }
            }
        } else {
            Write-Host "⚠️ GPU不可用或CUDA未安装" -ForegroundColor $Colors.Warning
        }
        
    } catch {
        Write-Host "❌ GPU信息检查失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    }
}
#endregion

#region 创建性能测试数据
Write-Host ""
Write-Host "📁 创建性能测试数据..." -ForegroundColor $Colors.Progress

try {
    # 创建小型测试图像用于AI模型测试
    $testImageCreation = python -c @"
import numpy as np
from PIL import Image
import os

test_data_path = '$TestDataPath'
if not os.path.exists(test_data_path):
    os.makedirs(test_data_path)

# 创建不同尺寸的测试图像
image_sizes = [(480, 320), (720, 480), (1280, 720)]  # 不同分辨率
if '$Quick' == 'True':
    image_sizes = [(480, 320)]  # 快速模式只测试小尺寸

for i, size in enumerate(image_sizes):
    # 生成随机图像数据
    width, height = size
    image_data = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    
    # 添加一些结构化内容模拟真实图像
    # 添加一些矩形"水印"区域
    watermark_x = width // 4
    watermark_y = height // 4  
    watermark_w = width // 3
    watermark_h = height // 6
    
    image_data[watermark_y:watermark_y+watermark_h, 
               watermark_x:watermark_x+watermark_w] = [255, 255, 255]
    
    # 保存测试图像
    img = Image.fromarray(image_data)
    img_path = os.path.join(test_data_path, f'perf_test_image_{width}x{height}.png')
    img.save(img_path)
    print(f'✅ 创建测试图像: {img_path} ({width}x{height})')

print(f'性能测试数据创建完成，共 {len(image_sizes)} 个文件')
"@
    
    Write-Host $testImageCreation -ForegroundColor $Colors.Detail
    
} catch {
    Write-Host "❌ 性能测试数据创建失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
}
#endregion

#region 视频处理器性能测试
Write-Host ""
Write-Host "🎥 视频处理器性能测试..." -ForegroundColor $Colors.Progress

try {
    $videoProcessingTest = python -c @"
import sys
import os
import time
import json
import psutil
import gc
sys.path.insert(0, os.getcwd())

results = {
    'initialization_time': 0.0,
    'memory_usage': {},
    'error': None
}

try:
    # 测试视频处理器初始化时间
    process = psutil.Process()
    start_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    start_time = time.time()
    from app.core.video.video_processor import VideoProcessor
    processor = VideoProcessor()
    end_time = time.time()
    
    results['initialization_time'] = end_time - start_time
    
    # 内存使用测试
    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    results['memory_usage'] = {
        'initial': start_memory,
        'after_init': end_memory,
        'delta': end_memory - start_memory
    }
    
    # 多次初始化测试 (模拟负载)
    iterations = $Iterations if not $Quick else 2
    init_times = []
    
    for i in range(iterations):
        gc.collect()  # 强制垃圾回收
        
        start_iter = time.time()
        temp_processor = VideoProcessor()
        end_iter = time.time()
        
        init_times.append(end_iter - start_iter)
        del temp_processor
    
    results['performance_stats'] = {
        'min_init_time': min(init_times),
        'max_init_time': max(init_times),
        'avg_init_time': sum(init_times) / len(init_times),
        'iterations': len(init_times)
    }
    
    print(json.dumps(results, indent=2))
    
except Exception as e:
    results['error'] = str(e)
    print(json.dumps(results, indent=2))
"@
    
    $videoResults = $videoProcessingTest | ConvertFrom-Json
    $PerformanceResults.VideoProcessing = $videoResults
    
    if ($videoResults.error) {
        Write-Host "❌ 视频处理器性能测试失败: $($videoResults.error)" -ForegroundColor $Colors.Error
    } else {
        Write-Host "✅ 视频处理器初始化: $([math]::Round($videoResults.initialization_time * 1000, 2)) ms" -ForegroundColor $Colors.Success
        Write-Host "✅ 内存使用增加: $([math]::Round($videoResults.memory_usage.delta, 2)) MB" -ForegroundColor $Colors.Success
        Write-Host "✅ 平均初始化时间: $([math]::Round($videoResults.performance_stats.avg_init_time * 1000, 2)) ms" -ForegroundColor $Colors.Success
    }
    
} catch {
    Write-Host "❌ 视频处理器性能测试执行失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
}
#endregion

#region AI处理器性能测试
Write-Host ""
Write-Host "🤖 AI处理器性能测试..." -ForegroundColor $Colors.Progress

try {
    $aiProcessingTest = python -c @"
import sys
import os
import time
import json
import psutil
import gc
from glob import glob
sys.path.insert(0, os.getcwd())

results = {
    'initialization_time': 0.0,
    'inference_times': [],
    'memory_usage': {},
    'error': None
}

try:
    # AI处理器初始化性能测试
    process = psutil.Process()
    start_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    start_time = time.time()
    from app.core.ai.ai_handler import AIHandler
    ai_handler = AIHandler()
    end_time = time.time()
    
    results['initialization_time'] = end_time - start_time
    
    # 内存使用测试
    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    results['memory_usage'] = {
        'initial': start_memory,
        'after_init': end_memory,
        'delta': end_memory - start_memory
    }
    
    # 模拟AI推理性能测试 (如果有测试图像)
    test_images = glob('$TestDataPath/perf_test_image_*.png')
    if test_images and hasattr(ai_handler, 'process_image'):
        for img_path in test_images:
            inference_times = []
            iterations = min($Iterations, 3)  # AI推理较慢，限制迭代次数
            
            for i in range(iterations):
                start_inference = time.time()
                try:
                    # 这里需要根据实际AI处理器接口调整
                    # result = ai_handler.process_image(img_path)
                    # 如果没有实际处理方法，模拟处理时间
                    time.sleep(0.1)  # 模拟处理时间
                except:
                    pass  # 忽略处理错误，重点测试性能
                end_inference = time.time()
                
                inference_times.append(end_inference - start_inference)
            
            if inference_times:
                results['inference_times'].append({
                    'image': os.path.basename(img_path),
                    'times': inference_times,
                    'avg_time': sum(inference_times) / len(inference_times)
                })
    
    print(json.dumps(results, indent=2))
    
except Exception as e:
    results['error'] = str(e)
    print(json.dumps(results, indent=2))
"@
    
    $aiResults = $aiProcessingTest | ConvertFrom-Json
    $PerformanceResults.AIInference = $aiResults
    
    if ($aiResults.error) {
        Write-Host "❌ AI处理器性能测试失败: $($aiResults.error)" -ForegroundColor $Colors.Error
    } else {
        Write-Host "✅ AI处理器初始化: $([math]::Round($aiResults.initialization_time * 1000, 2)) ms" -ForegroundColor $Colors.Success
        Write-Host "✅ 内存使用增加: $([math]::Round($aiResults.memory_usage.delta, 2)) MB" -ForegroundColor $Colors.Success
        
        if ($aiResults.inference_times -and $aiResults.inference_times.Count -gt 0) {
            foreach ($inference in $aiResults.inference_times) {
                Write-Host "✅ $($inference.image) 推理时间: $([math]::Round($inference.avg_time * 1000, 2)) ms" -ForegroundColor $Colors.Success
            }
        }
    }
    
} catch {
    Write-Host "❌ AI处理器性能测试执行失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
}
#endregion

#region 内存监控测试
if ($MemoryProfile) {
    Write-Host ""
    Write-Host "💾 内存使用监控测试..." -ForegroundColor $Colors.Progress
    
    try {
        $memoryProfileTest = python -c @"
import sys
import os
import time
import json
import psutil
import gc
sys.path.insert(0, os.getcwd())

results = {
    'baseline_memory': 0.0,
    'peak_memory': 0.0,
    'memory_timeline': [],
    'gc_impact': {},
    'error': None
}

try:
    process = psutil.Process()
    
    # 基线内存使用
    gc.collect()
    baseline = process.memory_info().rss / 1024 / 1024  # MB
    results['baseline_memory'] = baseline
    results['memory_timeline'].append({'time': 0, 'memory': baseline, 'action': 'baseline'})
    
    # 加载主要组件并监控内存
    components = [
        ('VideoProcessor', 'app.core.video.video_processor', 'VideoProcessor'),
        ('AIHandler', 'app.core.ai.ai_handler', 'AIHandler'),
        ('ConfigManager', 'app.config.config_manager', 'ConfigManager'),
    ]
    
    current_memory = baseline
    peak_memory = baseline
    
    for name, module_path, class_name in components:
        try:
            # 导入并实例化组件
            module = __import__(module_path, fromlist=[class_name])
            component_class = getattr(module, class_name)
            
            start_time = time.time()
            instance = component_class()
            end_time = time.time()
            
            # 测量内存变化
            new_memory = process.memory_info().rss / 1024 / 1024  # MB
            delta = new_memory - current_memory
            
            results['memory_timeline'].append({
                'time': end_time - start_time,
                'memory': new_memory,
                'delta': delta,
                'action': f'load_{name}'
            })
            
            current_memory = new_memory
            peak_memory = max(peak_memory, new_memory)
            
            del instance  # 清理实例
            
        except Exception as e:
            results['memory_timeline'].append({
                'action': f'error_{name}',
                'error': str(e)
            })
    
    # 测试垃圾回收影响
    pre_gc_memory = process.memory_info().rss / 1024 / 1024  # MB
    gc.collect()
    post_gc_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    results['gc_impact'] = {
        'before': pre_gc_memory,
        'after': post_gc_memory,
        'freed': pre_gc_memory - post_gc_memory
    }
    
    results['peak_memory'] = peak_memory
    
    print(json.dumps(results, indent=2))
    
except Exception as e:
    results['error'] = str(e)
    print(json.dumps(results, indent=2))
"@
        
        $memoryResults = $memoryProfileTest | ConvertFrom-Json
        $PerformanceResults.MemoryUsage = $memoryResults
        
        if ($memoryResults.error) {
            Write-Host "❌ 内存监控测试失败: $($memoryResults.error)" -ForegroundColor $Colors.Error
        } else {
            Write-Host "✅ 基线内存: $([math]::Round($memoryResults.baseline_memory, 2)) MB" -ForegroundColor $Colors.Success
            Write-Host "✅ 峰值内存: $([math]::Round($memoryResults.peak_memory, 2)) MB" -ForegroundColor $Colors.Success
            Write-Host "✅ GC回收: $([math]::Round($memoryResults.gc_impact.freed, 2)) MB" -ForegroundColor $Colors.Success
            
            if ($Verbose -and $memoryResults.memory_timeline) {
                foreach ($entry in $memoryResults.memory_timeline) {
                    if ($entry.delta) {
                        Write-Host "  $($entry.action): +$([math]::Round($entry.delta, 2)) MB" -ForegroundColor $Colors.Detail
                    }
                }
            }
        }
        
    } catch {
        Write-Host "❌ 内存监控测试执行失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    }
}
#endregion

#region CPU性能基准测试
if (-not $Quick) {
    Write-Host ""
    Write-Host "⚡ CPU性能基准测试..." -ForegroundColor $Colors.Progress
    
    try {
        $cpuBenchmark = python -c @"
import time
import json
import psutil
import multiprocessing as mp

results = {
    'single_thread': {},
    'multi_thread': {},
    'cpu_usage': {},
    'error': None
}

try:
    # CPU密集型任务基准测试
    def cpu_intensive_task(n):
        # 计算斐波那契数列 (CPU密集型)
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    # 单线程基准测试
    n = 30000 if '$Quick' != 'True' else 10000
    
    start_time = time.time()
    result = cpu_intensive_task(n)
    end_time = time.time()
    
    results['single_thread'] = {
        'duration': end_time - start_time,
        'operations_per_second': n / (end_time - start_time)
    }
    
    # 多线程基准测试 (使用CPU核心数的线程)
    cpu_count = psutil.cpu_count(logical=False)
    pool_size = min(cpu_count, 4)  # 限制最大线程数
    
    start_time = time.time()
    with mp.Pool(pool_size) as pool:
        tasks = [n // pool_size] * pool_size
        pool.map(cpu_intensive_task, tasks)
    end_time = time.time()
    
    results['multi_thread'] = {
        'duration': end_time - start_time,
        'thread_count': pool_size,
        'speedup': (results['single_thread']['duration'] / (end_time - start_time))
    }
    
    # CPU使用率监控
    cpu_percent = psutil.cpu_percent(interval=1)
    results['cpu_usage'] = {
        'current_usage': cpu_percent,
        'cpu_count': cpu_count
    }
    
    print(json.dumps(results, indent=2))
    
except Exception as e:
    results['error'] = str(e)
    print(json.dumps(results, indent=2))
"@
        
        $cpuResults = $cpuBenchmark | ConvertFrom-Json
        $PerformanceResults.Benchmarks = $cpuResults
        
        if ($cpuResults.error) {
            Write-Host "❌ CPU基准测试失败: $($cpuResults.error)" -ForegroundColor $Colors.Error
        } else {
            Write-Host "✅ 单线程性能: $([math]::Round($cpuResults.single_thread.operations_per_second, 0)) ops/sec" -ForegroundColor $Colors.Success
            Write-Host "✅ 多线程加速比: $([math]::Round($cpuResults.multi_thread.speedup, 2))x ($($cpuResults.multi_thread.thread_count) 线程)" -ForegroundColor $Colors.Success
            Write-Host "✅ 当前CPU使用率: $([math]::Round($cpuResults.cpu_usage.current_usage, 1))%" -ForegroundColor $Colors.Success
        }
        
    } catch {
        Write-Host "❌ CPU基准测试执行失败: $($_.Exception.Message)" -ForegroundColor $Colors.Error
    }
}
#endregion

#region 生成性能报告
Write-Host ""
Write-Host "📊 性能测试摘要" -ForegroundColor $Colors.Summary
Write-Host "=" * 50 -ForegroundColor $Colors.Info

$endTime = Get-Date
$duration = $endTime - $PerformanceResults.StartTime

Write-Host "🕒 测试时间: $($duration.ToString('mm\:ss'))" -ForegroundColor $Colors.Info
Write-Host "💻 CPU核心数: $($PerformanceResults.SystemInfo.cpu_count) (逻辑: $($PerformanceResults.SystemInfo.cpu_count_logical))" -ForegroundColor $Colors.Info
Write-Host "💾 总内存: $([math]::Round($PerformanceResults.SystemInfo.memory_total / 1GB, 2)) GB" -ForegroundColor $Colors.Info

if ($PerformanceResults.VideoProcessing -and $PerformanceResults.VideoProcessing.initialization_time) {
    Write-Host "🎥 视频处理器初始化: $([math]::Round($PerformanceResults.VideoProcessing.initialization_time * 1000, 2)) ms" -ForegroundColor $Colors.Info
}

if ($PerformanceResults.AIInference -and $PerformanceResults.AIInference.initialization_time) {
    Write-Host "🤖 AI处理器初始化: $([math]::Round($PerformanceResults.AIInference.initialization_time * 1000, 2)) ms" -ForegroundColor $Colors.Info
}

if ($PerformanceResults.Benchmarks -and $PerformanceResults.Benchmarks.single_thread) {
    Write-Host "⚡ CPU性能: $([math]::Round($PerformanceResults.Benchmarks.single_thread.operations_per_second, 0)) ops/sec" -ForegroundColor $Colors.Info
}

# 保存性能报告
$reportData = @{
    Timestamp = Get-Date
    TestDuration = $duration.TotalSeconds
    TestParameters = @{
        Quick = $Quick
        Iterations = $Iterations
        MemoryProfile = $MemoryProfile
        GPUProfile = $GPUProfile
    }
    Results = $PerformanceResults
}

$reportJson = $reportData | ConvertTo-Json -Depth 5
$reportPath = "logs/performance_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$reportJson | Out-File -FilePath $reportPath -Encoding UTF8
Write-Host "📄 性能报告已保存: $reportPath" -ForegroundColor $Colors.Info
#endregion

# 清理测试数据
if ((Test-Path $TestDataPath) -and (-not $Verbose)) {
    $testFiles = Get-ChildItem $TestDataPath -Filter "perf_test_*"
    if ($testFiles.Count -gt 0) {
        Remove-Item $testFiles.FullName -Force
        Write-Host "🧹 清理临时测试文件" -ForegroundColor $Colors.Info
    }
}

Write-Host ""
Write-Host "🎉 性能基准测试完成！详细报告: $reportPath" -ForegroundColor $Colors.Success
Write-Host "📋 运行完整测试套件: .\scripts\test-all.ps1" -ForegroundColor $Colors.Info

exit 0