# 本地候选权重体检报告

**日期**

- 2026-03-24

**目标**

- 使用当前仓库新增的 `U-Net 权重体检工具`
- 对当前仓库里真实存在的候选 `.pth/.pt/.ckpt` 文件做一次实际体检
- 明确哪些文件值得继续尝试作为 GPU 修复 U-Net 权重，哪些不值得

---

## 1. 体检基准

本次体检严格以当前仓库真实 loader 语义为准：

- `DeepLearningInpainter.load_model()` 会固定实例化：
  - `UNetInpaintingModel(in_channels=4, out_channels=3, base_channels=32)`
- 然后执行：
  - `torch.load(model_path, map_location=device)`
  - `self.model.load_state_dict(state_dict)`

这意味着，只有“**能按当前语义被直接加载的原始 PyTorch `state_dict`**”才应视为当前仓库可直接用的 GPU 修复 U-Net 权重。

当前参考 U-Net 权重的关键特征：

- 权重键总数：`108`
- 典型 shape：
  - `enc1.0.weight = [32, 4, 3, 3]`
  - `enc4.0.weight = [256, 128, 3, 3]`
  - `bottleneck.0.weight = [512, 256, 3, 3]`
  - `out_conv.weight = [3, 32, 1, 1]`

---

## 2. 检查范围

本次实际盘点时，排除了这些环境噪声目录：

- `.venv`
- `.cache`
- `.uv-cache`
- `site-packages`

排除后，当前仓库内真实存在的候选权重文件只有 2 个：

1. [yolo11x-watermark.pt](/C:/cascadeProjects/video_watermark_remover/models/yolo11x-watermark.pt)
2. [yolo11x-watermark-corzent.pt](/C:/cascadeProjects/video_watermark_remover/models/yolo11x-watermark-corzent.pt)

额外核对后发现：

- [README.md](/C:/cascadeProjects/video_watermark_remover/models/README.md) 明确说明 `models/` 当前存放的是 YOLO 水印检测模型。
- `tests/test_data` 和 `docs` 中虽然出现了多个 `.pth` 路径或 U-Net 元数据，但都只是示例配置、占位路径或元数据说明，不是当前仓库内真实存在的候选权重文件。

---

## 3. 实际体检结果

### 3.1 [yolo11x-watermark.pt](/C:/cascadeProjects/video_watermark_remover/models/yolo11x-watermark.pt)

- 大小：`114,512,018` 字节
- 体检结果：`load_error`
- 原因码：`torch_load_failed`
- 工具输出核心信号：
  - `Weights only load failed`
  - `Unsupported global: GLOBAL ultralytics.nn.tasks.DetectionModel`

结论：

- 这不是当前仓库可直接加载的 U-Net 修复权重。
- 结合文件名与 [README.md](/C:/cascadeProjects/video_watermark_remover/models/README.md)，可以高置信度判断它属于 **Ultralytics / YOLO 检测模型权重**。
- 作为“水印检测模型”应保留。
- 作为“GPU 修复 U-Net 权重”**不应继续尝试**。

### 3.2 [yolo11x-watermark-corzent.pt](/C:/cascadeProjects/video_watermark_remover/models/yolo11x-watermark-corzent.pt)

- 大小：`114,434,898` 字节
- 体检结果：`load_error`
- 原因码：`torch_load_failed`
- 工具输出核心信号：
  - `Weights only load failed`
  - `Unsupported global: GLOBAL ultralytics.nn.tasks.DetectionModel`

结论：

- 这同样不是当前仓库可直接加载的 U-Net 修复权重。
- 它属于 **YOLO 水印检测权重的 corzent 微调版本**，不是当前修复器所需的原始 U-Net `state_dict`。
- 作为“水印检测模型”应保留。
- 作为“GPU 修复 U-Net 权重”**不应继续尝试**。

---

## 4. 仓库内容易误导排查的“假候选”

### 4.1 [ai_model_config.yaml](/C:/cascadeProjects/video_watermark_remover/tests/test_data/configs/ai_model_config.yaml)

- 出现的示例路径：`models/watermark_removal.pth`
- 文件性质：示例配置，不是真实权重
- 风险点：
  - 里面写了 `architecture: "unet"`
  - 但输入元数据是 `channels: 3`

而当前仓库真实 U-Net loader 需要：

- `in_channels=4`
- 即 `RGB + mask`

所以即便未来真有这份 `watermark_removal.pth`，也**不能仅凭名字和元数据就视为直接兼容**。

### 4.2 [model_metadata.json](/C:/cascadeProjects/video_watermark_remover/tests/test_data/models/model_metadata.json)

- 文件性质：元数据说明，不是真实权重
- 它写了：
  - `基于UNet架构`
  - `input_shape: [3, 512, 512]`

这同样和当前仓库实际 GPU 修复 U-Net 的 4 通道输入约束不一致，只能作历史/概念参考，不能当真实候选。

### 4.3 文档与测试中的字符串占位

下面这些路径只说明“曾经规划或测试过这种命名”，不代表仓库里真的有可用权重：

- `models/unet-stage1.pth`
- `stub-unet.pth`

---

## 5. 汇总结论

本地当前结论非常明确：

1. 当前仓库内真实候选 `.pth/.pt/.ckpt` 文件只有 2 个。
2. 这 2 个都属于 YOLO 水印检测权重，不是 GPU 修复 U-Net 权重。
3. 当前仓库里 **没有** 现成可直接用于 GPU 修复的 U-Net 权重文件。
4. 下一步不应该继续反复尝试 `models/*.pt`，而应该转向“从外部筛选候选 U-Net 权重，再用体检工具做预筛”。

---

## 6. 推荐下一步

- 对外部候选文件，优先找这类特征：
  - 单文件 `.pth/.pt/.ckpt`
  - README 明确写 `torch.save(model.state_dict(), ...)`
  - 明确是 inpainting / watermark removal / image restoration，而不是 detection
  - 最好明确是 `RGB + mask` 四通道输入
- 拿到候选文件后，先执行：

```bash
.venv/Scripts/python.exe -m app.utils.inpainting_weight_inspector "path/to/candidate.pth"
```

- 如果体检结果不是：
  - `compatible`
  - 或者非常明确的 `needs_unpacking` / `needs_key_rewrite`

则不建议直接进入 GPU 主链尝试。
