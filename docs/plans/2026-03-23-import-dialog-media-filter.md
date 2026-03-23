# 导入对话框默认媒体过滤器 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让导入文件对话框首次打开时默认同时显示图片和视频文件。

**Architecture:** 抽取统一的导入过滤器常量，由 `SignalHandler` 与 `BatchFileManager` 共同复用。只改文件选择层，避免影响后续预览与处理链路。

**Tech Stack:** Python、PyQt6、pytest

---

### Task 1: 锁定当前错误行为

**Files:**
- Test: `tests/unit/test_import_dialog_filters.py`

**Step 1: Write the failing test**
- 断言主导入入口使用的过滤器首项为“支持的文件（图片+视频）”。
- 断言批量导入入口复用同一份过滤器定义。

**Step 2: Run test to verify it fails**
- Run: `python -m pytest "tests/unit/test_import_dialog_filters.py" -q`

### Task 2: 抽取统一过滤器

**Files:**
- Create: `src/app/ui/utils/file_dialog_filters.py`
- Modify: `src/app/ui/utils/__init__.py`
- Modify: `src/app/ui/signal_handler.py`
- Modify: `src/app/ui/widgets/batch/batch_file_manager.py`

**Step 1: Write minimal implementation**
- 新增统一过滤器常量。
- 主入口与批量入口改为复用该常量。

**Step 2: Run tests to verify they pass**
- Run: `python -m pytest "tests/unit/test_import_dialog_filters.py" -q`

### Task 3: 运行回归验证

**Files:**
- Test: `tests/unit/test_import_dialog_filters.py`
- Test: `tests/unit/test_signal_handler_auto_mode.py`

**Step 1: Run focused regression**
- Run: `python -m pytest "tests/unit/test_import_dialog_filters.py" "tests/unit/test_signal_handler_auto_mode.py" -q`

**Step 2: Confirm no regressions**
- 预期：全部通过。
