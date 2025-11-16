# Phase 5: GPU 加速优化 - 总体规划

**规划日期**: 2025-11-16
**预计耗时**: 12-16 小时
**优先级**: 极高 (解锁 GPU 算力)
**依赖**: Phase 4 完成

---

## 📋 规划背景

### Phase 4 成果回顾

```
Phase 3 → Phase 4: 10 fps → 50.8 fps (+408%) 🚀

优化路径:
- Stage 1: 基础优化 (+50%)
- Stage 2.1: CPU 多进程并行 (+200%)
- Stage 2.2: I/O 流水线 (+13%)
- Stage 2.4: 内存优化 (-4.4%)
- Stage 2.3: 音频并行化 (+4%)

当前瓶颈:
- AI 模型推理仍在 CPU 上
- CPU 利用率 95%+ (已饱和)
- GPU 利用率仅 3% (算力闲置)
```

### 硬件环境分析

**GPU 配置**:
```
GPU: NVIDIA GeForce RTX 4070
VRAM: 16GB (可用 ~14GB)
CUDA Cores: 5888
Tensor Cores: 184 (第4代)
CUDA Version: 12.9 (编译器)
Driver Version: 581.15 (支持 CUDA 13.0)
```

**当前 PyTorch 状态**:
```
PyTorch: 2.8.0+cpu (无 CUDA 支持)
CUDA available: False
问题: 无法使用 GPU 加速
```

### 优化潜力评估

**AI 推理性能对比** (理论):
```
CPU (i7/i9):
- 单帧推理: 100-200ms
- 并行处理 (4核): 25-50ms/帧
- 50.8 fps (Phase 4 实测)

GPU (RTX 4070):
- 单帧推理: 5-10ms (GPU 加速)
- 批处理 (batch=4): 1-2ms/帧
- 预期: 200-500 fps (40-100倍提升)

实际预期 (考虑数据传输):
- 保守估计: 100-150 fps (2-3倍提升)
- 理想情况: 200-300 fps (4-6倍提升)
```

---

## 🎯 Phase 5 总体目标

### 核心目标

**主目标**: 启用 GPU 加速，将处理速度从 **50.8 fps 提升到 150+ fps** (3倍提升)

**次要目标**:
1. 充分利用 GPU 算力 (目标利用率 70%+)
2. 优化 GPU 内存管理 (VRAM < 10GB)
3. 保持 CPU 多进程架构的优势
4. 实现 CPU-GPU 混合流水线

### 具体指标

| 指标 | Phase 4 | Phase 5 目标 | 提升幅度 |
|------|---------|-------------|---------|
| **处理速度** | 50.8 fps | 150 fps | **+195%** |
| **1000帧耗时** | 19.2 秒 | 6.7 秒 | **-65%** |
| **GPU 利用率** | 3% | 70%+ | **+2233%** |
| **VRAM 占用** | 0 MB | < 10GB | 合理 |
| **CPU 利用率** | 95% | 40-60% | 释放资源 |

---

## 🚀 Phase 5 阶段规划

### Stage 1: CUDA 环境配置 (2-3小时)

**目标**: 安装支持 CUDA 的 PyTorch 和相关依赖

#### 任务清单

1. **卸载 CPU 版 PyTorch** (15分钟)
   ```bash
   pip uninstall torch torchvision torchaudio
   ```

