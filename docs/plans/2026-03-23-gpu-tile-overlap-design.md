# GPU Tile Overlap Design

## 目标

在不改 UI、不改 `AIHandler` 外部接口、不污染 `GPUInpaintingProfile.to_dict()` 分组语义的前提下，为 `DeepLearningInpainter` 增加最小可落地的 `tile / overlap` 推理能力，优先提升大图与高分辨率帧的 GPU 推理稳定性。

---

## 当前问题

当前 GPU 修复路径已经具备：

- 单帧最小真实 profile
- grouped batch 真实批处理
- OOM 一次性更保守 profile 重试

但仍有两个明显缺口：

1. 大尺寸推理输入仍可能导致显存压力过高
2. grouped batch 虽然已经能按组执行，但遇到大图组时还没有更稳的内部切块策略

---

## 本轮边界

本轮明确只做：

1. `tile / overlap` 仅作为 `DeepLearningInpainter` 内部执行策略
2. 接入点放在 `_run_single_inference()` 内部
3. 需要 tile 的样本不进入 `_run_true_batch()`，而是回到现有 `_run_group_sequential()`
4. `last_profile_used`、`gpu_inpainting_profile` 继续只表示最终成功那次真正生效的 profile
5. tile 命中异常时，继续复用现有“整帧级一次性更保守 profile 重试”语义

本轮明确不做：

- UI 新参数
- `AIHandler.processing_info` 新字段
- tile-aware true batch
- mixed precision
- second pass
- 把 tile 信息塞进 `GPUInpaintingProfile.to_dict()`

---

## 方案比较

### 方案 A：tile 只放进 `_run_single_inference()`，大图组顺序执行

做法：

- `_run_single_inference()` 在 `resize_for_inference` 之后决定是否切块
- 切块时逐 tile 前向、按 overlap 权重拼接，完成后只调用一次 `_postprocess()`
- grouped batch 中若某组样本需要 tile，则该组直接走 `_run_group_sequential()`

优点：

- 改动面最小
- 不破坏现有 grouped batch 分组契约
- 不污染 profile 观测语义
- 能自然继承现有单帧 OOM retry

缺点：

- 大图组当前还不能享受 tile-aware true batch

### 方案 B：把 tile 信息并入 `GPUInpaintingProfile`

优点：

- 上层观测更完整

缺点：

- 会直接影响 grouped batch 的分组 key
- 需要同步修改大量现有测试语义
- 风险明显扩大

### 方案 C：直接做 tile-aware true batch

优点：

- 吞吐潜力更高

缺点：

- 需要同时改分组、组调度和批量拼块逻辑
- 当前阶段风险过大

### 推荐

推荐方案 A。

---

## 详细设计

### 1. tile 判定

新增内部 helper，例如：

- `_should_use_tiled_inference(inference_shape, profile)`

它只根据“实际推理输入尺寸”和内部阈值决定是否切块，不把 tile 作为 profile 的公开字段。

### 2. tile 计划

新增内部 helper，例如：

- `_build_tile_starts(length, tile_size, overlap)`
- `_build_tile_regions(image_shape, tile_size, overlap)`

规则：

- tile 尺寸与 overlap 使用内部固定策略
- overlap 必须小于 tile 尺寸
- 最后一块要兜住右边界和下边界

### 3. tile 前向与拼接

新增内部 helper，例如：

- `_run_model_forward(frame_rgb, mask)`
- `_run_tiled_model_forward(inference_frame_rgb, inference_mask, profile)`
- `_build_tile_weight(height, width, overlap)`

执行顺序：

1. 先把单个 tile 送入模型前向
2. 把每个 tile 的输出先裁回原 tile 区域
3. 用 overlap 权重把多个 tile 融合成一张完整推理输出
4. 最后只调用一次 `_postprocess()`

注意：

- 不允许对每个 tile 单独 `_postprocess()`
- 否则会破坏整图尺度上的融合语义

### 4. 模型步幅对齐

轻量级 U-Net 有 4 次下采样，内部推理输入更稳的做法是：

- 在真正送入模型前，把输入 pad 到稳定步幅
- 模型输出后再裁回 pad 前尺寸

这样 tile 与非 tile 路径都能复用同一套模型输入约束。

### 5. grouped batch 行为

新增内部判定，例如：

- `_requires_tiled_execution(item)`

规则：

- 只要组内任一样本需要 tile，该组就不走 `_run_true_batch()`
- 当前组直接退回 `_run_group_sequential()`
- 其他兼容组仍可继续 true batch

这可以保留现有三种组级执行模式：

- `true_batch`
- `grouped_true_batch`
- `mixed_grouped_batch`

---

## 测试设计

至少覆盖：

1. 单帧命中 tile 路径后，输出尺寸保持原图大小，`last_profile_used` 语义不变
2. 需要 tile 的 grouped batch 不会进入 `_run_true_batch()`
3. mixed case 中，小图组仍可 true batch，大图组顺序 tile，执行模式为 `mixed_grouped_batch`
4. tile 路径命中 OOM 时，仍只做一次整帧级更保守 profile 重试

---

## 成功标准

满足以下条件即可认为本阶段完成：

1. 单帧路径可根据推理输入尺寸自动切到 tile / overlap
2. grouped batch 中需要 tile 的组会稳定回退到顺序执行
3. 现有 grouped batch 分组语义与 `last_profile_used` 观测不被破坏
4. OOM retry 语义在 tile 路径下继续成立
5. 相关单测与回归测试通过
