# 性能参数彻底重构设计

## 背景

第二轮审查确认，当前性能参数相关实现虽然已经完成了一轮“统一收敛”，
但仍存在 3 个关键缺口：

1. `processing_mode=auto` 只是表面字段，实际并没有真正的自动策略函数。
2. `gpu_memory_limit_mb` 在默认推荐的 LaMa 路径上基本不生效。
3. 批处理仍保留 `BatchProcessingWidget -> ConfigManager.batch.*` 的旧配置旁路，
   结构上没有完全收口。

如果继续在现有结构上做局部补丁，会反复出现同一类问题：

- UI 有参数，但运行时没有真实消费点。
- 默认值统一了，但真实行为仍由多个分散位置共同决定。
- 单文件、批处理、预加载使用的是“看起来一致、实际上不同”的参数链路。

本轮用户明确选择：**方案 3，彻底重构方案**。

## 目标

本轮要把“性能参数”从一个 UI 表单集合，升级为一套完整的
**统一运行时性能配置架构**，目标如下：

1. 让 `processing_mode`、`worker_count`、`gpu_memory_limit_mb`、
   `enable_cache`、`cache_size_mb`、批处理策略字段都成为统一模型中的一等公民。
2. 让 `auto` 模式具备稳定、可测试、可解释的自动策略，而不是隐式降级逻辑。
3. 让 GPU 显存预算在 LaMa、legacy U-Net 等深度修复路径上都具备真实消费点。
4. 让批处理入口、单文件入口、预加载入口都只依赖同一份运行时性能快照。
5. 删除或封存旧配置旁路，不再保留第二套性能参数来源。

## 非目标

本轮不做以下事情：

1. 不重构整个偏好系统与 `ConfigManager` 的所有职责。
2. 不引入磁盘级跨任务结果缓存。
3. 不重写视频处理模式本身的核心算法，只重构其参数驱动方式。
4. 不把本轮扩展为全项目配置中心重建。

## 方案对比

### 方案 A：继续修补统一快照

- 维持现有 `AdvancedParamsSnapshot -> ai_params` 结构。
- 分别修补 `auto`、LaMa 预算透传、批处理旧入口。

优点：

- 改动相对较小。

缺点：

- 仍然是“在旧结构上补洞”。
- 自动模式、GPU 预算、批处理策略仍会散在不同运行层实现。
- 后续继续演化时，仍然容易出现字段存在但行为漂移。

### 方案 B：新增统一运行时性能配置层

- 在 `advanced_params.py` 之上，再抽一层明确的运行时配置对象：
  - 参数快照负责“存什么”
  - 运行时配置负责“怎么生效”
- 所有入口只消费运行时配置对象。

优点：

- 模型职责更清晰。
- 自动模式、预算、批处理、缓存预算都能在统一位置解析。
- 运行时决策可测试、可追踪、可扩展。

缺点：

- 改动面明显更大。
- 需要同步改 UI、builder、入口编排、AI 后端与测试。

### 方案 C：全面切到 `ConfigManager`

- 把所有性能参数都迁移到 `config.ini` 读写与解析。

优点：

- 表面上更像传统配置中心。

缺点：

- 与当前偏好系统、UI 绑定方式冲突过大。
- 风险远高于收益。

## 推荐方案

采用 **方案 B：新增统一运行时性能配置层**。

原因：

1. 这是唯一能真正完成“彻底重构”而不是“继续修补”的方案。
2. 它能保留现有偏好快照与 UI 的稳定部分，同时重建真正的运行时解释层。
3. 它能把 3 个问题统一视为同一件事：
   **性能参数缺少单一运行时事实来源**。

## 核心设计

### 1. 分离“参数快照”和“运行时配置”

现有 `AdvancedParamsSnapshot` 继续保留，但职责收窄为：

- 默认值
- 偏好持久化
- UI 映射
- 旧字段迁移

新增统一运行时配置对象，建议放在：

- `src/app/config/advanced_params.py`
  - 或拆分为 `src/app/config/runtime_performance.py`

建议新增两个核心类型：

1. `ProcessingContext`
   - 描述当前任务上下文
   - 字段建议：
     - `input_file_path`
     - `is_batch`
     - `prefer_pipeline`
     - `cpu_count`
     - `gpu_enabled`

