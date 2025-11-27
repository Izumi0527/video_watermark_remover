# Phase 4 Stage 2.1: 多进程帧并行处理 - 详细设计文档

**创建时间**: 2025-11-15
**状态**: 🎨 设计阶段
**预计时间**: 16小时
**目标**: 单文件处理速度从 15 fps 提升到 45 fps (+200%)

---

## 📋 需求分析

### 当前性能瓶颈

**Stage 1 后的处理流程**:
```
读取视频帧 (OpenCV VideoCapture)
    ↓ 串行
AI 处理每一帧 (受 Python GIL 限制)
    ↓ 串行
写入处理后的帧 (OpenCV VideoWriter)
```

**性能指标**:
- 处理速度: 15 fps
- 1000 帧视频: 66.7 秒
- CPU 利用率: 25% (单线程,受 GIL 限制)

**根本问题**: Python GIL (Global Interpreter Lock) 限制了 CPU 密集型任务的多线程并行。

### 解决方案对比

#### 方案 A: 队列模式(生产者-消费者) ❌

```
主线程(读取) → 输入队列 → [进程池] → 输出队列 → 主线程(写入)
```

**优点**:
- ✅ 经典模式,理论完善
- ✅ 负载均衡自动

**缺点**:
- ❌ 需要管理两个队列(输入、输出)
- ❌ 帧顺序打乱,需要复杂的重排逻辑
- ❌ 进程间通信开销大(序列化 numpy 数组)
- ❌ 代码复杂度高,容易出错

#### 方案 B: 分块批处理(推荐) ✅

```
视频(1000帧)
    ├─ 进程1: 帧 0-249   → temp_0.mp4
    ├─ 进程2: 帧 250-499 → temp_1.mp4
    ├─ 进程3: 帧 500-749 → temp_2.mp4
    └─ 进程4: 帧 750-999 → temp_3.mp4
            ↓
    FFmpeg concat
            ↓
      final_output.mp4
```

**优点**:
- ✅ 无需队列,避免进程间通信
- ✅ 自然保证顺序(块内有序,块间有序)
- ✅ 代码简单,易于理解和维护
- ✅ 适合视频这种顺序数据

**缺点**:
- ⚠️ 每个进程独立读取视频(4x I/O 开销)
- ⚠️ 需要 FFmpeg 合并视频块

**选择**: 方案 B (分块批处理),优点远大于缺点。

---

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                       VideoProcessorThread                   │
│                       (主线程,QThread)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  enable_multiprocess = True
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   Process 1   │     │   Process 2   │     │   Process 3   │ ...
│  Frames 0-249 │     │ Frames 250-499│     │ Frames 500-749│
└───────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
    temp_0.mp4            temp_1.mp4            temp_2.mp4
                              │
                    ┌─────────┴─────────┐
                    │  FFmpeg concat    │
                    └─────────┬─────────┘
                              │
                              ▼
                        final_output.mp4
```

### 核心组件

#### 1. 工作进程函数

```python
def process_video_chunk(
    video_path: str,
    start_frame: int,
    end_frame: int,
    output_path: str,
    ai_params: dict,
    config: ConfigParser,
    progress_queue: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
    chunk_id: int
) -> Tuple[str, bool, Optional[str]]:
    """
    处理视频块(在子进程中运行)

    Args:
        video_path: 输入视频路径
        start_frame: 起始帧索引
        end_frame: 结束帧索引
        output_path: 输出临时文件路径
        ai_params: AI 参数字典
        config: 配置对象
        progress_queue: 进度队列(发送进度信息到主线程)
        stop_event: 停止事件(主线程通知停止)
        chunk_id: 块ID(用于进度标识)

    Returns:
        (输出路径, 成功标志, 错误信息)
    """
    try:
        # 1. 在子进程中加载 AI 模型
        ai_handler = AIHandler(config, ai_params)
        if not ai_handler.load_models():
            return (None, False, "AI 模型加载失败")

        # 2. 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return (None, False, "无法打开视频文件")

        # 3. 获取视频参数
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

        # 4. 创建视频写入器
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 5. 定位到起始帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # 6. 逐帧处理
        total_frames_in_chunk = end_frame - start_frame
        for i in range(total_frames_in_chunk):
            # 检查停止事件
            if stop_event.is_set():
                break

            ret, frame = cap.read()
            if not ret:
                break

            # AI 处理
            processed_frame, _ = ai_handler.process_frame(frame)

            # 写入
            out.write(processed_frame)

            # 发送进度(每10帧)
            if i % 10 == 0:
                progress_queue.put({
                    "chunk_id": chunk_id,
                    "current": i,
                    "total": total_frames_in_chunk,
                })

        # 7. 释放资源
        cap.release()
        out.release()

        return (output_path, True, None)

    except Exception as e:
        return (None, False, str(e))
