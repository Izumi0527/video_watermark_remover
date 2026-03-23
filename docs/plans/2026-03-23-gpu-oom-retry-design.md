# GPU OOM Retry Design

## 目标

在不改 UI、不改外部调用签名的前提下，为 `DeepLearningInpainter` 增加“仅针对 GPU OOM 类失败的一次性更保守 profile 自动重试”能力，并把最小必要的重试观测透传给 `AIHandler.processing_info`。

---

## 当前问题

当前 GPU 修复路径已经具备：

- 单帧最小真实 profile
- grouped batch 真实批处理
- 最终成功 profile 的观测

但还缺少运行时稳定性自救能力：

- 单帧 GPU 推理若因 OOM 失败，会直接抛错
- grouped batch 的某个组若因 OOM 失败，只能退回顺序执行
- 上层 `processing_info` 无法区分“没有重试”和“发生过 OOM 降级重试”

---

## 本轮边界

本轮明确只做：

1. 只识别 GPU OOM 类错误
2. 只做一次更保守 profile 重试
3. 单帧与 grouped batch 都支持同一套 OOM 自救语义
4. 记录最小重试观测

本轮明确不做：

- tile / overlap
- mixed precision
- second pass
- 非 OOM 异常自动重试
- UI 新参数或配置项扩展

---

## 方案比较

### 方案 A：只在 `DeepLearningInpainter` 内部做 OOM 重试

做法：

- 单帧路径内部捕获 OOM 错误
- grouped batch 组级调度里捕获 OOM 错误
- 命中后改用更保守 profile 重试一次

优点：

- 改动面最小
- 保持单帧和 grouped batch 语义一致
- 不破坏 `AIHandler` 对 GPU 路径的现有封装

缺点：

- 需要补最小观测透传

### 方案 B：在 `AIHandler` 层统一做 GPU OOM 兜底

做法：

- 下层抛错
- 上层识别 OOM 后切换到更保守 GPU 或 OpenCV

优点：

- 策略集中

缺点：

- 无法自然复用 `DeepLearningInpainter` 的真实 profile 链路
- grouped batch 与单帧的语义更难统一

### 方案 C：OOM 重试与 mixed precision 一起补

优点：

- 一次性覆盖更多稳定性问题

缺点：

- 范围明显扩大
- 风险和测试面都会快速膨胀

### 推荐

推荐方案 A。

---

## 详细设计

### 1. OOM 判定

新增一个内部 helper，例如：

- `_is_gpu_oom_error(exc)`

只匹配非常明确的 OOM 类错误文案，例如：

- `cuda out of memory`
- `out of memory`
- `cudnn_status_alloc_failed`
- `显存不足`

不把普通 `RuntimeError`、shape 错误、权重错误、后处理错误误判成可重试错误。

### 2. 更保守 profile

新增一个内部 helper，例如：

- `_build_oom_retry_profile(profile)`

第一版只收紧这些字段：

- `resize_limit`
- `mask_expand_px`
- `mask_feather_px`
- `blend_ratio`

设计原则：

- 降低实际推理输入尺寸，优先解决显存占用
- 不把值降到非法范围
- 保持用户的 `requested_radius` 和 `quality_level` 作为原始请求观测

### 3. 单帧重试入口

把单帧完整执行链路抽成一个内部 helper，例如：

- `_run_single_inpainting_attempt(frame, mask, profile)`

这个 helper 负责：

1. 计算 `prepared_mask`
2. 计算 `inference_frame_rgb`
3. 预处理 tensor
4. 执行前向
5. 后处理输出

这样 OOM 重试时才能真正用新 profile 重建整条链路，而不是复用第一次失败时的 tensor。

### 4. grouped batch 重试入口

把 grouped batch 的 OOM 重试挂在：

- `_execute_batch_group(...)`

策略是：

1. 先按当前 group 跑一次真实 batch
2. 若命中 OOM，则对该组重建更保守 profile 的 `PreparedBatchItem`
3. 再尝试一次真实 batch
4. 若仍失败，则只回退该组顺序执行

不允许因为一个组 OOM 而把整批都重算。

### 5. 观测

继续保留：

- `last_profile_used`
- `AIHandler.last_gpu_inpainting_profile_used`
- `processing_info["gpu_inpainting_profile"]`

新增最小重试观测：

- `DeepLearningInpainter.last_oom_retry_used`
- `DeepLearningInpainter.last_oom_retry_count`
- `DeepLearningInpainter.last_retry_profile_used`

由 `AIHandler` 透传到：

- `processing_info["gpu_inpainting_oom_retry_used"]`
- `processing_info["gpu_inpainting_retry_count"]`
- `processing_info["gpu_inpainting_retry_profile"]`

注意：

- 不复用 `gpu_inpainting_fallback_reason`
- `gpu_inpainting_fallback_reason` 继续只表示“加载失败/设备不可用/路径级降级”

---

## 测试设计

至少覆盖：

1. 单帧 OOM 一次后，用更保守 profile 成功
2. 单帧非 OOM 异常不触发重试
3. grouped batch 某组 OOM 时，只重试该组，不影响其他组
4. `AIHandler.processing_info` 正确暴露：
   - 最终成功 profile
   - 是否发生重试
5. 重试耗尽后，不误报 GPU 成功后端与 profile

---

## 成功标准

满足以下条件即可认为本阶段完成：

1. 单帧路径命中 OOM 后可自动重试一次
2. grouped batch 路径命中 OOM 后只重试失败组
3. 非 OOM 异常不误触发重试
4. `processing_info` 能区分是否发生过 GPU OOM 重试
5. 现有 profile 与 grouped batch 回归测试不被破坏