2. `ResolvedPerformanceConfig`
   - 表示已经完成自动策略解析后的真实运行时配置
   - 字段建议：
     - `requested_processing_mode`
     - `resolved_processing_mode`
     - `worker_count`
     - `enable_multiprocess`
     - `use_pipeline`
     - `gpu_memory_budget_mb`
     - `enable_cache`
     - `cache_size_mb`
     - `batch_max_concurrent_files`
     - `batch_auto_retry_failed`
     - `batch_max_retry_count`

统一约定：

- `AdvancedParamsSnapshot` 负责“保存和展示”。
- `ResolvedPerformanceConfig` 负责“运行时解释和导出”。

### 2. 重建 `auto` 模式策略

当前 `auto` 逻辑只根据 `worker_count > 1` 决定是否多进程，
这不是真正的策略。

本轮重构后，自动策略必须通过统一函数完成，例如：

- `resolve_performance_config(snapshot, context) -> ResolvedPerformanceConfig`

自动策略原则：

1. 图片任务默认单进程。
2. 视频任务在 CPU 核数足够时优先进入 `pipeline`。
3. 若用户显式指定 `single_process / multiprocess / pipeline`，
   则绝不再二次猜测。
4. `worker_count=0` 只表示“并行度自动”，不再决定模式本身。
5. 自动策略结果必须写入 trace / log / manifest。

建议首版策略：

- 非视频：`single_process`
- 视频且 `cpu_count <= 2`：`single_process`
- 视频且 `cpu_count >= 3`：`pipeline`
- 若未来需要，可以继续把文件分辨率、批处理类型等因素纳入策略函数，
  但本轮先保证简单、稳定、可测。

### 3. GPU 预算统一建模为“推理预算”

当前 `gpu_memory_limit_mb` 只影响 `dl_inpainter`，
而默认路径是 LaMa，因此用户语义与运行时行为脱节。

本轮重构要求：

1. 所有 GPU 深度修复路径都接受同一种预算对象。
2. `AIHandler` 不再只给 `dl_inpainter` 下发预算，而是给当前 active backend
   下发统一 runtime profile。
3. LaMa backend 需要提供 `set_runtime_profile()` 或等价能力。

建议统一新增：

- `GPURuntimeProfile`
  - `memory_budget_mb`
  - `effective_memory_budget_mb`
  - `resize_limit`
  - `prefer_roi`
  - `oom_retry_enabled`

工作方式：

1. `AIHandler` 根据用户预算和当前设备可用显存构建 profile。
2. profile 同步到当前深度修复 backend。
3. backend 在推理前根据 profile 执行收缩策略：
   - 优先使用 ROI
   - 限制推理输入尺寸
   - 必要时降低 OOM retry 的初始 aggressive 程度
4. trace 中记录：
   - 用户预算
   - 实际预算
   - 实际尺寸限制
   - 是否启用 ROI

### 4. LaMa backend 与 runtime 重构

本轮不是只“加一个参数透传”，而是把 LaMa 纳入统一深度后端约束协议。

建议做法：

1. 给 `LaMaInpaintingBackend` 增加运行时 profile 状态。
2. 给 `LaMaTorchScriptRunner` 增加可选 profile 输入。
3. 在 LaMa 路径中引入预算驱动的尺寸收缩函数。

建议抽出独立函数：

- `_apply_runtime_profile_to_inputs(frame, mask, profile)`

职责：

- 先做 ROI 计算
- 若 ROI 仍过大，则按 `resize_limit` 收缩
- 推理完成后恢复到原分辨率并拼回

这样做的意义：

- LaMa 和 legacy U-Net 都遵循同一类“预算驱动 profile”
- 用户不会再遇到“默认推荐路径上预算不生效”的问题

### 5. 批处理入口彻底收口

本轮不再容忍 `BatchProcessingWidget` 保留第二套配置来源。

调整原则：

1. `BatchProcessingWidget.set_config()` 不再读取批处理性能参数。
2. `BatchProcessingWidget` 只接受：
   - `set_advanced_params()`
   - 或 `set_resolved_performance_config()`
3. 旧的 `ConfigManager.get_batch_*()` 在运行时链路中不再被调用。
4. 批处理并发边界统一到与快照/UI 一致的 `1-16`。

如果当前主入口已经不依赖 `BatchProcessingWidget`，则：