```

#### 2. 分块策略

```python
def calculate_chunks(total_frames: int, num_processes: int) -> List[Tuple[int, int, str]]:
    """
    计算分块策略

    Args:
        total_frames: 总帧数
        num_processes: 进程数

    Returns:
        [(start_frame, end_frame, temp_output_path), ...]
    """
    chunk_size = total_frames // num_processes
    chunks = []

    for i in range(num_processes):
        start = i * chunk_size
        # 最后一个块包含剩余所有帧
        end = total_frames if i == num_processes - 1 else (i + 1) * chunk_size
        temp_path = f"temp_chunk_{i}.mp4"
        chunks.append((start, end, temp_path))

    return chunks
```

#### 3. 并行执行

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

def run_multiprocess(self):
    """在 VideoProcessorThread 中运行多进程处理"""

    # 1. 获取视频信息
    cap = cv2.VideoCapture(self.input_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    # 2. 确定进程数
    num_processes = min(multiprocessing.cpu_count(), 4)  # 最多4个进程

    # 3. 计算分块
    chunks = calculate_chunks(total_frames, num_processes)

    # 4. 创建进度队列和停止事件
    progress_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()

    # 5. 启动进度轮询定时器
    self._progress_timer = QTimer()
    self._progress_timer.timeout.connect(
        lambda: self._check_progress_queue(progress_queue)
    )
    self._progress_timer.start(100)  # 每100ms检查一次

    # 6. 并行处理
    temp_files = []
    try:
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = []
            for i, (start, end, temp_path) in enumerate(chunks):
                future = executor.submit(
                    process_video_chunk,
                    self.input_path,
                    start,
                    end,
                    temp_path,
                    self.ai_params,
                    self.config,
                    progress_queue,
                    stop_event,
                    i  # chunk_id
                )
                futures.append(future)
                temp_files.append(temp_path)

            # 收集结果
            results = []
            for future in as_completed(futures):
                output_path, success, error_msg = future.result()
                if not success:
                    self.logger.error(f"块处理失败: {error_msg}")
                results.append((output_path, success, error_msg))

        # 7. 检查是否所有块都成功
        failed_chunks = [r for r in results if not r[1]]
        if failed_chunks:
            raise Exception(f"{len(failed_chunks)} 个块处理失败")

        # 8. 合并视频块
        self._merge_video_chunks([r[0] for r in results], self.output_path)

        return self.output_path

    finally:
        # 9. 清理
        self._progress_timer.stop()
        stop_event.set()

        # 删除临时文件
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    self.logger.warning(f"删除临时文件失败: {e}")
```

#### 4. 进度轮询

```python
def _check_progress_queue(self, progress_queue: multiprocessing.Queue):
    """检查进度队列并发送信号"""
    try:
        while not progress_queue.empty():
            progress_data = progress_queue.get_nowait()

            chunk_id = progress_data["chunk_id"]
            current = progress_data["current"]
            total = progress_data["total"]

            # 计算总体进度
            # (假设4个进程,每个进程负责25%的帧)
            overall_progress = (chunk_id * 25) + int((current / total) * 25)

            # 发送 PyQt 信号
            self.progress.emit(overall_progress)
            self.status.emit(f"处理块 {chunk_id + 1}: {current}/{total} 帧")
    except Exception as e:
        self.logger.warning(f"进度轮询错误: {e}")
```

#### 5. FFmpeg 视频合并

