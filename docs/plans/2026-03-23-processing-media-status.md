# 处理中媒体类型文案分流 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让图片与视频在处理中阶段显示各自正确的媒体类型文案。

**Architecture:** 在 `SignalHandler` 统一判定媒体类型并生成文案，`PreviewPanel` 只负责展示传入的提示文本。单文件与批处理共用同一套文案构造逻辑。

**Tech Stack:** Python、PyQt6、pytest

---

### Task 1: 写失败测试

**Files:**
- Modify: `tests/unit/test_signal_handler_auto_mode.py`
- Create: `tests/unit/test_processing_media_status.py`

**Step 1: Write the failing test**
- 断言单文件图片开始处理时提示为“正在处理图片”。
- 断言单文件视频开始处理时提示为“正在处理视频”。
- 断言批处理当前文件切换时按扩展名显示正确类型。

**Step 2: Run test to verify it fails**
- Run: `python -m pytest "tests/unit/test_processing_media_status.py" -q`

### Task 2: 实现 UI 文案分流

**Files:**
- Modify: `src/app/ui/components/preview_panel.py`
- Modify: `src/app/ui/signal_handler.py`

**Step 1: Write minimal implementation**
- `PreviewPanel.show_processing_progress()` 支持传入文案。
- `SignalHandler` 新增媒体类型判定/文案构造辅助方法并复用。

**Step 2: Run test to verify it passes**
- Run: `python -m pytest "tests/unit/test_processing_media_status.py" -q`

### Task 3: 跑回归

**Files:**
- Test: `tests/unit/test_processing_media_status.py`
- Test: `tests/unit/test_signal_handler_auto_mode.py`
- Test: `tests/unit/test_dynamic_watermark_tracking.py`

**Step 1: Run focused regression**
- Run: `python -m pytest "tests/unit/test_processing_media_status.py" "tests/unit/test_signal_handler_auto_mode.py" "tests/unit/test_dynamic_watermark_tracking.py" -q`

**Step 2: Confirm all pass**
- 预期：全部通过。