2. **安装 CUDA 版 PyTorch** (30分钟)
   ```bash
   # PyTorch 2.8 + CUDA 12.9
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

   **注意**: CUDA 12.9 兼容 cu124 (CUDA 12.4) wheel

3. **验证 CUDA 支持** (15分钟)
   ```python
   import torch
   print(f"CUDA available: {torch.cuda.is_available()}")
   print(f"CUDA device: {torch.cuda.get_device_name(0)}")
   print(f"CUDA version: {torch.version.cuda}")
   ```

4. **更新依赖** (30分钟)
   - 检查其他依赖是否需要 GPU 版本
   - 安装 CUDA 相关工具库

#### 预期成果

```
✅ PyTorch 2.8 + CUDA 12.4
✅ torch.cuda.is_available() == True
✅ GPU 设备可识别
✅ 简单 tensor 运算测试通过
```

---

### Stage 2: AI 模型 GPU 迁移 (4-5小时)

**目标**: 将 AI 模型 (LaMa inpainting) 迁移到 GPU

#### 核心修改

**文件**: `app/core/ai/ai_handler.py`

1. **模型加载时指定设备** (1小时)
   ```python
   class AIHandler:
       def __init__(self, config, ai_params):
           # 检测 GPU
           self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
           self.logger.info(f"Using device: {self.device}")

       def load_models(self):
           # 加载模型到 GPU
           self.model = load_lama_model(...)
           self.model.to(self.device)  # 关键: 迁移到 GPU
           self.model.eval()
   ```

2. **推理时数据传输** (2小时)
   ```python
   def process_frame(self, frame, params):
       # 1. 将输入转移到 GPU
       frame_tensor = torch.from_numpy(frame).to(self.device)

       # 2. GPU 推理
       with torch.no_grad():
           result = self.model(frame_tensor)

       # 3. 将结果转回 CPU
       result_np = result.cpu().numpy()

       return result_np
   ```

3. **批处理优化** (1小时)
   ```python
   def process_batch(self, frames):
       """批量处理多帧 (GPU 优势)"""
       batch_tensor = torch.stack([
           torch.from_numpy(f) for f in frames
       ]).to(self.device)

       with torch.no_grad():
           results = self.model(batch_tensor)

       return [r.cpu().numpy() for r in results]
   ```

4. **内存管理** (1小时)
   ```python
   def cleanup(self):
       """清理 GPU 内存"""
       torch.cuda.empty_cache()
       gc.collect()
   ```

#### 多进程 GPU 共享策略

**问题**: 多个进程如何共享 GPU？

**方案 A: 每个进程独立加载模型** (简单但 VRAM 占用大)
```python
# 子进程中
def frame_processor_worker(...):
    # 每个进程独立加载模型
    ai_handler = AIHandler(...)
    ai_handler.load_models()  # 每个进程占用 ~2GB VRAM

    # 4 进程 → 8GB VRAM (可接受)
```

**方案 B: 使用 CUDA Streams** (复杂但高效)
```python
# 主进程加载模型，子进程共享
# 需要复杂的进程间通信和同步
```

**选择**: **方案 A** (优先实施，简单可靠)
- RTX 4070 有 16GB VRAM，4个进程各占 2GB = 8GB，可接受
- 每个进程独立运行，无需复杂同步

#### 预期成果

```
✅ AI 模型成功迁移到 GPU
✅ 单帧推理时间: 100-200ms (CPU) → 5-10ms (GPU)
✅ 批处理支持 (batch=4-8)
✅ VRAM 占用 < 10GB (4进程)
```

---

### Stage 3: GPU 流水线优化 (3-4小时)

**目标**: 优化 CPU-GPU 数据传输，实现混合流水线

#### 优化策略

1. **异步数据传输** (1.5小时)
   ```python
   # 使用 CUDA Streams 异步传输
   stream = torch.cuda.Stream()

   with torch.cuda.stream(stream):
       frame_tensor = frame_tensor.to(device, non_blocking=True)
       result = model(frame_tensor)
       result_cpu = result.cpu()
   ```

2. **批处理流水线** (1.5小时)
   ```
   读取线程 → [帧缓冲] → GPU批处理 → [结果缓冲] → 写入线程
                         (batch=4-8)
   ```

   **关键**: 将多帧打包成 batch，减少 GPU 调用次数

3. **Pinned Memory** (1小时)
   ```python
   # 使用 pinned memory 加速 CPU-GPU 传输
   frame_tensor = torch.from_numpy(frame).pin_memory()
   frame_gpu = frame_tensor.to(device, non_blocking=True)
   ```

#### 混合 CPU-GPU 架构

```
主线程
  ↓
