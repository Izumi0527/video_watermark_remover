# 修复参数修复记录与 GPU U-Net 路径改造方案

## 文档说明

- 适用版本：`v0.6.0`
- 更新日期：`2026-03-23`
- 适用范围：当前仓库主流程中的检测后处理、OpenCV 修复链路、后处理链路，以及 GPU 深度学习 U-Net 路径现状说明

本文档专门记录本轮与“修复参数”相关的真实修复结果，并补充当前 `GPU 深度学习 U-Net` 路径的实际情况、阶段二落地结果与后续改造方案。

---

## 一句话结论

本轮已经把 `最小检测区域`、`修复算法`、`修复半径`、`修复质量` 中此前“没有真正生效”的部分接进主流程，当前生效边界是：

- `最小检测区域`：已经真正接入 `YOLO boxes -> mask`
- `修复算法`：已经真正影响 `OpenCV` 修复路径
- `修复半径`：已经真正影响 `OpenCV + GPU U-Net profile`
- `修复质量`：已经真正影响 `OpenCV + 后处理 + GPU U-Net profile`
- `GPU 深度学习 U-Net`：已经打通正式权重加载主路径、明确降级，并具备最小真实 profile

---

## 阶段一当前状态

截至 `2026-03-23`，阶段一已经落地了下面这些能力：

- `AIHandler` 现在会真实解析 `inpainting_model_path`
- `AIHandler.load_models()` / `AIHandler.update_device()` 会把权重路径传给 `DeepLearningInpainter.load_model(model_path=...)`
- 当 `inpainting_model_path` 为空、文件不存在或模型加载失败时，主流程会明确降级到 `OpenCV`
- `processing_info` 现在会补充：
  - `inpainting_backend`
  - `gpu_inpainting_requested`
  - `gpu_inpainting_fallback_reason`
  - `configured_inpainting_model_path`
  - `loaded_inpainting_model_path`
- `VideoProcessorThread` 会把配置中的 `inpainting_model_path` 注入 `ai_params`
  - 这样多进程 / 流水线 worker 链路也能拿到同一份 GPU 权重路径
- 如果复用的是“旧参数下预加载的 AIHandler”，而当前任务参数已经变化，`VideoProcessorThread` 会重建 `AIHandler`，避免继续沿用过期的 GPU 修复状态

这也意味着：

- 现在只有在“权重路径存在且加载成功”时，主流程才会把实际后端记为 `gpu_deep_learning_unet`
- “用户请求 GPU 修复”和“本次实际用了 GPU U-Net”这两件事，已经开始被清晰区分

---

## 阶段二当前状态

截至 `2026-03-23`，阶段二已经落地了下面这些能力：

- `AIHandler.inpaint_frame()` 在 GPU 路径下，会真实把：
  - `inpaint_radius`
  - `quality_level`
  传给 `DeepLearningInpainter.inpaint_frame(...)`
- `DeepLearningInpainter` 已新增最小真实 `GPUInpaintingProfile`
  - `requested_radius`
  - `quality_level`
  - `mask_expand_px`
  - `mask_feather_px`
  - `blend_ratio`
  - `resize_limit`
- GPU 路径现在会基于 profile 真实执行：
  - 掩码扩张
  - 掩码羽化
  - 推理前按质量档位缩放输入分辨率
  - 输出与原图按 profile 做软混合
- `processing_info` 现在会补充：
  - `gpu_inpainting_profile`
  - 其中记录本次实际生效的最小 GPU profile 数值，而不是只记录 UI 原始参数

这也意味着：

- `修复半径` 在 GPU 路径上的语义，已经不再是 OpenCV 的“扩散半径”
- 它现在表示“送入 U-Net 之前的上下文扩张强度”
- `修复质量` 则开始真实控制：
  - GPU 推理分辨率上限
  - 边界羽化强度
  - 最终混合强度

---

---

## 本次实际修了什么

### 1. 最小检测区域真正接进 YOLO 后处理

之前的问题：

- UI / 参数构建层已经能产出 `min_area_pixels`
- 但这项参数没有真正进入 `YOLO boxes -> mask` 的主后处理链路

本次修复后：

- `AIHandler` 初始化 `YOLOWatermarkDetector` 时，已经真实透传 `min_area_pixels`
- `YOLOWatermarkDetector._boxes_to_mask()` 已基于**原始检测框面积**做过滤
- 过滤发生在 `padding` 之前，避免被扩框后的面积“误放大”

