# YOLO Corzent 水印模型接入设计

> 日期：2026-03-22  
> 目标：在不破坏现有默认行为的前提下，为项目新增一个可选的“更高精度”水印检测模型来源，并做到可切换、可校验、可回滚。

## 背景与问题

当前项目默认使用 `yolo11x-watermark`（YOLOv11x 微调权重）进行水印检测，但实际使用中仍可能出现：

- A：漏检（小水印/半透明/复杂背景）
- B：误检（把正常内容判作水印）
- C：边界不准（检测框转 mask 过粗导致处理范围不精确）

本次变更聚焦“更换更高精度检测权重”，用于改善 A/B（漏检/误检）。边界精细度（C）受限于当前 `boxes → 矩形mask(+padding)` 的后处理上限，本次不在范围内（后续可单独升级到分割/细化）。

## 方案概述

新增一个模型类型 `yolo11x-watermark-corzent`，指向 Hugging Face 模型仓库：

- 模型：`corzent/yolo11x_watermark_detection`
- 权重文件：`best.pt`
- 下载地址（resolve）：`https://huggingface.co/corzent/yolo11x_watermark_detection/resolve/main/best.pt`

在项目中以新文件名落盘，避免覆盖现有默认模型：

- `models/yolo11x-watermark-corzent.pt`

并在下载后进行 SHA256 校验，若校验失败则删除文件并判定失败。

## 回滚策略

- 手动回滚：将 `config.ini` 的 `[YOLO] model_type` 改回 `yolo11x-watermark`。
- 自动回滚（仅针对新模型）：当新模型“解析/下载/校验”失败时，自动降级到 `yolo11x-watermark` 并继续执行（同时输出清晰日志）。

## 影响范围（文件）

- 逻辑：
  - `src/app/utils/model_downloader.py`：新增模型配置与校验
  - `src/app/core/ai/yolo_detector.py`：允许新 model_type，并在解析失败时降级
- 配置与文档：
  - `config.ini.example`：补充 `model_type` 可选值说明
  - `models/README.md`：新增模型说明与使用示例
- 测试：
  - `tests/unit/test_model_downloader.py`：新增模型 key/字段断言
  - 新增单测：验证 `YOLOWatermarkDetector` 在新模型解析失败时可自动降级

## 验收标准

1. `ModelDownloader.list_available_models()` 能列出 `yolo11x-watermark-corzent`，并能正常下载到 `models/` 目录。
2. 当配置 `model_type=yolo11x-watermark-corzent` 且新模型不可用时（例如下载失败/禁用自动下载），程序会记录降级日志并回退到 `yolo11x-watermark`。
3. 运行 `pytest tests/unit/test_model_downloader.py -q` 通过。

## 风险与约束

- PyTorch `.pt` 权重属于反序列化载入，需避免加载来源不可信的权重；本方案只接入固定来源，并加入 SHA256 校验以降低传输损坏风险。
- 本次不改动推理/后处理算法，不保证 C（边界精细）显著提升；若 C 是主要痛点，应升级到分割模型输出或二阶段细化。
