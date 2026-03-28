# 运行模式可观测性增强 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让用户在 GUI 和文件日志中明确看到当前请求模式、实际运行模式、自动降级原因以及单进程长任务仍在持续推进。

**Architecture:** 复用现有统一性能参数快照，在 `SignalHandler` 启动入口生成首屏提示，在 `DetailedProgressWidget` 持续展示运行模式摘要，并在单进程处理循环中补充周期性心跳日志。核心运行模式护栏逻辑不变，只增强可观测性。

**Tech Stack:** Python 3.12、PyQt6、pytest

---

### Task 1: 统一运行模式展示文案

**Files:**
- Modify: `src/app/config/advanced_params.py`
- Test: `tests/unit/test_processing_mode_observability.py`

**Step 1: Write the failing test**

- 为“请求模式 / 实际模式 / 限制原因”的中文摘要与提示补测试。

**Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_processing_mode_observability.py -q`

**Step 3: Write minimal implementation**

- 新增运行模式摘要和限制原因中文文案函数。

**Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_processing_mode_observability.py -q`

### Task 2: 启动时把运行模式快照推到 UI

**Files:**
- Modify: `src/app/ui/signal_handler.py`
- Test: `tests/unit/test_signal_handler_thread_mode_passthrough.py`

**Step 1: Write the failing test**

- 断言开始处理时，详细进度区和日志面板都能收到运行模式快照。

**Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_signal_handler_thread_mode_passthrough.py -q`

**Step 3: Write minimal implementation**

- 在 `handle_start_processing()` 中推送统一的运行模式状态和提示。

**Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_signal_handler_thread_mode_passthrough.py -q`

### Task 3: 详细进度区持续展示运行模式

**Files:**
- Modify: `src/app/ui/components/detailed_progress_widget.py`
- Test: `tests/unit/test_detailed_progress_widget_runtime_hint.py`

**Step 1: Write the failing test**

- 断言组件能显示运行模式摘要和护栏提示。

**Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_detailed_progress_widget_runtime_hint.py -q`

**Step 3: Write minimal implementation**

- 增加运行模式展示标签，并在 `update_progress()` 中更新。

**Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_detailed_progress_widget_runtime_hint.py -q`

### Task 4: 单进程长任务心跳日志

**Files:**
- Modify: `src/app/core/video/modes/single_process.py`
- Test: `tests/unit/core/video/test_single_process_runtime_observability.py`

**Step 1: Write the failing test**

- 断言单进程处理时会输出包含模式信息的心跳日志。

**Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/core/video/test_single_process_runtime_observability.py -q`

**Step 3: Write minimal implementation**

- 按时间间隔输出心跳日志，包含帧进度、速度、ETA 和运行模式摘要。

**Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/core/video/test_single_process_runtime_observability.py -q`

### Task 5: 回归验证

**Files:**
- Test: `tests/unit/test_processing_mode_observability.py`
- Test: `tests/unit/test_signal_handler_thread_mode_passthrough.py`
- Test: `tests/unit/test_detailed_progress_widget_runtime_hint.py`
- Test: `tests/unit/core/video/test_single_process_runtime_observability.py`

**Step 1: Run focused verification**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_processing_mode_observability.py tests/unit/test_signal_handler_thread_mode_passthrough.py tests/unit/test_detailed_progress_widget_runtime_hint.py tests/unit/core/video/test_single_process_runtime_observability.py -q`

**Step 2: 若通过，再补跑受影响既有回归**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/core/video/test_single_process_output_audio.py tests/unit/core/video/test_runtime_guard.py tests/unit/test_advanced_parameters_widget_runtime_model.py -q`