当前真实行为：

- 调大 `最小检测区域`
  - 更能过滤小噪点、小误检
  - 更容易漏掉小角标、小字水印
- 调小 `最小检测区域`
  - 更容易抓到小角标、小字、细碎字幕样水印
  - 误检概率会增加

当前边界：

- 这项修复目前作用在当前主路径 `boxes -> mask`
- 如果未来切到真正的 `segmentation masks` 输出，还需要单独补一版最小面积过滤逻辑

---

### 2. 修复算法真正接进 OpenCV 主流程

之前的问题：

- 前端可以选择修复算法
- 但主流程里并没有稳定地把这个选择真正传给 `ImageInpainter`

本次修复后：

- `AIHandler.inpaint_frame()` 会先解析当前应走的 OpenCV 修复方法
- 然后把解析结果真实传给 `ImageInpainter.inpaint_frame(method=...)`
- 同时补齐了方法名兼容：
  - `navier_stokes -> ns`
  - `custom_interpolation -> custom`
- `processing_info["inpainting_method"]` 也会尽量记录实际执行的方法，而不是只保留 UI 原始选择值

当前真实行为：

- `telea`
  - 速度较快
  - 对中小区域通常比较稳
- `navier_stokes`
  - 更偏高质量
  - 对较大区域或结构延续更敏感
- `custom_interpolation`
  - 更适合小面积、局部、边缘过渡类场景
- `gpu_dl`
  - 只有在 GPU 深度学习路径已成功加载时才真正走 U-Net
  - 若实际降级到 OpenCV，会回退为 `auto`

---

### 3. 修复半径真正接进 OpenCV 修复

之前的问题：

- 参数层能拿到 `inpaint_radius`
- 但没有确保这项参数真实影响 OpenCV 修复执行

本次修复后：

- `AIHandler` 会把 `inpaint_radius` 真实传给 `ImageInpainter.inpaint_frame(radius=...)`
- `ImageInpainter` 会先算出 `effective_radius`
- `telea` / `navier_stokes` 最终使用的是 `effective_radius`
- `custom_interpolation` 当前不会直接消费这个半径，而是更多受 `quality_level` 驱动内部插值强度

当前真实行为：

- 调大 `修复半径`
  - 修复传播范围更大
  - 更适合边缘残留明显、区域略大的水印
  - 也更容易把周围正常纹理一起“抹进去”
- 调小 `修复半径`
  - 修复更克制
  - 更适合小水印、边缘清楚的区域
  - 但更容易留下残边、补不满

补充说明：

- 当前 OpenCV 路径里，`修复质量` 还会进一步影响最终的有效半径
- 也就是说，界面里相同的 `修复半径`，在 `质量 1` 和 `质量 5` 下，实际效果不会完全一样

---

### 4. 修复质量真正接进 OpenCV + 后处理

之前的问题：

- `quality_level` 可以从 UI 传下来
- 但没有真正统一影响 OpenCV 修复和后处理强度

本次修复后：

- `AIHandler` 会把 `quality_level` 真实传给 `ImageInpainter`
- `ImageInpainter` 会基于质量等级调整：
  - OpenCV 有效修复半径
  - `auto` 模式下的小 / 中 / 大区域分档阈值
  - `custom_interpolation` 的 padding、模糊核、形态学核、膨胀次数、过渡核
- `AIHandler` 还会基于质量等级构建后处理强度档位，真实传给 `apply_postprocessing()`

当前真实行为：

- 调低 `修复质量`
  - OpenCV 修复更克制
  - 后处理更轻
  - 速度与稳定性通常更好
  - 更适合预览、批量快速处理
- 调高 `修复质量`
  - OpenCV 修复更积极
  - 边缘平滑、混合、增强都会更强
  - 更适合追求最终观感
  - 但更容易出现“修大了”“抹软了”的副作用

重要边界：

- 当前 `修复质量` 只统一影响 `OpenCV + 后处理`
- 阶段二之后，`修复质量` 也已经开始影响 `GPU 深度学习 U-Net` 路径的最小 profile

---

## 当前修复参数的真实可调范围

### 已经真正可调

- `最小检测区域`
- `修复算法`
- `修复半径`
- `修复质量`
- `边缘平滑 / 颜色混合 / 图像增强` 的后处理开关
- `GPU U-Net` 的最小 profile：
  - `mask_expand_px`
  - `mask_feather_px`
  - `blend_ratio`
  - `resize_limit`