```python
def _merge_video_chunks(self, chunk_paths: List[str], output_path: str):
    """使用 FFmpeg 合并视频块"""

    # 1. 创建 concat 列表文件
    concat_list_path = "concat_list.txt"
    with open(concat_list_path, "w") as f:
        for chunk_path in chunk_paths:
            # FFmpeg concat demuxer 要求绝对路径
            abs_path = os.path.abspath(chunk_path)
            f.write(f"file '{abs_path}'\n")

    # 2. 使用 FFmpeg concat demuxer 合并(无损、快速)
    ffmpeg_cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",  # 复制编码,不重新编码
        output_path,
        "-y"  # 覆盖已存在文件
    ]

    # 3. 执行 FFmpeg
    result = subprocess.run(
        ffmpeg_cmd,
        capture_output=True,
        text=True,
        timeout=30
    )

    # 4. 检查结果
    if result.returncode != 0:
        raise Exception(f"FFmpeg 合并失败: {result.stderr}")

    # 5. 删除 concat 列表文件
    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)

    self.logger.info(f"视频块合并完成: {output_path}")
```

---

## 🔧 实施细节

### 1. VideoProcessorThread 修改

**文件**: `app/core/video/video_processor.py`

#### 添加多进程模式开关

```python
class VideoProcessorThread(QThread):
    def __init__(
        self,
        input_path: str,
        output_path: str,
        ai_params: Optional[Dict[str, Any]],
        config: Optional[ConfigParser] = None,
        preloaded_ai_handler: Optional[AIHandler] = None,
        enable_multiprocess: bool = True,  # 新增: 是否启用多进程
        num_processes: Optional[int] = None,  # 新增: 进程数(None=自动检测)
        parent: Optional[QThread] = None,
    ):
        super().__init__(parent)
        # ... (其他初始化)

        self.enable_multiprocess = enable_multiprocess
        self.num_processes = num_processes or min(multiprocessing.cpu_count(), 4)
        self._progress_timer = None
        self._stop_event = None
```

#### 修改 run() 方法

```python
def run(self) -> None:
    try:
        self._start_time = time.time()

        # 判断文件类型
        file_ext = os.path.splitext(self.input_path)[1].lower()

        if file_ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            # 图片处理(单进程)
            self._process_image()
        else:
            # 视频处理
            if self.enable_multiprocess:
                # 多进程模式
                self._process_video_multiprocess()
            else:
                # 单进程模式(原有逻辑)
                self._process_video_singleprocess()

        self.finished.emit(self.output_path)

    except Exception as e:
        self.logger.error(f"处理失败: {e}")
        self.error.emit(str(e))
```

#### 新增多进程处理方法

```python
def _process_video_multiprocess(self):
    """多进程视频处理"""

    # 1. 获取视频信息
    cap = cv2.VideoCapture(self.input_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    self.status.emit(f"🚀 使用 {self.num_processes} 个进程并行处理 {total_frames} 帧")

    # 2. 计算分块
    chunks = self._calculate_chunks(total_frames, self.num_processes)

    # 3. 创建进度队列和停止事件
    progress_queue = multiprocessing.Queue()
    self._stop_event = multiprocessing.Event()

    # 4. 启动进度轮询
    self._progress_timer = QTimer()
    self._progress_timer.timeout.connect(
        lambda: self._check_progress_queue(progress_queue, total_frames)
    )
    self._progress_timer.start(100)

    # 5. 并行处理
    temp_files = []
    try:
        with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
            futures = []
            for i, (start, end, temp_path) in enumerate(chunks):
                future = executor.submit(
                    process_video_chunk,
                    self.input_path,
                    start,
                    end,
                    temp_path,
                    self.ai_params,
                    self.config,
                    progress_queue,
                    self._stop_event,
                    i
                )
                futures.append(future)
                temp_files.append(temp_path)

            # 收集结果
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # 6. 检查结果
        failed_chunks = [r for r in results if not r[1]]
        if failed_chunks:
            raise Exception(f"{len(failed_chunks)} 个块处理失败")

        # 7. 合并视频块
        chunk_paths = [r[0] for r in results if r[0] is not None]
        self.status.emit("🔗 正在合并视频块...")
        self._merge_video_chunks(chunk_paths, self.output_path)

        self.status.emit("✅ 多进程处理完成")

    finally:
        # 8. 清理
        if self._progress_timer:
            self._progress_timer.stop()
        if self._stop_event:
            self._stop_event.set()

        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    self.logger.warning(f"删除临时文件失败: {e}")
```

### 2. 模块级工作函数

**位置**: `app/core/video/video_processor.py` (在类定义外)