启动读取线程 (CPU)
  ↓
[帧队列] (30帧, CPU内存)
  ↓
GPU 批处理进程池 (4进程)
  ├─ 进程1: batch=4, GPU 0
  ├─ 进程2: batch=4, GPU 0
  ├─ 进程3: batch=4, GPU 0
  └─ 进程4: batch=4, GPU 0
  ↓
[结果队列] (50帧, CPU内存)
  ↓
写入线程 (CPU)
  ↓
输出视频
```

#### 预期成果

```
✅ CPU-GPU 数据传输优化 (-50% 开销)
✅ 批处理支持 (batch=4-8)
✅ 异步传输 (non_blocking=True)
✅ Pinned memory 加速
```

---

### Stage 4: 性能调优和监控 (2-3小时)

**目标**: 调优参数，优化性能，添加监控

#### 调优参数

1. **批处理大小** (Batch Size)
   ```python
   # 测试不同 batch size 的性能
   batch_sizes = [1, 2, 4, 8, 16]

   # 选择最优值 (权衡吞吐量和延迟)
   optimal_batch_size = 4-8  # 预期
   ```

2. **进程数** (Num Processes)
   ```python
   # RTX 4070 可同时运行多个进程
   num_processes = [2, 4, 6, 8]

   # 选择最优值 (权衡 GPU 利用率和 VRAM)
   optimal_num_processes = 4  # 预期
   ```

3. **队列大小** (Queue Size)
   ```python
   # 减小队列大小 (GPU 处理快，不需要大缓冲)
   frame_queue_size = 10-20  # vs CPU 30
   result_queue_size = 20-30  # vs CPU 50
   ```

#### GPU 性能监控

1. **添加 GPU 指标** (1小时)
   ```python
   def get_gpu_metrics():
       """获取 GPU 性能指标"""
       return {
           "gpu_utilization": get_gpu_usage(),  # %
           "vram_used": get_vram_usage(),  # MB
           "gpu_temperature": get_gpu_temp(),  # °C
           "gpu_power": get_gpu_power(),  # W
       }
   ```

2. **集成到进度信号** (30分钟)
   ```python
   progress_data = {
       "phase": "processing_frames",
       "current_frame": 500,
       "processing_speed": 150.5,  # fps
       "gpu_utilization": 75,  # %
       "vram_used": 8192,  # MB
   }
   ```

#### 预期成果

```
✅ 最优 batch size: 4-8
✅ 最优进程数: 4
✅ GPU 利用率: 70%+
✅ 实时 GPU 监控
```

---

## 📊 性能预期

### 性能提升预测

| 场景 | Phase 4 (CPU) | Phase 5 (GPU) | 提升幅度 |
|------|--------------|--------------|---------|
| **单帧推理** | 100-200ms | 5-10ms | **10-40倍** |
| **批处理 (batch=4)** | 100ms | 8ms (2ms/帧) | **12.5倍** |
| **整体处理速度** | 50.8 fps | 150 fps | **+195%** |
| **1000帧耗时** | 19.2秒 | 6.7秒 | **-65%** |

### 性能对比可视化

```
AI 推理性能:
CPU (单核): ████████████████████ 100-200ms
CPU (4核并行): ██████ 25-50ms
GPU (单帧): █ 5-10ms
GPU (batch=4): ▏ 2ms/帧

总体处理速度:
Phase 3 (CPU单进程): ██████████ 10 fps
Phase 4 (CPU多进程): ████████████████████████████████████████████████████ 50.8 fps
Phase 5 (GPU加速): ████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████ 150 fps (预期)