### 仍然不能误以为“已经打通”的部分

- `修复算法` 在 GPU 路径里仍不是“多种 GPU 修复算法切换器”
- `GPU U-Net` 目前还没有：
  - tile / overlap
  - second pass
  - OOM 自动降级重试
  - mixed precision 档位
- `inpaint_batch()` 当前仍复用单帧 profile 流程，优先保证行为一致性，不代表已经完成真正的批量推理优化

---

## 当前 GPU 深度学习 U-Net 路径的真实情况

### 1. 这条路径现在到底是什么

当前 GPU 修复器位于：

- `src/app/core/ai/dl_inpainter.py`

它实现的是：

- 项目内自定义的轻量级 `U-Net`
- 输入为 `RGB + mask` 共 `4` 通道
- 输出为 `3` 通道修复图像
- 输出不会再按硬掩码直接替换，而是会按 profile 做软混合

这说明它当前已经从“只会跑的骨架”升级成：

- 一条具备正式权重入口与明确降级的 GPU 修复路径
- 一条具备最小真实参数语义的 GPU profile 路径

但它仍然不是完整生产级形态，后面还需要继续补强。

---

### 2. 当前主流程是怎么调用它的

当前调用链大致是：

```text
AdvancedParametersWidget / AIParamsBuilder
  -> 产出 quality_level / inpaint_radius / use_gpu_inpainting / inpainting_model_path

VideoProcessorThread
  -> 把 ai_params 传给 AIHandler

AIHandler.load_models()
  -> _load_gpu_inpainter_or_fallback()
  -> 只有权重存在且加载成功才保留 GPU 路径

AIHandler.process_frame()
  -> AIHandler.inpaint_frame(frame, mask)

AIHandler.inpaint_frame()
  -> DeepLearningInpainter.inpaint_frame(
       frame,
       mask,
       radius=self.inpaint_radius,
       quality_level=self.quality_level,
     )

DeepLearningInpainter
  -> _build_inpainting_profile()
  -> _prepare_mask()
  -> _resize_for_inference()
  -> U-Net 推理
  -> _blend_with_original()
```

当前关键事实：

- `AIHandler` 已经会把 `inpainting_model_path` 真实传给 GPU 修复器
- 没有权重 / 权重不存在 / 加载失败时，会明确降级到 `OpenCV`
- `修复半径` 和 `修复质量` 已经开始真实改变 GPU 修复结果

---

### 3. 当前哪些参数对 GPU 路径生效

#### 已生效

- `use_gpu_inpainting`
  - 决定是否优先尝试 GPU 深度学习修复
- `device`
  - 决定优先使用 `cuda` / `cpu` / `auto`
- `inpainting_model_path`
  - 决定是否能真正启用 GPU U-Net
- `修复半径`
  - 映射到 `mask_expand_px`
  - 次级影响 `mask_feather_px`
- `修复质量`
  - 映射到 `resize_limit`
  - 映射到 `blend_ratio`
  - 映射到 `mask_feather_px`
- `GPU batch`
  - 会先按样本的**生效 profile**和**实际推理输入尺寸**分组
  - 兼容组走真实 batch 前向
  - 不兼容组只对该组顺序执行，不再整批退化
  - 某一组真实 batch 前向失败时，也只回退该组，优先保证结果语义一致

#### 当前仍保持简单的部分

- `修复算法`
  - 在 GPU 路径上目前仍主要表示“是否走 `gpu_dl`”
  - 不是 GPU 内部多种模型或多种修复算法的切换器

---

### 4. 当前最小 GPU profile 的真实语义

当前真实生效的 `GPUInpaintingProfile` 字段如下：

- `requested_radius`
  - 记录用户请求的修复半径
- `quality_level`
  - 记录用户请求的修复质量档位
- `mask_expand_px`
  - 控制送入 U-Net 前的掩码扩张范围
- `mask_feather_px`
  - 控制送入 U-Net 和最终融合时的边缘羽化强度
- `blend_ratio`
  - 控制生成结果与原图的融合强度
- `resize_limit`
  - 控制 GPU 推理时的输入最大边长

这套 profile 已经真实作用在：

1. 掩码几何范围
2. 边缘软化范围
3. 最终混合强度
4. 推理输入分辨率

---

## 当前 GPU U-Net 路径仍然不算完整生产形态的原因

