# GPU Batch 吞吐优化设计

## 背景

当前 [dl_inpainter.py](/C:/cascadeProjects/video_watermark_remover/src/app/core/ai/dl_inpainter.py) 中的 `inpaint_batch()` 已经保证了和单帧 `inpaint_frame()` 一致的 profile 语义，但实现仍然是逐帧循环调用单帧入口，尚未真正利用 GPU 的 batch 前向能力。

这带来的直接问题是：

- 批量入口不会显著减少 GPU 前向次数
- `quality_level / inpaint_radius` 虽然已真实生效，但批量路径没有吞吐优势
- 后续继续叠加 tile、OOM 回退、mixed precision 之前，缺少一个稳定的“真实 batch 前向”基线

---

## 本轮目标

在不改变外部调用接口的前提下，让 `DeepLearningInpainter.inpaint_batch()` 在满足以下条件时走真实 GPU batch 前向：

- 同一批次所有帧的**实际推理输入尺寸一致**
- 同一批次所有帧的**实际生效 GPU profile 完全一致**

只要不满足上述条件，整批回退到当前稳定的逐帧模式。

---

## 已选方案

用户已确认本轮采用：

- 方案：`稳妥优先`
- 边界：`同尺寸 + 同 profile 才走真实 batch`
- 回退：`不满足条件时整批回退逐帧`

这意味着本轮不会做：

- 按组 batch
- tile / overlap
- mixed precision
- OOM 自动切 batch size
- UI 层或线程层改动

---

## 设计原则

### 1. 正确性优先于吞吐

本轮批量优化只允许在“结果语义不漂移”的前提下启用。  
如果无法证明批量路径与单帧路径使用了同一套 profile 和同一推理输入尺寸，就不进入真实 batch。

### 2. 回退必须保守

只要发现条件不满足或 batch 前向异常，就整批回退逐帧。  
不做“部分成功、部分回退”的混合状态机。

### 3. 外部接口保持不变

`inpaint_batch(frames, masks, radius=3, quality_level=3, profiles=None)` 不改签名。  
这轮变化全部收敛在 `src/app/core/ai/dl_inpainter.py` 内部。

### 4. 可观测性优先

需要补一个内部执行模式标记，用于测试和后续排障：

- `self.last_batch_execution_mode = "true_batch" | "fallback_sequential"`

该字段本轮只做内部调试用途，不向 UI 层透出。

---

## 核心数据流

### 步骤 1：批次预检查

对每一帧先复用现有单帧流程中已经稳定的几步：

1. `_resolve_profile(...)`
2. `_prepare_mask(...)`
3. `_resize_for_inference(...)`

为每帧收集一个内部 `batch item`，至少包含：

- 原始 `frame_rgb`
- 原始尺寸
- `prepared_mask`
- `resolved_profile`
- resize 后的 `inference_frame_rgb`
- resize 后的 `inference_mask`
- 推理输入尺寸

### 步骤 2：判断是否允许真实 batch

仅当以下两个条件都满足时，进入真实 batch 前向：

1. 所有 `resolved_profile.to_dict()` 完全一致
2. 所有 `inference_frame_rgb.shape[:2]` 完全一致

否则直接整批回退到逐帧模式。

### 步骤 3：真实 batch 前向

满足条件时：

1. 对每个 `batch item` 调 `_preprocess(...)`
2. 用 `torch.cat(..., dim=0)` 合并成 `(B, 4, H, W)`
3. 只执行一次 `self.model(batch_tensor)`
4. 按样本逐个拆出结果
5. 对每个样本调用 `_postprocess(...)`
6. 保证最终输出尺寸与各自原始帧一致

### 步骤 4：异常回退

如果真实 batch 前向中任一步抛异常：

- 记录日志
- 整批回退到逐帧路径
- `last_batch_execution_mode = "fallback_sequential"`

---

## 关键实现点

### 1. 新增内部 batch item 结构

建议在 [dl_inpainter.py](/C:/cascadeProjects/video_watermark_remover/src/app/core/ai/dl_inpainter.py) 中新增轻量级内部数据结构，例如：