- 保留它作为兼容 UI 组件可以接受
- 但必须把旧读法彻底删掉，避免未来再次接线时复活旧漂移

### 6. 缓存参数继续作为“流水线缓冲预算”

这一点不需要推翻前一版设计，但要纳入新运行时配置对象统一解释。

即：

- `enable_cache` 与 `cache_size_mb` 不再直接散落在 `ai_params`
- 而是先进入 `ResolvedPerformanceConfig`
- 再由流水线模式消费

这样日志、manifest、单文件、批处理都会看到同一份缓存预算语义。

## 数据流重构

### 新的数据流

1. UI 输出 `AdvancedParamsSnapshot`
2. 偏好系统持久化 `AdvancedParamsSnapshot`
3. 入口层构建 `ProcessingContext`
4. 统一调用 `resolve_performance_config(snapshot, context)`
5. 运行时只消费 `ResolvedPerformanceConfig`

### 单文件入口

- `SignalHandler` 获取 UI 快照
- 基于输入文件构建 `ProcessingContext`
- 生成 `ResolvedPerformanceConfig`
- 传给 `VideoProcessorThread` 和 `AIHandler`

### 批处理入口

- 每次启动批处理时生成一份批处理级 `ResolvedPerformanceConfig`
- 批处理线程只消费这份配置
- manifest 导出记录请求值与解析值

### 预加载入口

- 主窗口初始化或预热时，也必须通过统一解析函数生成运行时配置
- 不能再单独拼默认 `ai_params`

## 接口变更建议

### `AdvancedParamsSnapshot`

保留：

- `from_dict()`
- `to_dict()`
- `to_ui_dict()`

删除或弱化：

- 直接在快照内做复杂运行时解析的职责

新增：

- `build_processing_context(...)`
- `resolve(...) -> ResolvedPerformanceConfig`

### `ResolvedPerformanceConfig`

建议提供：

- `to_ai_params()`
- `to_batch_config()`
- `to_manifest_dict()`

这样所有入口不再直接依赖多个手写导出函数。

### AI backend 协议

建议为深度修复 backend 增加统一能力：

- `set_runtime_profile(profile)`
- `get_runtime_profile()`

这样 `AIHandler` 不需要知道不同 backend 的内部细节。

## 兼容策略

1. 旧偏好字段继续迁移到新快照字段。
2. 旧 `batch.*`、`advanced.max_threads` 仅保留迁移职责，不再参与运行时读取。
3. manifest 中同时记录：
   - 请求值
   - 解析值
4. 如果自动策略无法确定，必须保守回退并记录原因。

## 测试策略

本轮需要把测试从“字段存在”升级为“真实行为成立”。

### 1. 参数解析层

- `AdvancedParamsSnapshot` 默认值与迁移测试
- `ResolvedPerformanceConfig` 自动模式解析测试
- 显式模式覆盖自动模式测试

### 2. 入口层

- 单文件入口使用解析后配置测试
- 批处理入口使用解析后配置测试
- 预加载入口使用解析后配置测试

### 3. AI 运行时

- `AIHandler` 能把 budget profile 下发到当前 active backend
- LaMa backend 实际消费 profile 测试
- legacy U-Net 与 LaMa 共享预算语义测试

### 4. 批处理与兼容层

- `BatchProcessingWidget` 不再读旧配置测试
- 并发上限统一测试

### 5. 回归链路

- 单文件视频自动模式回归
- 批处理视频模式透传回归
- manifest 导出真实解析值回归

## 风险

1. 本轮改动会触及 UI、偏好、编排、AI backend、视频运行时多个层级，
   必须严格按 TDD 和分阶段验证推进。
2. LaMa runtime 的预算驱动收缩如果实现不慎，可能影响画质与速度平衡，
   因此必须把“预算限制”和“效果策略”分开记录在 trace 中。
3. 删除旧批处理旁路后，如果还有隐蔽调用点，会在测试中暴露；
   这正是本轮应主动清理的风险，而不是继续保留双轨。

## 一句话结论

本轮不应继续围绕现有 `dict` 参数流修补，而要把性能参数正式升级为
“统一快照 + 统一上下文 + 统一解析 + 统一运行时配置”的完整架构；
只有这样，`auto` 模式、LaMa 显存预算和批处理配置旁路这 3 个问题
才能一次性彻底解决。
