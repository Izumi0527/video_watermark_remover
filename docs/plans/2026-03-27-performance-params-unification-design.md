# 性能参数统一收敛设计

## 背景

本轮审查确认，当前“性能参数”相关代码存在 6 类问题：

1. `thread_count` 只被映射成 `num_processes`，但默认运行时并不会主动启用 `multiprocess/pipeline`，导致参数看似可调、实际难以生效。
2. `gpu_memory_limit`、`cache_size`、`enable_cache` 目前主要停留在 UI 和参数构建层，运行时基本没有真实消费点。
3. 批处理并发与重试策略在编排层仍有硬编码，和配置、偏好、UI 选择不一致。
4. 高级参数偏好持久化链路没有真正接通，用户修改后的性能参数无法稳定恢复。
5. “线程数自动”当前建立在 `QSpinBox` 最小值为 `1` 的语义上，存在明显误导。
6. 默认值同时散落在 UI、偏好默认、`ConfigManager`、运行时映射等多处，长期存在漂移风险。

用户已明确本轮目标：

- 采用“结构收敛”方案，而不是局部补丁。
- 在性能参数中显式提供“处理模式”。
- `GPU 内存限制`、`缓存设置`、`批处理配置` 都要真正接入运行时。
- `批处理并发数 / 自动重试 / 重试次数` 统一放入同一个性能参数界面。

## 目标

本轮设计目标是把“性能参数”收敛为一套可解释、可持久化、可测试、可追溯的统一模型，做到：

1. UI 展示的性能参数与运行时真实生效的参数保持一致。
2. 默认值、偏好值、预加载参数、单文件入口、批处理入口共享同一套参数定义。
3. 处理模式显式建模，不再由若干隐式布尔值和默认构造参数共同猜测。
4. `GPU 内存限制` 和 `缓存设置` 绑定到真实运行时消费点，而不是继续作为“死参数”保留在界面中。
5. 批处理配置不再在编排层硬编码，而是统一归属于性能参数模型。

## 非目标

本轮不做以下事情：

1. 不重做整套全局配置体系，不把所有偏好都迁移到 `ConfigManager`。
2. 不引入跨任务结果缓存，不尝试做高风险的图像处理结果复用。
3. 不改动现有 AI 修复算法本身的核心效果逻辑，仅接通参数对其的约束能力。
4. 不把本轮扩大成完整的 UI 大改版，界面只围绕性能参数分组与命名做必要调整。

## 方案对比

### 方案 A：最小修补

- 在现有 `dict` 参数流上继续补字段、补透传、补运行时读取。
- 保留默认值与偏好分散在各处的结构。

优点：

- 落地快，短期代码改动少。

缺点：

- 六个问题可以分别修，但无法真正消除“默认值漂移”和“语义散落”。
- 后续再加性能参数时，仍会继续出现 UI、偏好、运行时脱节。

### 方案 B：统一高级参数快照模型

- 新增统一参数模型模块，集中定义性能参数字段、默认值、校验、偏好读写、运行时导出。
- UI、预加载、单文件、批处理都围绕同一份参数快照工作。

优点：

- 能一次性解决当前 6 个问题。
- 后续继续新增参数和补测试的成本更低。
- 保持现有架构边界，不需要推倒重来。

缺点：

- 初次改动面比局部补丁更大，需要补一轮迁移与回归测试。

### 方案 C：全面切换为 `ConfigManager` 驱动

- 把高级参数和批处理配置全面迁移到 `config.ini / ConfigManager`。
- 弱化当前偏好系统。

优点：

- 配置入口理论上最统一。

缺点：

- 侵入性过高，会把当前任务扩大为“全项目配置体系重构”。
- 风险与收益不匹配。

## 推荐方案

采用方案 B：统一高级参数快照模型。

原因：

1. 这是唯一能同时解决“参数生效”“默认值统一”“偏好恢复”“批处理配置硬编码”“运行时语义清晰”这几类问题的方案。
2. 它不要求改动整个项目的配置体系，重构边界仍然收敛在性能参数相关模块。
3. 它和现有代码结构兼容，可以在 `UI -> builder -> runtime` 现有链路上渐进落地。

## 核心设计

### 1. 引入统一参数模型

新增模块：

- `src/app/config/advanced_params.py`

该模块负责：

1. 定义性能参数的标准字段、默认值和枚举。
2. 提供标准化与校验逻辑。
3. 提供偏好读写与旧结构迁移逻辑。
4. 提供运行时导出接口：
   - `to_ui_dict()`
   - `to_ai_params()`
   - `to_batch_config()`

建议核心字段如下：

- `processing_mode`
  - `auto`
  - `single_process`
  - `multiprocess`
  - `pipeline`
- `worker_count`
  - `0` 表示自动
  - `1-16` 表示显式并行度