- `PreparedBatchItem`

字段建议包含：

- `original_rgb`
- `prepared_mask`
- `profile`
- `inference_frame_rgb`
- `inference_mask`
- `original_shape`
- `inference_shape`

### 2. 新增批量资格判断辅助方法

建议新增：

- `_prepare_batch_items(...)`
- `_can_use_true_batch(...)`
- `_run_true_batch(...)`

职责划分建议：

- `_prepare_batch_items`：构造每帧 batch item
- `_can_use_true_batch`：判断 profile / 尺寸是否统一
- `_run_true_batch`：执行一次真正的 batch 前向和逐帧后处理

### 3. 保留当前逐帧实现作为兜底

不要重写单帧修复逻辑，也不要把单帧入口塞进批量路径的复杂分支里。  
批量失败时直接复用当前 `self.inpaint_frame(...)`，这是本轮最可靠的回退基线。

---

## 回退规则

以下任一情况出现，都整批回退逐帧：

- `frames` / `masks` 长度不一致
- 任一 `mask` 为空或无有效区域
- 任一帧解析后的 profile 不同
- 任一帧 resize 后推理输入尺寸不同
- `torch.cat(...)` 失败
- `self.model(batch_tensor)` 失败
- batch 输出数量与输入数量不一致
- batch 输出后处理失败

---

## 测试设计

### 必做单元测试

建议新增或扩展 `tests/unit/test_dl_inpainter_batch.py`，覆盖以下场景：

1. **命中真实 batch**
   - 同尺寸、同 profile
   - 断言模型前向次数为 `1`
   - 断言执行模式是 `true_batch`

2. **不同尺寸回退逐帧**
   - 断言模型前向次数退回逐帧次数
   - 断言执行模式是 `fallback_sequential`

3. **同尺寸但不同 profile 回退逐帧**
   - 防止错误合批

4. **真实 batch 后输出尺寸仍正确**
   - 每帧输出尺寸必须等于各自原始尺寸

5. **真实 batch 抛异常时整批回退**
   - 断言仍能返回结果
   - 断言不会污染 profile 状态

### 回归测试

除新增 batch 单测外，本轮至少需要补跑：

- `tests/unit/test_dl_inpainter_profile.py`
- `tests/unit/test_dynamic_watermark_tracking.py`
- `tests/integration/test_dl_inpainter_gpu.py`

---

## 风险与控制

### 风险 1：表面批量化，实际仍多次前向

控制方式：

- 在测试里显式统计模型前向调用次数
- 不以“结果正确”作为唯一标准

### 风险 2：批量路径与单帧路径语义漂移

控制方式：

- 只在 profile 和推理输入尺寸完全一致时允许真实 batch
- 其它情况整批回退

### 风险 3：批量异常导致半批状态混乱

控制方式：

- 不做半批恢复
- 一旦出错，整批回退

### 风险 4：性能提升不明显

控制方式：

- 先把“真实 batch 前向次数减少”做成可验证事实
- 本轮不承诺最终吞吐数值，只承诺结构上完成真正 batch 前向

---

## 验收标准

满足以下条件，才算本轮设计真正落地：

1. `inpaint_batch()` 在同尺寸 + 同 profile 条件下，真实只做一次模型前向
2. 不满足条件时整批回退逐帧
3. 输出结果尺寸保持正确
4. 批量路径异常时能自动回退
5. 新增 batch 单测通过
6. 现有 profile 和 AI 主链路回归测试不被破坏

---

## 本轮不做的事

为了保证可落地和可验证，本轮明确不做：

- 按组 batch
- batch 内动态拆分
- tile / overlap
- second pass
- mixed precision
- OOM 自适应重试
- 上层 UI / 配置项扩展

---

## 下一步

下一步进入实现计划阶段，按 TDD 顺序拆成：

1. 先写失败测试
2. 再补真实 batch 内部实现
3. 再做异常回退和状态观测
4. 最后跑定向测试与回归测试