提升倍数:
Phase 3 → Phase 4: +408%
Phase 4 → Phase 5: +195% (预期)
Phase 3 → Phase 5: +1400% (14倍!) 🚀🚀🚀
```

### VRAM 占用预测

| 配置 | 单进程 VRAM | 4进程 VRAM | 总 VRAM | 可用性 |
|------|-----------|----------|--------|--------|
| **模型大小** | 2GB | 8GB | 8GB | ✅ 充足 |
| **batch=4 额外** | 500MB | 2GB | 10GB | ✅ 充足 |
| **batch=8 额外** | 1GB | 4GB | 12GB | ✅ 充足 |
| **batch=16 额外** | 2GB | 8GB | 16GB | ⚠️ 接近上限 |

**选择**: batch=4-8，总 VRAM ~10-12GB，安全余量充足

---

## 🔧 技术挑战和解决方案

### 挑战 1: PyTorch CUDA 版本兼容性

**问题**: CUDA 12.9 可能与 PyTorch 预编译 wheel 不兼容

**解决方案**:
- 使用 cu124 wheel (CUDA 12.4)，向后兼容 CUDA 12.9
- 备选: 使用 cu121 wheel (CUDA 12.1)
- 最坏情况: 从源码编译 PyTorch (耗时 2-4小时)

### 挑战 2: 多进程 GPU 共享

**问题**: 多个进程同时使用 GPU 可能冲突

**解决方案**:
- 每个进程独立加载模型 (VRAM 充足)
- 使用 CUDA_VISIBLE_DEVICES 限制 GPU 访问 (可选)
- 进程数 ≤ 4，避免 GPU 过载

### 挑战 3: CPU-GPU 数据传输开销

**问题**: 数据在 CPU 和 GPU 之间传输会增加延迟

**解决方案**:
- 使用 pinned memory 加速传输 (2-3倍提速)
- 异步传输 (non_blocking=True)
- 批处理减少传输次数 (batch=4-8)

### 挑战 4: VRAM 不足风险

**问题**: 多进程加载模型可能超出 VRAM

**解决方案**:
- 动态调整进程数 (根据 VRAM 可用量)
- 使用 Model Quantization (FP16/INT8) 减小模型 (可选)
- 监控 VRAM 使用，超限时降级到 CPU

---

## 🧪 测试和验证

### 测试计划

1. **Stage 1 验证** (30分钟)
   - CUDA 环境测试
   - 简单 tensor 运算 (GPU vs CPU)
   - 性能基准测试

2. **Stage 2 验证** (1小时)
   - 单帧 GPU 推理测试
   - 批处理测试 (batch=1,2,4,8,16)
   - VRAM 占用监控

3. **Stage 3 验证** (1小时)
   - 端到端流水线测试 (100帧视频)
   - CPU-GPU 数据传输性能测试
   - 异步传输效果验证

4. **Stage 4 验证** (1小时)
   - 完整视频处理测试 (1000帧)
   - 参数调优测试
   - GPU 监控指标验证

### 性能基准

| 测试视频 | Phase 4 (CPU) | Phase 5 (GPU) | 提升 |
|---------|--------------|--------------|------|
| **100帧** | 1.97秒 | < 1秒 | > 2倍 |
| **1000帧** | 19.2秒 | < 7秒 | > 2.7倍 |
| **10000帧** | 186.5秒 | < 70秒 | > 2.6倍 |

---

## 📝 实施时间表

### 总体时间规划

| 阶段 | 预计耗时 | 累计耗时 |
|------|---------|---------|
| **Stage 1: CUDA 环境** | 2-3小时 | 2-3小时 |
| **Stage 2: 模型迁移** | 4-5小时 | 6-8小时 |
| **Stage 3: 流水线优化** | 3-4小时 | 9-12小时 |
| **Stage 4: 性能调优** | 2-3小时 | 11-15小时 |
| **文档和测试** | 1-2小时 | 12-17小时 |

**总计**: 12-17小时 (预留 buffer)

### 里程碑

- ✅ **Milestone 1**: CUDA PyTorch 安装成功
- ✅ **Milestone 2**: AI 模型 GPU 推理可用
- ✅ **Milestone 3**: 批处理流水线完成
- ✅ **Milestone 4**: 性能提升 > 100 fps
- ✅ **Milestone 5**: 完整文档和测试

---

## ⚠️ 风险和应对

### 风险列表

1. **CUDA 兼容性问题** (概率: 中, 影响: 高)
   - 应对: 尝试多个 CUDA 版本 wheel，最坏情况编译源码

2. **VRAM 不足** (概率: 低, 影响: 中)
   - 应对: 减少进程数，使用 FP16 量化

3. **性能提升不达预期** (概率: 中, 影响: 中)
   - 应对: 优化批处理，减少数据传输，调优参数

4. **多进程 GPU 冲突** (概率: 低, 影响: 低)
   - 应对: 每进程独立加载模型，避免共享状态

### 降级策略

如果 GPU 加速失败或效果不佳：
1. 保留 Phase 4 CPU 多进程方案作为备选
2. 混合模式: 部分进程 GPU，部分进程 CPU
3. 单进程 GPU + 批处理 (简化架构)

---

## 🎯 成功标准

### 功能验证

- ✅ PyTorch CUDA 环境配置成功
- ✅ AI 模型成功迁移到 GPU
- ✅ 批处理流水线正常工作
- ✅ VRAM 占用在合理范围 (< 14GB)
- ✅ GPU 利用率 > 70%

### 性能验证

- ✅ 单帧推理 < 10ms (GPU)
- ✅ 批处理 (batch=4) < 2ms/帧
- ✅ 整体处理速度 > 100 fps
- ✅ 1000帧视频 < 10秒
- ✅ 性能提升 > 2倍 (vs Phase 4)

---

## 🔮 Phase 5 之后

完成 GPU 加速后，后续可继续优化：

### Phase 6: 模型优化 (可选)
- 模型量化 (FP16/INT8)
- 模型剪枝
- 知识蒸馏

### Phase 7: 分布式处理 (可选)
- 多 GPU 并行 (如果有多张显卡)
- 多机分布式处理
- 云端 GPU 加速

### Phase 8: 实时处理 (可选)
- 实时视频流处理
- 摄像头实时去水印
- WebRTC 集成

---

## 📚 技术参考

### PyTorch CUDA

- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)
- [CUDA Compatibility](https://pytorch.org/get-started/previous-versions/)
- [PyTorch CUDA Semantics](https://pytorch.org/docs/stable/notes/cuda.html)

### GPU 优化

- [NVIDIA Deep Learning Performance Guide](https://docs.nvidia.com/deeplearning/performance/index.html)
- [PyTorch Performance Tuning Guide](https://pytorch.org/tutorials/recipes/recipes/tuning_guide.html)
- [Batch Processing Best Practices](https://docs.nvidia.com/deeplearning/frameworks/pytorch-performance-guide/)

### CUDA Programming

- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA Streams](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#streams)
- [Pinned Memory](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#page-locked-host-memory)

---

## 🎉 预期成果

完成 Phase 5 后:

```
🚀 Phase 5 预期成果 🚀

处理速度:
- Phase 4: 50.8 fps
- Phase 5: 150 fps (+195%) 🚀

1000帧视频:
- Phase 4: 19.2秒
- Phase 5: 6.7秒 (-65%) 🚀

GPU 利用率:
- Phase 4: 3%
- Phase 5: 70%+ (+2233%) 🚀

总体提升 (Phase 3 → Phase 5):
- 10 fps → 150 fps (+1400%, 15倍!) 🚀🚀🚀
- 100秒 → 6.7秒 (-93.3%) 🚀🚀🚀

技术价值:
- ✅ 充分利用 GPU 算力
- ✅ 现代化 AI 推理架构
- ✅ 为后续优化奠定基础
- ✅ 性能达到业界领先水平
```

---

**文档创建时间**: 2025-11-16
**预计开始时间**: 立即开始
**预计完成时间**: 2025-11-17

**下一步**: 开始 Stage 1 - CUDA 环境配置

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