虽然阶段一和阶段二已经把主链路打通，但下面这些能力仍然没有完成：

### 1. 还没有 tile / overlap / second pass

当前 GPU profile 只落地了最小字段：

- `mask_expand_px`
- `mask_feather_px`
- `blend_ratio`
- `resize_limit`

还没有：

- `tile_size`
- `tile_overlap`
- `second_pass`

这意味着超大图、高精细边缘和复杂内容场景，后续仍有提升空间。

### 2. 还没有 OOM / GPU 异常重试分级

当前已有“加载失败明确降级”的能力，但还没有更细的：

- OOM 后自动切小 profile 重试
- mixed precision 档位回退
- 推理时异常后自动切 OpenCV 并记录更完整上下文

### 3. 批量路径已经支持按组 batch，但还没做更高级吞吐优化

当前 `inpaint_batch()` 已能复用同一套 profile 语义，但重点是：

- 已支持按“同生效 profile + 同实际推理输入尺寸”分组
- 兼容组会执行真正的 batch tensor 前向
- 不兼容组或失败组只对该组顺序执行，继续优先保证每帧结果和单帧入口一致
- 还没有针对 batch tensor 继续叠加 tile、mixed precision、OOM 自动重试这类更高级优化

所以这一步可以视为“真实 batch 主路径已经建立”，但还不是“GPU 批量性能优化已经完全完成”。

### 4. 模型质量仍然依赖正式训练权重

即使主路径已经打通正式权重入口，当前轻量级 `U-Net` 的上限仍取决于：

- 训练数据质量
- checkpoint 兼容性
- 真实业务样本覆盖度

也就是说：

- 现在这条路已经“能解释、能观测、能调”
- 但是否达到最终生产效果，还取决于权重本身是否成熟

---

## GPU 深度学习 U-Net 路径后续方案

下面给出当前推荐的下一阶段方案，目标是从“最小真实可调”继续推进到“更稳的生产级 GPU 路径”。

### 阶段三：补 GPU 推理稳定性与高级 profile

建议新增：

```text
GPUInpaintingProfile
  - tile_size
  - tile_overlap
  - second_pass
  - mixed_precision
  - oom_retry_profile
```

建议优先级：

1. `tile_size / tile_overlap`
   - 先解决大图和高分辨率视频帧的稳定性
2. `OOM 回退策略`
   - 推理失败时按更保守 profile 自动重试
3. `mixed precision`
   - 兼顾显存和性能
4. `second_pass`
   - 作为最高质量档的可选增强

### 阶段四：补模型与观测能力

建议补充：

1. checkpoint 结构兼容校验
2. `processing_info` 记录更多 GPU 运行信息
   - 实际输入分辨率
   - 是否发生缩放
   - 是否发生重试
3. 独立的 GPU 路径回归测试样本
4. 高压缩字幕样、透明角标样、Logo 样本集专项回归

---

## 我更推荐的落地顺序

如果后续继续做，我建议按下面顺序推进：

1. 保持当前阶段一 + 阶段二结果稳定
2. 先补 `tile / overlap / OOM 降级`
3. 再补 `mixed precision / second pass`
4. 最后再做更激进的 GPU 高质量档位

原因是：

- 现在最重要的不是继续加字段，而是让 GPU 路径在真实样本上更稳
- 当前用户已经能真实调 `修复半径 / 修复质量`
- 下一步最值得投入的是“大图稳定性”和“异常回退能力”

---

## 本轮建议用户如何理解这些参数

如果当前仍以可用性和稳定性优先，建议这样理解：

- `修复算法 / 修复半径 / 修复质量`
  - 现在已经可以放心用于 `OpenCV + 后处理`
- `GPU 深度学习 U-Net`
  - 现在已经具备最小真实 profile
  - 可以真实调 `修复半径 / 修复质量`
  - 但仍应视为“正在走向生产级”的路径，而不是所有高级能力都已经齐全

如果当前项目目标是“尽快得到稳定、可解释、可调的结果”：

- 主路径仍建议优先以 `YOLO + OpenCV + 后处理` 为准
- GPU U-Net 可以开始用于专项样本验证和逐步替换，但还不建议把它描述成“高级 profile 已全部完善”的最终状态

---

## 关联文档

- 检测参数预设建议：`docs/detection_parameter_presets.md`
- 历史参数分析总文档：`docs/parameters_analysis.md`
