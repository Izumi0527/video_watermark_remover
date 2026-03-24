# 批处理取消与清单追溯修复 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复批处理取消返回值不一致与 manifest 运行参数追溯失真问题，并补齐回归测试。

**Architecture:** 保持现有 `BatchProcessorThread -> SignalHandler -> manifest` 链路不变，只修正取消分支返回结构，并在 `SignalHandler` 中缓存最近一次批处理运行快照。所有行为先通过失败测试锁定，再做最小化实现修改。

**Tech Stack:** Python 3.12、PyQt6、pytest

---

### Task 1: 为批处理取消分支补回归测试

**Files:**
- Modify: `tests/unit/test_batch_processor_preloaded_policy.py`
- Modify: `src/app/ui/widgets/batch/batch_processor_thread.py`

**Step 1: Write the failing test**

新增一个测试，模拟 `VideoProcessorThread` 已创建但尚未进入 `run()` 时 `should_stop=True`，断言 `_process_single_file()` 返回三元组，且状态为 `CANCELLED`。

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/unit/test_batch_processor_preloaded_policy.py -k cancelled`

Expected: 失败，暴露当前返回单个 `ProcessingStatus` 的问题。

**Step 3: Write minimal implementation**

将 `_process_single_file()` 中该取消分支改为返回 `(ProcessingStatus.CANCELLED, "用户取消", None)`。

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/unit/test_batch_processor_preloaded_policy.py`

Expected: 全部通过。

### Task 2: 为 manifest 运行快照补失败测试

**Files:**
- Create: `tests/unit/test_signal_handler_batch_manifest.py`
- Modify: `src/app/ui/signal_handler.py`

**Step 1: Write the failing tests**

新增 2 个测试：

- 最近一次批处理结束后，导出 manifest 仍应带出最近一次运行的 `ai_params` 和批处理配置。
- 清空队列或替换新队列后，旧的最近运行快照应失效，避免污染新导出结果。

**Step 2: Run tests to verify they fail**

Run: `pytest -q tests/unit/test_signal_handler_batch_manifest.py`

Expected: 失败，分别暴露“结束后 batch 配置丢失”和“旧快照未清空”的问题。

**Step 3: Write minimal implementation**

- 在 `SignalHandler` 中新增最近一次批处理运行快照字段。
- 在启动批处理时记录 `ai_params`、并发数、重试配置和时间戳。
- 在清空队列、替换多文件队列时清空旧快照。
- manifest 导出时优先读取活动线程，其次读取最近一次运行快照。

**Step 4: Run tests to verify they pass**

Run: `pytest -q tests/unit/test_signal_handler_batch_manifest.py`

Expected: 全部通过。

### Task 3: 回归验证

**Files:**
- Verify: `tests/unit/test_dynamic_watermark_tracking.py`
- Verify: `tests/unit/test_batch_processor_preloaded_policy.py`
- Verify: `tests/unit/test_signal_handler_batch_manifest.py`

**Step 1: Run targeted regression suite**

Run: `pytest -q tests/unit/test_dynamic_watermark_tracking.py tests/unit/test_batch_processor_preloaded_policy.py tests/unit/test_signal_handler_batch_manifest.py`

Expected: 全部通过。

**Step 2: Review changed behavior**

检查：

- 取消文件不会误记为失败。
- manifest 中 `run.ai_params`、`run.ai_params_source`、`batch.max_concurrent_files` 等字段在任务结束后仍可追溯。
- 清空或替换队列后，不会继续输出旧批次参数。
