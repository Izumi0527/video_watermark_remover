# YOLO Corzent 水印模型接入 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新增 `yolo11x-watermark-corzent` 模型类型，支持自动下载+SHA256校验，并在失败时自动降级到 `yolo11x-watermark`。

**Architecture:** 通过扩展 `ModelDownloader.MODELS` 接入新模型；`YOLOWatermarkDetector` 放开可选 `model_type` 并在解析阶段对新模型进行一次性降级回退。

**Tech Stack:** Python、ConfigParser、urllib、pytest、ultralytics（运行时）

---

### Task 1: 添加失败用例（TDD - RED）

**Files:**
- Modify: `tests/unit/test_model_downloader.py`
- Create: `tests/unit/test_yolo_detector_model_fallback.py`

**Step 1: 扩展 ModelDownloader 单测（应先失败）**
- 断言 `ModelDownloader.MODELS` 包含 `yolo11x-watermark-corzent`
- 断言其包含 `url/filename/size_mb/description/sha256` 字段

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_model_downloader.py -q`
Expected: FAIL（新 key 尚未添加）

**Step 2: 新增 YOLO detector 降级单测（应先失败）**
- 构造最小 `ConfigParser`，设置 `model_type=yolo11x-watermark-corzent` 且 `auto_download_model=no`
- 仅创建 fallback 模型文件（`yolo11x-watermark.pt`）到临时目录
- 期望：初始化 detector 时不抛异常，并最终解析到 fallback 模型路径

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_yolo_detector_model_fallback.py -q`
Expected: FAIL（当前不支持该 model_type 且无降级逻辑）

### Task 2: 实现下载器模型配置（TDD - GREEN）

**Files:**
- Modify: `src/app/utils/model_downloader.py`

**Step 1: 在 MODELS 中新增 `yolo11x-watermark-corzent`**
- `filename`: `yolo11x-watermark-corzent.pt`
- `url`: Hugging Face resolve 链接
- `sha256`: 固定 64 位校验值（来自 HEAD ETag）

**Step 2: 运行单测**
Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_model_downloader.py -q`
Expected: PASS

### Task 3: 实现 detector 支持与降级（TDD - GREEN）

**Files:**
- Modify: `src/app/core/ai/yolo_detector.py`

**Step 1: 放开 `model_type` 白名单**
- 支持：`yolo11s`、`yolo11x-watermark`、`yolo11x-watermark-corzent`、`custom`

**Step 2: 解析阶段增加一次性降级**
- 仅当 `model_type=yolo11x-watermark-corzent` 且解析失败时，回退到 `yolo11x-watermark`

**Step 3: 运行单测**
Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_yolo_detector_model_fallback.py -q`
Expected: PASS

### Task 4: 同步配置与文档

**Files:**
- Modify: `config.ini.example`
- Modify: `models/README.md`

**Step 1: 更新 `model_type` 说明**
- 增加 `yolo11x-watermark-corzent` 选项

**Step 2: 文档新增该模型介绍/切换示例**

### Task 5: 回归验证

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit -q`
Expected: PASS（不超过 60s 为佳；如超时则缩小到相关用例）

> 可选提交（如需要）：本仓库约定提交信息为 `feat(yolo): ...`，但是否提交由维护者决定。