```python
def process_video_chunk(
    video_path: str,
    start_frame: int,
    end_frame: int,
    output_path: str,
    ai_params: dict,
    config: ConfigParser,
    progress_queue: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
    chunk_id: int
) -> Tuple[str, bool, Optional[str]]:
    """
    处理视频块(模块级函数,可被 multiprocessing 序列化)

    这个函数必须在模块级别定义,不能是类方法,
    因为 multiprocessing 需要能够 pickle 它。
    """
    # (实现见上面的详细代码)
    pass
```

### 3. 错误处理和降级

```python
def _process_video_multiprocess(self):
    """多进程视频处理(带降级机制)"""

    try:
        # 尝试多进程处理
        # ... (上面的代码)

    except Exception as e:
        self.logger.error(f"多进程处理失败,降级到单进程: {e}")

        # 降级到单进程处理
        self.status.emit("⚠️ 多进程失败,切换到单进程模式")
        self._process_video_singleprocess()
```

---

## 📊 性能分析

### 理论性能

**加速比计算**:
```
理想加速比 = 进程数 = 4
考虑 I/O 开销: 4 × 0.85 = 3.4
考虑进程启动开销: 3.4 × 0.95 = 3.23
考虑合并开销: 3.23 × 0.98 = 3.16

预期加速比: 3x
```

**性能预期**:
```
当前(Stage 1):
- 处理速度: 15 fps
- 1000 帧视频: 66.7 秒
- CPU 利用率: 25%

预期(Stage 2.1):
- 处理速度: 15 × 3 = 45 fps (超过目标 35 fps ✅)
- 1000 帧视频: 66.7 / 3 = 22.2 秒
- CPU 利用率: 90-95%
```

### 内存占用

```
每个进程:
- AI 模型: 40MB
- 帧缓冲(10帧): 60MB
- 其他: 20MB
小计: 120MB/进程

总计(4进程):
- 进程内存: 120MB × 4 = 480MB
- 主进程: 80MB
- 总计: 560MB

增加量: +400MB (相比 Stage 1 的 160MB)
评估: 可接受(现代计算机通常 8GB+ 内存)
```

### I/O 开销分析

**单进程 I/O**:
```
读取: 1 × 视频大小 = 100MB
写入: 1 × 视频大小 = 100MB
总计: 200MB
```

**多进程 I/O**:
```
读取: 4 × 视频大小 = 400MB (每个进程独立读取)
写入: 4 × 临时文件 = 400MB
合并: 读取 400MB + 写入 100MB = 500MB
总计: 1300MB

开销增加: 6.5x
```

**缓解措施**:
1. 使用 SSD(随机读取性能好)
2. 限制帧缓冲大小(减少内存-磁盘交换)
3. 使用 FFmpeg concat demuxer(复制模式,无重编码)

---

## ⚠️ 风险与缓解

### 高风险项

#### 1. AI 模型在子进程加载失败

**风险描述**: AI 模型包含 CUDA 张量、C++ 对象,可能无法在子进程正确初始化。

**概率**: 中等

**影响**: 功能完全失效

**缓解措施**:
- 充分测试 AI 模型在子进程的加载
- 提供详细的错误日志
- 实现降级机制(失败时切换到单进程)

**测试计划**:
```python
# 单独测试子进程加载 AI 模型
def test_ai_model_in_subprocess():
    from multiprocessing import Process

    def load_ai():
        ai_handler = AIHandler(config, ai_params={})
        success = ai_handler.load_models()
        print(f"AI 加载: {'成功' if success else '失败'}")

    p = Process(target=load_ai)
    p.start()
    p.join()
```

#### 2. FFmpeg 合并失败

**风险描述**: 不同块的编码参数不一致,导致 concat 失败。

**概率**: 低(确保参数一致)

**影响**: 需要重新编码,增加 30 秒开销

**缓解措施**:
- 严格控制编码参数(所有块使用相同的 fourcc、fps、分辨率)
- 提供降级方案(使用 filter_complex 重新编码)

**降级代码**:
```python
def _merge_video_chunks_fallback(self, chunk_paths, output_path):
    """降级方案: 使用 filter_complex 重新编码合并"""
    inputs = " ".join([f"-i {p}" for p in chunk_paths])
    filter_str = f"concat=n={len(chunk_paths)}:v=1:a=0"

    ffmpeg_cmd = f"ffmpeg {inputs} -filter_complex {filter_str} {output_path} -y"
    # ... 执行
```

