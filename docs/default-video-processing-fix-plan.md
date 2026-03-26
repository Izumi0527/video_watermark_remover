# 默认参数慢处理修复实施方案（执行版）

> 详细任务拆解与测试驱动实施顺序见：`docs/plans/2026-03-25-default-video-performance-remediation.md`

## 0. 状态快照（更新于 2026-03-26）

已完成（本仓库当前工作区）：

- A1：预加载参数对齐，首任务可复用（预加载不再使用空 `ai_params`，并注入模型路径快照）。
- A2（部分）：单文件与批处理创建 `VideoProcessorThread` 时已透传 `enable_multiprocess/use_pipeline/num_processes`（但默认 `ai_params` 仍未生成这两个开关，默认仍为 single-process）。
- B1：OpenCV backend `load()` 幂等，避免逐帧重复加载。
- C1（提前完成）：逐帧成功日志降级为 `DEBUG`，并修正加载阶段的 YOLO 模型与 device 文案，不再写死 `v11s`。
- P0（新增）：LaMa 后端增加 ROI 裁剪修复，显著降低“整帧深度修复每帧一次”的计算量。

待完成（仍建议后续推进）：

- A3：默认处理策略切换（single/pipeline/multiprocess）的自动决策与 UI/配置入口。
- B2：将 `YOLOWatermarkDetector.detect_batch()` 接入真实视频处理链路。
- B3：LaMa 可用性前置判定与 UI 默认推荐文案一致性。
- C2/C3：输出参数与批处理硬编码清理（非本轮主性能瓶颈，但影响一致性与可控性）。

## 1. 目标与范围

目标：

1. 解决“默认参数下单文件视频处理特别慢”的主链路问题。
2. 让启动预加载、UI 默认参数、实际处理路径三者一致。
3. 在不破坏现有业务功能的前提下，建立可回归的性能基线。

范围：

- `src/app/ui/main_window.py`
- `src/app/ui/signal_handler.py`
- `src/app/ui/utils/ai_params_builder.py`
- `src/app/core/video/**`
- `src/app/core/ai/**`
- `src/app/core/audio/**`
- `tests/**`

非目标：

- 本轮不做 UI 大改版。
- 本轮不引入新模型。
- 本轮不做跨平台编解码体系重构。

---

## 2. 当前性能基线（来自 2026-03-25 日志）

1. `1.mp4`：
   - 开始：`09:25:05`
   - 完成：`09:40:31`
   - 帧数：`539`
   - 总耗时约：`926s`
   - 吞吐约：`0.58 FPS`
   - 相对源视频时长放大约：`51.54x`
2. `2.mp4`：
   - 开始：`11:43:35`
   - 完成：`11:57:00`
   - 帧数：`460`
   - 总耗时约：`805s`
   - 吞吐约：`0.57 FPS`
   - 相对源视频时长放大约：`52.50x`
3. 日志重复负载：
   - `Loading lightweight image inpainting model...` 当天出现 `310` 次。
   - `Using single-process mode` 当天出现 `3` 次。
   - `预加载 AIHandler 参数已变化...` 当天出现 `4` 次。
   - `Using automatic watermark detection ...` 当天出现 `1030` 次。
   - `No watermark areas detected` 当天出现 `673` 次。

## 2.1 本轮验证基线（2026-03-25 晚间复核）

为确保修复计划不是建立在过期结论上，本轮额外完成了三组轻量验证：

1. 参数刷新与模式分支契约
   - `pytest tests/unit/core/ai/video/test_video_module_split.py -q`
   - 结果：`7 passed`
   - 说明：当前 `VideoProcessorThread` 的 `_ai_handler_needs_refresh`、single/chunk/pipeline 分支入口与本文分析一致。
2. 批处理预加载复用边界
   - `pytest tests/unit/test_batch_processor_preloaded_policy.py -q`
   - 结果：`4 passed`
   - 说明：并发批处理不会跨线程复用同一个 `preloaded_ai_handler`，后续修复预加载逻辑时必须保留这条线程安全边界。
3. 修复后端默认映射
   - `pytest tests/unit/test_inpainting_backend_selection.py -q`
   - 结果：`5 passed`
   - 说明：当前默认 UI 文案仍会把默认修复后端映射到 `lama`，这与“默认先尝试 LaMa，再回退 OpenCV”的问题链一致。

同时需要注意一条现有测试约束：

- `tests/e2e/ps1/test_end_to_end.ps1`
  - 当前仍显式断言 `video_processor.enable_multiprocess is False`
  - 因此一旦阶段 A2 / A3 调整默认处理策略，必须同步更新这条 E2E 预期，避免测试门禁误报。

---

## 3. 分阶段修复任务

## 阶段 A（P0，先解决主耗时）