- `enable_gpu`
- `gpu_memory_limit_mb`
- `enable_cache`
- `cache_size_mb`
- `batch_max_concurrent_files`
- `batch_auto_retry_failed`
- `batch_max_retry_count`

### 2. 明确“处理模式”语义

当前问题的根源之一是：

- UI 只有 `thread_count`
- builder 只生成 `num_processes`
- 运行时要不要进入 `multiprocess/pipeline` 却取决于另外两个布尔开关

本轮改造后：

- `processing_mode` 成为显式用户参数
- `worker_count` 只负责并行度
- 运行时导出规则统一为：
  - `single_process`
    - `enable_multiprocess=False`
    - `use_pipeline=False`
  - `multiprocess`
    - `enable_multiprocess=True`
    - `use_pipeline=False`
  - `pipeline`
    - `enable_multiprocess=True`
    - `use_pipeline=True`
  - `auto`
    - 由统一策略函数根据输入类型、设备、文件规模和并行度推导

这样可以彻底消除“只改了线程数却没改运行模式”的灰色语义。

### 3. `worker_count=0` 才表示自动

当前 `QSpinBox` 的“自动”建立在最小值 `1` 的特殊文案上，语义错误。

本轮统一为：

- `0` 表示自动
- `1-16` 表示显式并行度

UI 上可显示为：

- `0 -> 自动`
- 其余值显示数字

运行时实际生效值通过统一策略函数计算，例如：

- `single_process` 时忽略 `worker_count`
- `pipeline/multiprocess` 时：
  - `worker_count > 0` 用用户值
  - `worker_count == 0` 用自动策略

### 4. `GPU 内存限制` 的真实语义

本轮把 `gpu_memory_limit_mb` 设计成“深度修复运行时显存预算”，是软预算，不是硬隔离。

建议接入点：

- `src/app/core/ai/ai_handler.py`
- `src/app/core/ai/dl_inpainter.py`
- 必要时补 `src/app/core/ai/inpainting_backends/legacy_unet_backend.py`
- 如需统一检测路径预算，可在后续扩展到 `src/app/core/ai/gpu_monitor.py`

语义：

1. GPU 深度修复路径加载或推理前，读取 `gpu_memory_limit_mb`。
2. 若用户预算高于当前可用显存，则自动收缩到安全值，并记录日志。
3. 预算会影响 GPU 修复 profile 选择、OOM 重试策略以及必要时的 OpenCV 降级阈值。
4. 当前参数主要约束“修复”链路，而不是承诺统一控制所有 CUDA 分配。

### 5. `缓存设置` 的真实语义

本轮不做“跨任务结果缓存”。

原因：

- 对图像/视频修复任务来说，跨任务结果复用的命中率和一致性都较差。
- 这会引入额外的缓存失效、输入摘要计算、磁盘/内存回收风险。

本轮将 `enable_cache / cache_size_mb` 收敛成“视频流水线运行时缓冲预算”。

建议接入点：

- `src/app/core/video/modes/pipeline.py`
- `src/app/core/video/workers/frame_writer.py`
- `src/app/core/video/utils/backpressure.py`

语义：

1. `enable_cache=False`
   - 使用小缓冲和保守队列容量
   - 追求低内存占用
2. `enable_cache=True`
   - 使用基于 `cache_size_mb` 推导的队列/缓冲上限
   - 在内存足够时换取更高吞吐
3. `cache_size_mb`
   - 参与推导：
     - 读取队列容量
     - 结果队列容量
     - 写入缓冲上限
   - 对单文件 `pipeline` 路径和批处理内部的视频任务都生效

这样“缓存设置”会成为一个真实可调的吞吐/内存平衡参数。

### 6. 批处理配置统一进入性能参数

用户已明确：

- `batch_max_concurrent_files`
- `batch_auto_retry_failed`
- `batch_max_retry_count`

都应进入同一个性能参数界面统一管理。

这意味着：

1. 主界面的性能参数页将成为批处理策略的主编辑入口。
2. `SignalHandler._start_batch_processing()` 不再硬编码 `4 / True / 3`。
3. `BatchProcessingWidget` 若仍被保留，也必须改成消费统一参数模型，避免出现第二套配置入口。
4. 导出的 batch manifest 中也要记录这组真实运行值。

### 7. 默认值与持久化统一

本轮统一规则如下：

1. UI 默认值只从 `advanced_params.py` 读取。
2. 性能参数偏好存储到 `advanced_params` 分类。
3. 旧结构迁移规则：
   - `advanced.max_threads -> advanced_params.worker_count`
   - `advanced.enable_gpu -> advanced_params.enable_gpu`
   - `advanced.cache_size_mb -> advanced_params.cache_size_mb`
   - `batch.max_concurrent_files -> advanced_params.batch_max_concurrent_files`
   - `batch.auto_retry_failed -> advanced_params.batch_auto_retry_failed`
   - `batch.max_retry_count -> advanced_params.batch_max_retry_count`