### 中风险项

#### 1. 内存占用超预期

**风险描述**: 560MB 内存占用可能在低端设备上造成问题。

**概率**: 低(现代设备通常 8GB+ 内存)

**影响**: 系统变慢,可能触发 OOM

**缓解措施**:
- 限制帧缓冲大小(最多 10 帧)
- 及时释放已处理的帧
- 检测可用内存,动态调整进程数

```python
import psutil

def get_optimal_num_processes() -> int:
    """根据可用内存动态调整进程数"""
    available_memory_gb = psutil.virtual_memory().available / (1024 ** 3)

    if available_memory_gb < 2:
        return 1  # 降级到单进程
    elif available_memory_gb < 4:
        return 2
    else:
        return min(multiprocessing.cpu_count(), 4)
```

#### 2. 用户取消时的资源清理

**风险描述**: 用户中途取消,临时文件残留。

**概率**: 中等

**影响**: 磁盘空间浪费

**缓解措施**:
- 完善的 try-finally 清理逻辑
- 使用 tempfile 模块创建临时文件(自动清理)

```python
import tempfile

def _create_temp_file(self, chunk_id: int) -> str:
    """创建临时文件"""
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"video_chunk_{chunk_id}_{os.getpid()}.mp4")
    return temp_path
```

### 低风险项

#### 1. 进度报告不准确

**风险描述**: 多进程进度汇总不准确。

**概率**: 低

**影响**: 用户体验略差,不影响功能

**缓解措施**:
- 使用加权平均计算总体进度
- 定期校准进度

---

## 🧪 测试计划

### 单元测试

#### 1. 分块策略测试

```python
def test_calculate_chunks():
    # 测试用例 1: 1000 帧,4 进程
    chunks = calculate_chunks(1000, 4)
    assert len(chunks) == 4
    assert chunks[0] == (0, 250, "temp_chunk_0.mp4")
    assert chunks[3] == (750, 1000, "temp_chunk_3.mp4")

    # 测试用例 2: 不能整除的情况
    chunks = calculate_chunks(1001, 4)
    assert chunks[3][1] == 1001  # 最后一个块包含剩余帧
```

#### 2. 工作函数测试

```python
def test_process_video_chunk():
    # 准备测试视频
    test_video = "test_data/sample_video.mp4"

    # 创建队列和事件
    progress_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()

    # 测试处理前 100 帧
    result = process_video_chunk(
        test_video,
        0, 100,
        "output_chunk.mp4",
        {},
        None,
        progress_queue,
        stop_event,
        0
    )

    assert result[1] == True  # 成功
    assert os.path.exists(result[0])  # 输出文件存在

    # 清理
    os.remove(result[0])
```

### 集成测试

#### 1. 端到端测试

```python
def test_multiprocess_video_processing():
    """完整的多进程处理测试"""

    # 1. 准备测试视频(100 帧)
    test_video = "test_data/100_frames.mp4"
    output_video = "output_multiprocess.mp4"

    # 2. 创建处理器
    processor = VideoProcessorThread(
        input_path=test_video,
        output_path=output_video,
        ai_params={},
        enable_multiprocess=True,
        num_processes=2
    )

    # 3. 运行处理(同步)
    processor.run()

    # 4. 验证输出
    assert os.path.exists(output_video)

    # 5. 验证帧数
    cap = cv2.VideoCapture(output_video)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    assert frame_count == 100
    cap.release()

    # 6. 清理
    os.remove(output_video)
```

#### 2. 性能基准测试

```python
import time

def test_performance_comparison():
    """对比单进程和多进程性能"""

    test_video = "test_data/1000_frames.mp4"

    # 单进程
    start = time.time()
    processor_single = VideoProcessorThread(
        test_video, "output_single.mp4",
        ai_params={}, enable_multiprocess=False
    )
    processor_single.run()
    single_time = time.time() - start

    # 多进程
    start = time.time()
    processor_multi = VideoProcessorThread(
        test_video, "output_multi.mp4",
        ai_params={}, enable_multiprocess=True
    )
    processor_multi.run()
    multi_time = time.time() - start

    # 计算加速比
    speedup = single_time / multi_time
    print(f"加速比: {speedup:.2f}x")
    assert speedup >= 2.0  # 至少 2x 加速

    # 清理
    os.remove("output_single.mp4")
    os.remove("output_multi.mp4")
```

