# 候选权重自动筛查清单

**日期**

- 2026-03-24

**目标**

- 给“网上常见的模型权重文件”做一个面向本仓库的自动筛查口径
- 明确哪些可以直接试，哪些需要转换，哪些不要推荐
- 避免把“名字里有 U-Net”误判成“当前仓库可直接用”

---

## 1. 先说结论

当前仓库的 GPU 修复权重筛查，必须围绕这一条来做：

**候选文件是否能按现状被 `torch.load(...)` 读取，并能被当前 `UNetInpaintingModel(4 -> 3, base_channels=32)` 直接 `load_state_dict(...)` 成功加载。**

因此分类口径应严格收敛为三类：

### 可直接试

- 单文件 `.pt/.pth/.ckpt/.bin`
- 顶层就是原始 PyTorch `state_dict`
- 与当前仓库 U-Net 键名和 shape 直接匹配

### 需要转换

- 仍然是“同一套 U-Net 架构”的权重
- 但包装形式不符合当前 loader 语义
- 例如：
  - `{"state_dict": ...}`
  - `{"model": ...}`
  - `{"model_state_dict": ...}`
  - `module.` / `model.` 前缀

### 不要推荐

- 虽然文件名像模型权重，但体系、架构或格式与当前 loader 不匹配
- 例如：
  - Ultralytics / YOLO `.pt`
  - Diffusers `unet/diffusion_pytorch_model.safetensors`
  - `.onnx`
  - `.engine`
  - `.trt`
  - 各类分割任务 U-Net、医学影像 U-Net、扩散模型 U-Net

---

## 2. 分类规则

## 2.1 可直接试

满足以下条件时，才建议归入“可直接试”：

1. 单文件 PyTorch 权重
2. README 或训练代码明确采用：

```python
torch.save(model.state_dict(), "xxx.pth")
```

3. 恢复方式写的是：

```python
state_dict = torch.load("xxx.pth", map_location="cpu")
model.load_state_dict(state_dict)
```

4. 任务语义是：
  - inpainting
  - watermark removal
  - image restoration
5. 结构特征与当前仓库一致：
  - 输入是 `RGB + mask`
  - 即首层卷积等价于 `4` 通道输入
  - 输出是 `3` 通道图像

### 典型可直接试文件特征

- `unet-stage1.pth`
- `watermark_inpaint_unet.pth`
- `inpainting_weights.pth`

注意：

- **这些只是“名字特征”，不是充分条件。**
- 最终仍必须过本地体检工具。

---

## 2.2 需要转换

只有下面这类情况，才应该归入“需要转换”：

### 包装 checkpoint

常见形式：

```python
{
  "state_dict": ...,
  "epoch": ...,
  "optimizer": ...
}
```

或：

```python
{
  "model": ...,
  ...
}
```

或：

```python
{
  "model_state_dict": ...,
  ...
}
```

这类文件的问题通常不是“架构错了”，而是“当前 loader 不会自动解包”。

### 常见键名前缀

例如：

- `module.`
- `model.`

这通常来自并行训练或训练脚本封装层。

### 归入“需要转换”的严格前提

解包或去前缀之后，仍然必须满足：

- 键名能对齐当前仓库 U-Net
- shape 能对齐当前仓库 U-Net

如果这两条不成立，就不能再叫“需要转换”，而应直接归入“不要推荐”。

---

## 2.3 不要推荐

以下几类虽然网上很常见，但**不建议**作为当前仓库 GPU 修复权重候选：

### A. Ultralytics / YOLO `.pt`

官方文档中，YOLO 权重是这样加载的：

- `model = YOLO("yolo26n.pt")`

这说明它们属于 Ultralytics / YOLO 模型体系，而不是当前仓库要吃的原始 U-Net `state_dict`。  
来源：Ultralytics 官方文档  
https://docs.ultralytics.com/

对本仓库来说：

- 这类文件可能是目标检测模型
- 不是修复 U-Net 权重
- 不应归入“可直接试”
- 一般也不应归入“需要转换”

### B. Diffusers `unet/diffusion_pytorch_model.safetensors`

Diffusers 官方文档中，典型加载方式是：

- `UNet2DConditionModel.from_pretrained("runwayml/stable-diffusion-v1-5", subfolder="unet")`

这说明它们是 Diffusers 体系下的组件化 U-Net，而不是当前仓库这种“单文件原始 state_dict + 轻量修复 U-Net”的语义。  
来源：Hugging Face Diffusers 官方文档  
https://huggingface.co/docs/diffusers/v0.20.0/api/models/overview

而且 Hugging Face 上常见文件路径就是：