任务 A1：预加载参数对齐，确保首任务可复用

- 改动点：
  - 先统一“默认参数”的单一来源，明确以 UI 默认快照还是配置快照为准，避免 `config.ini.example` 与 UI 默认值长期漂移。
  - 预加载不再使用 `ai_params={}`。
  - 使用默认 UI 参数快照创建 `AIHandler`。
  - 缩减 `_ai_handler_needs_refresh` 的误触发场景。
- 负责人建议：
  - `ui-implementer` + `core-engine-implementer`
- 验收：
  - 默认参数下首任务不再出现“预加载参数变化，重新加载”日志。
  - 真实运行日志中的 `conf_threshold`、`requested_inpainting_backend`、`num_processes` 等关键字段，与 UI 默认值和预加载快照保持一致。

任务 A2：打通单文件/批处理入口的模式与批处理配置传递

- 改动点：
  - `SignalHandler` 创建 `VideoProcessorThread` 时显式传入：
    - `num_processes`
    - `enable_multiprocess`
    - `use_pipeline`
  - `BatchProcessorThread` 为每个视频文件创建 `VideoProcessorThread` 时，同步透传上述参数，避免只修单文件入口。
  - `SignalHandler._start_batch_processing()` 不再硬编码：
    - `max_concurrent_files = 4`
    - `auto_retry_failed = True`
    - `max_retry_count = 3`
  - 批处理入口应优先读取配置层或 UI 参数，再统一传入 `BatchProcessorThread`。
- 负责人建议：
  - `batch-orchestrator`
- 验收：
  - 单文件处理不再固定 `Using single-process mode`。
  - 批处理内的单个视频文件也不再因为入口透传缺失而静默退回默认串行策略。
  - 批处理日志中的并发数、重试策略与配置值一致，不再出现入口硬编码行为。

任务 A3：默认策略切换为可配置高吞吐路径

- 改动点：
  - 为单文件视频引入策略选择（single/pipeline/multiprocess）。
  - 默认策略由视频规模和设备能力驱动。
- 负责人建议：
  - `core-engine-implementer`
- 验收：
  - 中长视频在默认参数下能进入 pipeline 或 multiprocess。

---

## 阶段 B（P1，消除重复开销）

任务 B1：修复 OpenCV backend 重复 `load()` 生命周期

- 改动点：
  - `OpenCVInpaintingBackend` 增加已加载状态。
  - `AIHandler._ensure_opencv_backend_loaded()` 仅在未加载时触发。
- 负责人建议：
  - `core-engine-implementer`
- 验收：
  - 同一任务中 `Loading lightweight image inpainting model...` 不再逐帧出现。

任务 B2：把 `detect_batch()` 接入默认视频路径

- 改动点：
  - 在 pipeline 或单文件策略中引入小批量检测。
  - 先批量检测，再分帧修复。
- 负责人建议：
  - `core-engine-implementer`
- 验收：
  - 默认视频链路可命中 `detect_batch()`，并产生可测吞吐提升。

任务 B3：前置 LaMa 可用性判定

- 改动点：
  - 启动期或处理前给出可用性结论。
  - 默认值与真实可用 backend 保持一致。
- 负责人建议：
  - `ui-implementer` + `core-engine-implementer`
- 验收：
  - 默认路径不再出现“先推荐 LaMa 再立刻回退”的认知反差。

---

## 阶段 C（P2，体验与配置一致性）

任务 C1：降低逐帧 INFO 日志等级

- 改动点：
  - 将逐帧成功日志下调到 `DEBUG`。
  - 保留阶段级关键日志。
- 负责人建议：
  - `core-engine-implementer`

任务 C2：让 `preserve_audio` 与导出参数真正生效

- 改动点：
  - 视频链路读取并尊重 `preserve_audio`。
  - 参数映射到 FFmpeg 输出策略。
  - `output_format`、`compression_quality` 不再停留在 UI/参数对象里，而是进入真实导出分支。
- 负责人建议：
  - `core-engine-implementer` + `batch-orchestrator`

任务 C3：统一批处理配置来源，移除编排层硬编码

- 改动点：
  - `SignalHandler._start_batch_processing()` 改为读取 `ConfigManager.get_batch_max_concurrent()`、`get_batch_auto_retry()`、`get_batch_max_retry_count()` 或批处理 UI 当前值。
  - 删除 `max_concurrent_files=4 / auto_retry_failed=True / max_retry_count=3` 这组硬编码默认。
  - 让配置模板、UI 默认值、真实运行时参数保持一致。
  - 同步校准批处理 manifest 导出的 `batch` 字段，避免导出结果仍保留旧快照或硬编码值。
- 负责人建议：
  - `batch-orchestrator`

---

