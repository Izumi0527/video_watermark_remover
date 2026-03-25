# U-Net 权重体检工具 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新增一个本地可执行的 U-Net 权重体检工具，用于判断候选文件是否能被当前仓库直接作为 GPU 修复权重加载。

**Architecture:** 将核心诊断逻辑收敛到 `src/app/utils/inpainting_weight_inspector.py`，直接复用当前 `UNetInpaintingModel` 的结构模板做判断；同一模块提供轻量 CLI 入口，文件与目录都走同一套检查逻辑。实现顺序遵循 TDD：先写失败测试，再补最小实现，最后做定向回归验证。

**Tech Stack:** Python 3.12、PyTorch、pytest、argparse

---

### Task 1: 新增权重体检核心测试

**Files:**
- Create: `tests/unit/test_inpainting_weight_inspector.py`

**Step 1: Write the failing tests**

新增最小测试矩阵，至少覆盖：

- 不存在路径返回 `missing`
- 原始兼容 `state_dict` 返回 `compatible`
- 包装 checkpoint（`state_dict`）返回 `needs_unpacking`
- `module.` 前缀权重返回 `needs_key_rewrite`
- shape 不匹配返回 `incompatible`
- `.safetensors` 返回格式不支持
- 目录扫描能枚举多个候选
- CLI 在“全部兼容”和“包含不兼容项”时返回不同退出码

**Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_weight_inspector.py -q`

Expected: 失败，提示缺少模块或断言不成立。

**Step 3: Write minimal implementation**

先只补最小数据结构和函数签名，让测试逐步逼出真实行为。

**Step 4: Run test to verify it fails correctly**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_weight_inspector.py -q`

Expected: 失败原因收敛到具体行为缺口，而不是导入错误。

### Task 2: 实现核心权重体检逻辑

**Files:**
- Create: `src/app/utils/inpainting_weight_inspector.py`
- Modify: `src/app/utils/__init__.py`

**Step 1: Implement direct compatibility inspection**

- 构建参考 `UNetInpaintingModel` 的标准 `state_dict`
- 识别原始 `state_dict`
- 比对键名与 shape

**Step 2: Implement wrapped checkpoint and prefix analysis**

- 识别 `state_dict`、`model`、`model_state_dict` 包装形式
- 识别 `module.` / `model.` 常见前缀
- 输出建议说明

**Step 3: Implement directory scan and CLI entry**

- 支持文件与目录输入
- 用 `argparse` 解析参数
- 输出摘要与退出码

**Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_weight_inspector.py -q`

Expected: 全部通过。

### Task 3: 做定向验证并检查无关回归

**Files:**
- Verify: `tests/unit/test_inpainting_weight_inspector.py`
- Verify: `src/app/core/ai/dl_inpainter.py`
- Verify: `src/app/utils/inpainting_weight_inspector.py`

**Step 1: Run targeted verification**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_weight_inspector.py tests/unit/test_image_inpainter.py -q`

Expected: 相关工具测试通过，未破坏现有图像修复基础行为。

**Step 2: Smoke the CLI**

Run: `.venv/Scripts/python.exe -m app.utils.inpainting_weight_inspector models`

Expected: 输出当前目录候选文件诊断结果，并返回非零退出码，因为本地只有 YOLO 权重且不兼容当前 U-Net。

**Step 3: Review docs and usage**

确认设计文档、实现计划与 CLI 实际行为一致。