- `unet/diffusion_pytorch_model.safetensors`

例如：

- `diffusers/stable-diffusion-xl-1.0-inpainting-0.1/unet/diffusion_pytorch_model.safetensors`

来源：Hugging Face 模型文件页面  
https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1/blob/main/unet/diffusion_pytorch_model.safetensors

对本仓库来说：

- 名字里虽然有 `unet`
- 但模型体系不同
- 存储格式也不同
- 不应推荐为当前仓库的直接候选

### C. ONNX / TensorRT / `.engine` / `.trt`

这类文件不是当前 loader 支持的格式。

当前仓库体检工具已经把它们归为：

- `incompatible`

因此不应归入“可直接试”或“需要转换”。

### D. 各类分割任务 U-Net

例如：

- 医学分割
- 语义分割
- 裂缝检测
- 遥感分割

它们虽然经常叫 U-Net，但通常只说明“网络家族类似”，不说明和当前轻量修复 U-Net 同架构。

常见问题包括：

- 输入通道是 `1` 或 `3`
- 输出通道是类别数，不是 RGB
- backbone、skip connection、head 结构不同

这类文件默认都不应推荐。

---

## 3. 官方资料给出的关键筛查信号

### PyTorch 官方信号

PyTorch 官方建议：

- 更推荐保存 `state_dict`
- 再通过 `load_state_dict()` 恢复

来源：PyTorch 官方序列化文档  
https://docs.pytorch.org/docs/stable/notes/serialization

同时，PyTorch 2.6 之后：

- `torch.load()` 默认使用 `weights_only=True`
- 这更偏向“只读纯权重”
- 遇到复杂 pickled 对象时会报安全相关错误

来源：PyTorch 官方 `torch.load` / 序列化文档  
https://docs.pytorch.org/docs/stable/generated/torch.load.html  
https://docs.pytorch.org/docs/stable/notes/serialization

这对我们的筛查很重要：

- 原始 `state_dict` 更容易直接通过
- 复杂训练 checkpoint、整模型 pickle、框架对象更容易被拦住

### Lightning 官方信号

Lightning 官方明确指出，一个 `.ckpt` 往往不仅包含权重，还包含：

- epoch
- global step
- optimizer state
- scheduler state
- hyperparameters

来源：Lightning 官方 checkpoint 文档  
https://lightning.ai/docs/pytorch/2.0.0/common/checkpointing_basic.html

这说明：

- `.ckpt` 不能天然视为“可直接试”
- 它通常更像“需要解包的训练 checkpoint”

---

## 4. 面向实际排查的自动筛查步骤

### 第一步：先看来源和任务

优先排除：

- detection
- segmentation
- diffusion
- text-to-image
- stable diffusion
- yolov*

优先保留：

- inpainting
- watermark removal
- image restoration

### 第二步：再看文件形态

优先保留：

- 单文件 `.pth/.pt/.ckpt`

谨慎看待：

- 目录型模型
- `unet/diffusion_pytorch_model.safetensors`
- 多分片模型

### 第三步：用体检工具跑一遍

```bash
.venv/Scripts/python.exe -m app.utils.inpainting_weight_inspector "path/to/candidate"
```

### 第四步：按结果落类

- `compatible`
  - 归入“可直接试”
- `needs_unpacking`
  - 归入“需要转换”
- `needs_key_rewrite`
  - 归入“需要转换”
- `incompatible`
  - 归入“不要推荐”
- `load_error`
  - 默认归入“不要推荐”
  - 但若来源可信、且你明确知道它只是历史 checkpoint/复杂 pickle，可再人工复核
- `missing`
  - 不是候选

---

## 5. 一句话版清单

### 可直接试

- 原始 PyTorch `state_dict`
- 单文件 `.pt/.pth/.ckpt/.bin`
- 当前 U-Net 键名和 shape 直接匹配

### 需要转换

- `state_dict/model/model_state_dict` 包装 checkpoint
- `module.` / `model.` 前缀
- 前提是：解包或改键后仍是当前同一 U-Net 架构

### 不要推荐

- YOLO `.pt`
- Diffusers `unet/diffusion_pytorch_model.safetensors`
- `.onnx/.engine/.trt`
- 各类分割/检测/扩散任务 U-Net

---

## 6. 当前仓库的直接结论

把这套筛查清单应用到当前仓库后，结果是：

- 仓库里现有 `models/*.pt` 都属于 **YOLO 检测权重**
- 它们不属于“可直接试”
- 也不应归入“需要转换”
- 应直接归入“不要推荐”

因此，下一步应去外部继续寻找真正的 GPU 修复 U-Net 候选，再用本地体检工具预筛。