## 4. 最小回归测试集合

优先执行：

1. `tests/unit/core/ai/video/test_video_module_split.py`
2. `tests/integration/core/ai/video/test_video_modes.py`
3. `tests/integration/runtime/task6_runtime_smoke.py`
4. `tests/unit/test_lama_backend_runtime_fallback.py`
5. `tests/integration/test_yolo_detector.py`
6. `tests/unit/test_batch_processor_preloaded_policy.py`
7. `tests/unit/test_processing_info_backend_trace.py`
8. `tests/unit/test_ai_handler_gpu_runtime_fallback.py`

### 4.1 本轮已完成快速验证

已执行：

```powershell
pytest -q `
  "tests/unit/test_batch_processor_preloaded_policy.py" `
  "tests/unit/test_ai_handler_gpu_runtime_fallback.py" `
  "tests/unit/test_lama_backend_runtime_fallback.py" `
  "tests/unit/test_processing_info_backend_trace.py"
```

结果：

- `13 passed in 0.17s`
- 当前可确认：
  - 并发批处理下不会错误复用同一个预加载 `AIHandler`
  - GPU / LaMa 回退与 backend trace 契约仍然稳定
  - 这组快速验证仍未覆盖“默认策略调整后的 E2E 预期”，因此实现阶段必须补同步更新
- 当前仍未覆盖：
  - 单文件/批处理入口的模式参数透传
  - 默认参数下的预加载命中率
  - 性能基线与日志刷屏次数约束

建议新增：

1. 单文件入口参数透传测试（建议新增 `tests/unit/test_signal_handler_thread_mode_passthrough.py`，覆盖 `num_processes/enable_multiprocess/use_pipeline`）。
2. 批处理入口参数透传测试（覆盖 `BatchProcessorThread -> VideoProcessorThread` 同类参数）。
3. 预加载命中测试（默认参数下首任务不重建 `AIHandler`）。
4. OpenCV backend `load()` 次数约束测试（同任务最多一次）。
5. 默认视频链路 `detect_batch()` 接线测试。
6. 批处理配置读取测试（覆盖 `max_concurrent_files/auto_retry_failed/max_retry_count` 不再被入口硬编码）。
7. 状态文案一致性测试（覆盖“AI 模型已就绪”与首任务是否仍触发二次加载）。
8. `tests/e2e/ps1/test_end_to_end.ps1` 预期同步更新测试（当前仍显式断言默认 `enable_multiprocess is False`）。
9. 视频导出参数生效测试（断言 `preserve_audio`、`compression_quality` 至少会进入核心导出分支）。

---

## 5. 变更冲突边界

以下文件不建议多人同轮并行修改：

1. `src/app/ui/signal_handler.py`
2. `src/app/core/video/thread.py`
3. `src/app/core/video/modes/pipeline.py`
4. `src/app/core/video/modes/multiprocess.py`
5. `src/app/core/ai/ai_handler.py`

建议策略：

1. 先冻结接口，再并行改实现。
2. 同一文件同一轮只允许一个实现代理写入。
3. `quality-reviewer` 只做审查，不直接改业务逻辑。

---

## 6. 验收指标与回滚条件

验收指标：

1. 默认参数下样例视频吞吐提升明显（至少优于当前 `~0.57 FPS` 基线）。
2. 首任务不再发生无必要二次模型加载。
3. OpenCV backend 不再逐帧重复 `load()`。
4. 单文件模式策略与 UI 参数表现一致。

回滚条件：

1. 出现处理结果错误或明显画质退化。
2. 单文件稳定性下降（崩溃、卡死、线程泄漏）。
3. 回归测试关键用例失败且无法在当轮修复。

---

## 7. 实施建议

建议节奏：

1. 先做阶段 A，并立即跑最小回归集合。
2. 阶段 A 稳定后进入阶段 B，优先修复重复 `load()`。
3. 最后做阶段 C，收敛日志和配置一致性问题。

执行记录建议写入：

- `docs/default-video-processing-slow-investigation.md`
- `docs/default-video-processing-fix-plan.md`
- 本文档作为实施基线，按阶段追加“已完成项/验证结果/遗留风险”。

---

## 8. 本轮已验证基线

已执行：

1. `pytest -q tests/unit/test_batch_processor_preloaded_policy.py tests/unit/test_ai_params_builder_inpainting_compatibility.py`
   - `9` 个用例全部通过，用时约 `0.10s`

这组基线说明：

1. 当前代码已经对“批处理并发时不复用同一个 `preloaded_ai_handler`”有明确测试保护。
2. 当前代码已经对“UI 修复方法 -> backend / GPU 开关映射”有明确测试保护。
3. 后续修复默认慢路径时，不能破坏这两条既有契约。
