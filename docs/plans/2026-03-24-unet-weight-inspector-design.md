# U-Net 权重体检工具设计

**背景**

当前仓库已经支持通过 `inpainting_model_path` 加载 GPU 修复权重，但仓库内并没有现成的 U-Net 修复权重文件。实际排查时，容易遇到两个问题：

1. 候选文件名里带有 `unet`、`inpainting` 或 `.pt/.pth`，但并不一定能被当前仓库直接加载。
2. 外部模型常见的分发形式很多，包括原始 `state_dict`、包装 checkpoint、`module.` 前缀、多框架格式和扩散模型专用权重，人工判断成本高且容易误判。

**目标**

本次要提供一个本地可执行的“U-Net 权重体检工具”，用于快速回答这几个问题：

- 这个候选文件是不是当前仓库可直接加载的 GPU 修复权重？
- 如果不能直接加载，是“需要人工解包/改键名”还是“结构根本不兼容”？
- 如果给一个目录，里面哪些候选文件值得继续尝试？

**方案选择**

方案 A：一次性脚本。

- 在 `scripts/` 下新增一个单文件脚本，直接读取路径并打印诊断结果。

优点：

- 上手快。

缺点：

- 逻辑难复用，不利于单元测试。
- 后续真实 GPU 集成验证如果也要用到同一套判断逻辑，会产生重复代码。

方案 B：可导入校验模块 + 轻量命令行入口。

- 在 `src/app/utils` 中实现可复用的权重体检逻辑。
- 同一模块提供 `python -m` 命令行入口。

优点：

- 可测试、可复用、易于后续被集成测试或脚本调用。
- 与现有 `app.utils.model_downloader` 的工具风格一致。

缺点：

- 比一次性脚本多一点结构化设计。

方案 C：把体检逻辑直接塞进 `AIHandler` 或 `DeepLearningInpainter`。

优点：

- 离真实加载链路最近。

缺点：

- 诊断工具与业务运行时耦合，会扩大热点文件改动范围。
- 不利于单独做 CLI 与回归测试。

**推荐**

采用方案 B。

理由：

- 这个工具本质上是“离线诊断能力”，应独立于运行时主链路。
- 复用当前 `UNetInpaintingModel` 的结构约束做判断，既能保证结果可信，又能保持实现收敛。
- 后续如果要补真实 GPU smoke，也能复用同一套检查逻辑。

**关键设计**

1. 检查对象

- 以当前仓库真实使用的 `UNetInpaintingModel(in_channels=4, out_channels=3, base_channels=32)` 为唯一兼容基准。
- 参考模型的 `state_dict()` 作为标准键名和 shape 模板。

2. 输出分类

- `compatible`
  - 文件可被当前仓库按现状直接 `torch.load(...)` 后 `load_state_dict(...)` 成功加载。
- `needs_unpacking`
  - 文件顶层不是原始 `state_dict`，但存在 `state_dict`、`model`、`model_state_dict` 等嵌套字段，解包后可匹配。
- `needs_key_rewrite`
  - 权重形状兼容，但键名带有 `module.` 或 `model.` 等常见前缀，当前代码不能直接加载。
- `incompatible`
  - 键名、shape、对象结构或文件格式与当前模型不匹配。
- `load_error`
  - 文件存在，但当前环境无法按 `torch.load` 读取。
- `missing`
  - 路径不存在。

3. 检查流程

- 路径不存在时直接返回 `missing`。
- 遇到当前明确不支持的扩展名（如 `.safetensors`、`.onnx`、`.engine`）时，直接标记 `incompatible`，并说明“当前 loader 不支持该格式”。
- 对 `.pt/.pth/.bin/.ckpt` 等候选文件执行 `torch.load(..., map_location="cpu")`。
- 识别顶层对象：
  - 原始 `state_dict`
  - 包装 checkpoint
  - 非字典对象
- 对候选权重尝试三种匹配：
  - 原始精确匹配
  - 解包后精确匹配
  - 常见前缀剥离后的匹配
- 输出缺失键、额外键、shape 不匹配摘要，帮助定位问题。

4. 命令行入口

- 使用 `python -m app.utils.inpainting_weight_inspector <path>`。
- 当输入是文件时，输出单个诊断结果。
- 当输入是目录时，递归扫描常见权重扩展名并逐个输出。
- 退出码约定：
  - `0`：全部候选都可直接加载
  - `1`：存在需要人工处理或不兼容项
  - `2`：参数错误或执行异常

5. 测试策略

- 先写失败测试，再补最小实现。
- 单元测试最小覆盖：
  - 不存在文件
  - 原始兼容 `state_dict`
  - 包装 checkpoint（`state_dict`）
  - `module.` 前缀权重
  - shape 不匹配
  - 不支持扩展名
  - 目录扫描
  - CLI 退出码与关键输出

**边界与非目标**

- 本轮不自动转换权重文件，也不修改 `AIHandler` 加载逻辑。
- 本轮不尝试兼容 Hugging Face Diffusers、Safetensors、ONNX、TensorRT 等其他体系的模型格式。
- 本轮不直接下载外部 U-Net 权重，只提供本地判定能力。