### 压力测试

```python
def test_large_video():
    """测试大视频(5000 帧,1080p)"""
    # ...

def test_4k_video():
    """测试 4K 视频"""
    # ...

def test_memory_usage():
    """测试内存占用"""
    import psutil
    process = psutil.Process()

    # 记录处理前内存
    mem_before = process.memory_info().rss / (1024 ** 2)  # MB

    # 处理视频
    # ...

    # 记录处理后内存
    mem_after = process.memory_info().rss / (1024 ** 2)
    mem_increase = mem_after - mem_before

    assert mem_increase < 600  # 内存增加不超过 600MB
```

---

## 📝 实施检查清单

### 准备阶段

- [ ] 安装 psutil 库(内存检测)
- [ ] 准备测试视频(100帧、1000帧、5000帧)
- [ ] 验证 FFmpeg 可用性
- [ ] 确认 AI 模型可在子进程加载

### 开发阶段

#### 核心功能

- [ ] 实现 `process_video_chunk()` 工作函数
- [ ] 实现 `calculate_chunks()` 分块策略
- [ ] 修改 `VideoProcessorThread.__init__` 添加参数
- [ ] 实现 `_process_video_multiprocess()` 方法
- [ ] 实现 `_merge_video_chunks()` 合并方法
- [ ] 实现 `_check_progress_queue()` 进度轮询

#### 辅助功能

- [ ] 实现 `get_optimal_num_processes()` 动态进程数
- [ ] 实现 `_create_temp_file()` 临时文件创建
- [ ] 实现降级机制(多进程失败→单进程)
- [ ] 实现优雅停止(stop_event)
- [ ] 实现资源清理(try-finally)

### 测试阶段

#### 单元测试

- [ ] 测试分块策略
- [ ] 测试工作函数
- [ ] 测试进度汇总
- [ ] 测试 FFmpeg 合并

#### 集成测试

- [ ] 端到端测试(小视频 100 帧)
- [ ] 端到端测试(中视频 1000 帧)
- [ ] 性能对比测试
- [ ] 内存占用测试

#### 压力测试

- [ ] 大视频测试(5000 帧)
- [ ] 4K 视频测试
- [ ] 并发批量测试(10 个文件同时处理)

### 优化阶段

- [ ] 性能剖析(cProfile)
- [ ] 内存剖析(memory_profiler)
- [ ] 根据测试结果调优
- [ ] 文档更新

### 发布阶段

- [ ] 创建实施记录文档
- [ ] 更新用户文档
- [ ] Git 提交
- [ ] 性能测试报告

---

## 📚 参考资料

### Python Multiprocessing

- [Python multiprocessing 官方文档](https://docs.python.org/3/library/multiprocessing.html)
- [ProcessPoolExecutor 文档](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor)
- [Multiprocessing Best Practices](https://docs.python.org/3/library/multiprocessing.html#programming-guidelines)

### FFmpeg

- [FFmpeg concat demuxer](https://trac.ffmpeg.org/wiki/Concatenate)
- [FFmpeg filter_complex](https://ffmpeg.org/ffmpeg-filters.html#concat)

### PyQt6 与 Multiprocessing

- [Qt Signal/Slot Thread Safety](https://doc.qt.io/qt-6/threads-qobject.html)
- [QTimer 文档](https://doc.qt.io/qt-6/qtimer.html)

---

## 🎉 预期成果

### 性能提升

| 指标 | Stage 1 | Stage 2.1 预期 | 提升幅度 |
|------|---------|----------------|----------|
| **处理速度** | 15 fps | 45 fps | **+200%** |
| **1000帧视频** | 66.7秒 | 22.2秒 | **-67%** |
| **CPU利用率** | 25% | 95% | **+280%** |
| **加速比** | 1x | 3x | **3x** |

### 用户体验

- ✅ 视频处理速度显著提升
- ✅ 批量处理更高效(原 5分钟 → 现 1.7分钟)
- ✅ 充分利用多核 CPU
- ✅ 进度报告保持准确

### 技术价值

- ✅ 突破 Python GIL 限制
- ✅ 多进程并行处理范例
- ✅ 进程间通信最佳实践
- ✅ 资源管理和错误处理

---

**文档创建时间**: 2025-11-15
**作者**: 
**版本**: v1.0 (设计阶段)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
