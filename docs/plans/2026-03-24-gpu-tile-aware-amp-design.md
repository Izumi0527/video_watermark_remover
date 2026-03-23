# GPU Tile-Aware Batch And Mixed Precision Design

## 目标

在不改 UI、不改 `AIHandler` 外部接口、不污染 `GPUInpaintingProfile.to_dict()` 与现有分组契约的前提下，为 `DeepLearningInpainter` 增加两项最小可落地能力：

1. `tile-aware true batch`
2. `mixed precision` 统一前向包装

---

## 当前上下文

截至当前代码基线，GPU 修复链路已经具备：

- grouped batch
- 单帧内部 `tile / overlap`
- 整帧级一次性更保守 profile OOM 重试

当前仍存在两个明显缺口：

1. 大图组命中 tile 后只能组内顺序执行，吞吐损失明显
2. 还没有统一的 mixed precision 包装层，无法在单帧、tile、batch 三条路径间复用

---

## 本轮边界

本轮明确只做：

1. 保持 `_get_batch_group_key()` 语义不变
2. 组内新增 `tile_aware_true_batch` 执行策略
3. mixed precision 只作为统一前向包装层
4. `last_profile_used`、`gpu_inpainting_profile` 继续只表达最终成功那次真正生效的修复 profile
5. OOM retry 继续保持“一次整帧级保守 profile 重试”的语义

本轮明确不做：

- UI 新参数
- `processing_info` 新字段
- second pass
- 复杂精度档位矩阵
- 把 AMP / tile 细节写进 `GPUInpaintingProfile`

---

## 方案比较

### 方案 A：只做 tile-aware true batch

优点：

- 直接解决大图组吞吐问题

缺点：

- 显存压力没有同步缓解
- 后续还要再补 mixed precision

### 方案 B：只做 mixed precision

优点：

- 接入面相对集中
- 对单帧、tile、batch 都可能有帮助

缺点：

- 大图组仍然只能顺序 tile，吞吐短板还在

### 方案 C：两者同阶段一起做，但都只做最小版本

做法：

- `tile-aware true batch` 仅在组内 tile plan 完全一致时启用
- mixed precision 仅作为统一前向包装层，不扩展为复杂配置系统

优点：

- 同时解决吞吐与显存两个方向的痛点
- 复杂度仍可控

缺点：

- 状态机比单做一项更复杂，需要把失败回退顺序设计清楚

### 推荐

推荐方案 C。

---

## 详细设计

### 1. 组内执行模式

保持现有 grouped batch 分组逻辑不变，组内只在以下三种模式中三选一：

- `true_batch`
- `tile_aware_true_batch`
- `sequential_fallback`

选择规则：

1. 组内样本都不需要 tile：走 `true_batch`
2. 组内样本都需要 tile，且 tile plan 完全一致：走 `tile_aware_true_batch`
3. 只要 tile plan 不一致或校验失败：走 `sequential_fallback`

### 2. mixed precision 的位置

mixed precision 不参与分组，也不参与模式选择，只作为统一前向包装层，覆盖：

- 单帧直推
- 顺序 tile
- 普通 true batch
- tile-aware true batch

这样可以避免把 AMP 细节和 batch / tile 语义耦合在一起。

### 3. 新增 helper

建议新增并收口在 `src/app/core/ai/dl_inpainter.py`：

- `_resolve_tile_plan_for_item(item)`
  - 解析单样本 tile plan
- `_can_use_tile_aware_true_batch(group, tile_plans)`
  - 判断当前组能否走 tile-aware batch
- `_resolve_precision_policy(...)`
  - 判断当前设备和模式是否允许优先尝试 mixed precision
- `_run_forward_with_precision(input_tensor, prefer_mixed_precision=True)`
  - 统一封装 FP32 / AMP 前向
- `_run_sequential_tiled_inference(...)`
  - 复用当前顺序 tile 逻辑
- `_run_tile_aware_true_batch(batch_items, tile_plan)`
  - 按 tile 位置跨样本合批

### 4. tile-aware true batch 的执行方式

对一个组执行 `tile_aware_true_batch` 时：

1. 先确认所有样本的 tile plan 完全一致
2. 按 tile 索引遍历
3. 取出每个样本在该 tile 位置上的图像与掩码
4. 拼成一个 `(B, 4, H, W)` batch tensor
5. 通过 `_run_forward_with_precision(...)` 做一次前向
6. 再把结果拆回各自样本的整图缓冲区
7. 所有 tile 完成后，每个样本只调用一次 `_postprocess(...)`

注意：

- 不允许对每个 tile 单独 `_postprocess()`
- 仍然要保持最终后处理与整图语义一致

### 5. mixed precision 的失败顺序

统一前向包装层内的顺序固定为：

1. 先尝试 mixed precision
2. 若命中 AMP 不可用或精度相关异常，先回退到 FP32
3. 若 FP32 仍失败且属于 OOM，再进入现有 profile 保守重试
4. 若不是 OOM，则不做 profile 重试

这样可以保证：

- “精度降级”和“profile 降级”是两层不同机制
- AMP 失败不会污染 OOM retry 计数

### 6. OOM retry 与执行模式的关系

现有 OOM retry 语义继续保留，但重试时优先保持当前执行模式：

- 当前模式能继续 `tile_aware_true_batch`，就继续该模式
- 若 retry profile 导致 tile plan 不再一致，则降到 `sequential_fallback`

这能保证“先尽量保留吞吐，再保守降级”。

### 7. 观测语义

本轮不新增公开观测字段，但建议内部把 `last_batch_execution_mode` 扩展为：

- `true_batch`
- `grouped_true_batch`
- `tile_aware_true_batch`
- `mixed_grouped_batch`
- `fallback_sequential`

其中：

- 若整批所有有效组都走 tile-aware true batch，则记 `tile_aware_true_batch`
- 若组间混用普通 true batch、tile-aware true batch、顺序回退，则记 `mixed_grouped_batch`

---

## 测试设计

至少覆盖：

1. `tile_aware_true_batch` 命中时，模型前向次数小于顺序 tile
2. tile plan 不一致时，组级稳定回退到顺序执行
3. mixed precision 统一前向包装会被单帧、普通 batch、tile-aware batch 复用
4. mixed precision 失败时，先降回 FP32 而不是直接改 profile
5. 开启 mixed precision 后，OOM retry 仍只记一次整帧级保守重试
6. `last_profile_used` 与 `last_batch_execution_mode` 语义不漂移

---

## 成功标准

满足以下条件即可认为本阶段完成：

1. 大图组在 tile plan 一致时能走 `tile_aware_true_batch`
2. tile plan 不一致时稳定回退到顺序路径
3. mixed precision 能被四条 GPU 前向路径共享
4. AMP 失败与 OOM 失败有清晰的分层回退
5. 相关单测、定向回归、静态检查通过