4. `AdvancedParametersWidget` 不再自带硬编码默认值，而是：
   - 创建时加载统一默认值
   - 若偏好存在则覆盖
   - 应用/重置时通过统一模块写回
5. 启动预加载也使用同一份默认快照，避免再次出现“UI 默认值”和“预加载默认值”不同步。

## 组件与数据流

### UI 层

涉及文件：

- `src/app/ui/widgets/advanced/tabs/performance_tab.py`
- `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- `src/app/ui/components/control_panel.py`

职责：

- 展示统一参数模型定义的性能参数控件。
- 收集用户输入并映射到统一快照。
- 与偏好系统交互，而不是自己硬编码默认值。

### 参数构建层

涉及文件：

- `src/app/ui/utils/ai_params_builder.py`
- `src/app/config/advanced_params.py`

职责：

- 把统一快照导出为运行时 `ai_params`
- 把统一快照导出为 `batch_config`

### 编排层

涉及文件：

- `src/app/ui/main_window.py`
- `src/app/ui/signal_handler.py`
- `src/app/ui/widgets/batch/batch_processor_thread.py`
- `src/app/ui/widgets/batch/batch_processing_widget.py`

职责：

- 使用统一参数快照构建预加载参数
- 创建单文件 `VideoProcessorThread`
- 创建批处理 `BatchProcessorThread`
- 保证 manifest 导出的配置与真实运行配置一致

### 运行时层

涉及文件：

- `src/app/core/video/thread.py`
- `src/app/core/video/modes/pipeline.py`
- `src/app/core/video/workers/frame_writer.py`
- `src/app/core/ai/ai_handler.py`
- `src/app/core/ai/dl_inpainter.py`

职责：

- 消费显式处理模式与并行度
- 消费 GPU 修复显存预算
- 消费流水线缓冲预算

## 错误处理与兼容策略

1. 若用户历史偏好缺失或字段非法，统一回退到模型默认值。
2. 若 `worker_count=0` 且自动策略无法计算，则保守回退到既有默认并行度。
3. 若 `gpu_memory_limit_mb` 超出可用显存，记录 warning 并收缩预算，不直接报错。
4. 若 `cache_size_mb` 推导出的队列容量不合理，夹紧到安全上下限。
5. 若仍存在旧入口直接读取 `batch.*` 或 `advanced.*`，优先从新结构兼容读取，再逐步收敛。

## 测试策略

本轮至少补以下测试：

1. 参数模型测试
   - 默认值
   - 校验
   - 旧偏好迁移
2. UI / widget 测试
   - `processing_mode`
   - `worker_count=0 -> 自动`
   - 批处理配置字段显示和读写
3. 构建器测试
   - `processing_mode -> enable_multiprocess/use_pipeline/num_processes`
   - `gpu_memory_limit_mb` 与 `cache_size_mb` 的运行时导出
4. 单文件入口测试
   - `SignalHandler -> VideoProcessorThread` 的模式透传
5. 批处理入口测试
   - 批处理配置与视频模式透传
   - 不再依赖硬编码值
6. GPU 预算测试
   - 预算进入 `AIHandler / DLInpainter`
   - 超预算时收缩或降级
7. 缓冲预算测试
   - `cache_size_mb` 会影响 `pipeline` 队列与写入缓冲策略

## 实施分期

### Phase 1：统一参数模型

- 新增 `advanced_params.py`
- 建立默认值、校验、迁移、导出接口

### Phase 2：UI 与持久化

- 重构性能页
- 接通 widget 与偏好系统
- 清理硬编码默认值

### Phase 3：运行时映射

- builder 改为消费统一参数模型
- 单文件入口和预加载接线
- 批处理入口和 manifest 接线

### Phase 4：真实生效点

- 处理模式显式驱动运行时
- GPU 显存预算生效
- 视频流水线缓冲预算生效

### Phase 5：测试与文档

- 补齐回归测试
- 更新现有性能参数相关文档

## 风险与注意事项

1. `BatchProcessingWidget` 目前仍保留一套旧批处理配置读法，本轮必须收敛，否则会形成第二个漂移源。
2. `cache_size_mb` 本轮只定义为“运行时缓冲预算”，不能对外误称为“跨任务结果缓存”。
3. `gpu_memory_limit_mb` 是软预算，不应让用户误解为显卡硬隔离。
4. `processing_mode=auto` 必须有稳定、可测试的策略函数，避免行为不可预期。
5. 本轮不触碰 `BatchProcessorThread` 的预加载 AIHandler 并发安全边界，仍需保持“并发大于 1 时不复用同一个实例”。

## 一句话结论

本轮应把“性能参数”从一组分散的 UI 控件，收敛成“统一参数模型 + 统一偏好持久化 + 统一运行时导出 + 明确真实消费点”的完整链路；这样才能同时解决参数不生效、默认值漂移、批处理硬编码和持久化失效这几类问题。
