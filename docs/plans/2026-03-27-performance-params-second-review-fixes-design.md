# 性能参数二次复审修复设计

## 背景

在 `b6e18c0` 这轮彻底重构之后，性能参数链路已经完成了统一快照、统一解析和统一运行时配置的主体收口，但第二次详细审查又暴露出 3 个剩余问题：

1. 批处理 `auto` 模式仍按“首文件”解析，混合队列会整批误用同一模式。
2. 预加载 `AIHandler` 的刷新判定仍靠手工列举字段，GPU 预算变化不会触发 refresh。
3. `advanced_params` 默认值与 legacy 迁移没有彻底解耦，恢复默认后仍可能被旧字段重新污染。

此外，`cache_size_mb` 当前更接近“流水线缓冲档位”，尚未和 UI 的 MB 预算语义完全一致。

## 目标

本轮修复的目标是：

1. 让批处理在运行时按文件级别解析 `ResolvedPerformanceConfig`。
2. 让预加载 refresh 改为基于统一运行时签名，而不是继续追加零散字段。
3. 让 `advanced_params` 成为唯一真默认来源，legacy 字段只做缺失场景的一次性迁移。
4. 让流水线缓冲预算和 `cache_size_mb` 的 MB 语义更接近，避免明显超配。

## 非目标

本轮不做以下工作：

1. 不重写整个批处理架构，也不改动批处理 UI 交互流程。
2. 不把 `cache_size_mb` 扩展成严格的进程级内存控制器。
3. 不重构 `AIHandler` 的全部初始化流程，只修正 refresh 判定与预算透传边界。

## 方案对比

### 方案 A：最小补丁

- 批处理里按文件分支判断模式。
- 把 `gpu_memory_mb` 加进 refresh key。
- 修一处默认值迁移条件。

优点：

- 改动小，交付快。

缺点：

- 结构继续依赖手工分支和字段枚举。
- 下一次再增加运行时字段，仍然容易漏掉。

### 方案 B：入口层增强

- 保留现有 `ResolvedPerformanceConfig`。
- 批处理、预加载和偏好迁移全部回到这层统一消费。

优点：

- 与当前重构方向一致。
- 改动范围可控。

缺点：

- 还需要保留一部分旧兼容接口，不能完全消灭中间适配层。

### 方案 C：二次收口重构

- 建立“文件级运行时配置 + 运行时签名 + 一次性迁移归档”机制。

优点：

- 能一次性解决当前 3 个问题的共同根因。
- 更利于 manifest、trace 和后续策略扩展。

缺点：

- 需要同时修改 builder、SignalHandler、批处理线程、偏好迁移和测试。

## 推荐方案

采用 **方案 C：二次收口重构**。

原因：

1. 当前 3 个问题本质上都是“统一模型已经建立，但消费边界还没有完全压实”。
2. 继续靠补 key 或补 if，会把刚建立的运行时模型重新拖回局部补丁状态。
3. 方案 C 可以最小化未来继续演化时的维护成本。

## 核心设计

### 1. 批处理改成文件级 `ResolvedPerformanceConfig`

当前批处理只在启动时基于首文件生成一份 `ai_params`，这会导致混合图片/视频队列一起走错模式。

本轮改为：

1. `SignalHandler` 在启动批处理时只保留批次级原始快照。
2. `BatchProcessorThread` 在处理单个文件前，根据 `input_path` 调用统一 builder 解析该文件的 `ResolvedPerformanceConfig`。
3. 每个文件拥有自己对应的：
   - `ai_params`
   - `enable_multiprocess`
   - `num_processes`
   - `use_pipeline`
4. manifest 除批次级 `run.runtime_performance` 外，还要把每个文件的实际运行时配置写进 `items[*].processing_details` 或等价字段。

### 2. 预加载改成运行时签名 refresh

当前 `AI_HANDLER_REFRESH_KEYS` 是一组手工枚举字段，已经证明会漏掉 `gpu_memory_mb` 这种关键配置。

本轮改为：

1. 新增统一的运行时签名函数，例如：
   - `build_ai_handler_runtime_signature(ai_params) -> dict`
2. 预加载 `AIHandler` 与实际任务参数都先转成签名，再做比较。
3. 签名应覆盖所有会影响模型加载、预算和设备行为的字段，包括：
   - device
   - requested_inpainting_backend
   - opencv_inpainting_method
   - inpainting_algorithm
   - inpaint_radius
   - quality_level
   - min_area_pixels
   - gpu_memory_mb
   - inpainting_model_path
   - lama_model_path
   - lama_model_dir

这样后续即使继续增加运行时字段，也只需统一维护签名生成逻辑。

### 3. `advanced_params` 成为唯一真默认来源

当前逻辑在 `advanced_params` 恰好等于默认值时，会继续回退 legacy `advanced` / `batch` 字段，导致“恢复默认”不稳定。

本轮改为：

1. 只有 `advanced_params` 缺失或结构非法时，才执行 legacy 迁移。
2. 如果 `advanced_params` 已存在，即使其值等于默认值，也不能再让 legacy 字段重新覆盖。
3. 迁移成功后，把归一化后的 `advanced_params` 立即写回偏好数据，作为后续唯一来源。
4. legacy `advanced.max_threads` 和 `batch.*` 仅保留兼容存量数据的职责，不再参与稳定运行时读取。

### 4. 缓冲预算公式改成更接近 MB 语义

当前 `cache_size_mb` 会被最小队列值钉死，在 4K 视频下明显超出用户设置的 MB 预算。

本轮不引入复杂内存控制器，但至少调整为：

1. 根据 `frame_shape` 计算单帧近似内存占用。
2. 用 `cache_size_mb` 推导总缓冲帧数上限。
3. 再把总缓冲帧数按读取队列、结果队列、写入缓冲做比例切分。
4. 低分辨率下仍保留最小吞吐保障，但不能在 4K + 64MB 这类场景超配到数百 MB。

## 测试策略

### 1. 偏好迁移

- `advanced_params` 已存在默认值时，不再被 legacy 字段覆盖。
- `advanced_params` 缺失时，legacy 迁移仍然可用。

### 2. 预加载 refresh

- 仅改 `gpu_memory_mb` 时必须触发 refresh。
- 无关 trace 字段变化不应触发 refresh。

### 3. 批处理文件级解析

- 混合队列中图片应解析为 `single_process`。
- 视频应解析为 `pipeline`。
- manifest 中每个文件都能看到对应的运行时配置。

### 4. 缓冲预算

- `cache_size_mb` 变大时预算增大。
- 小预算场景下总近似缓冲内存不应明显超过预算。

## 风险

1. 批处理如果在文件级解析时重新误用共享 `AIHandler`，可能引入线程安全问题，需要保留“并发 > 1 不复用 preloaded handler”的现有限制。
2. 运行时签名若包含无关字段，会导致不必要的模型重建，需要严格控制签名内容。
3. 缓冲预算公式过于激进会影响吞吐，因此要用单测锁住下限与上限。

## 一句话结论

这轮不是简单修 3 个 if，而是把“批处理解析粒度、预加载刷新判定、默认值迁移边界”继续收口到统一运行时模型里；只有这样，第二次复审发现的问题才不会在下一轮以别的形式重复出现。
