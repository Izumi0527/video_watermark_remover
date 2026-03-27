# Performance Parameters Second Review Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复第二次复审发现的 3 个剩余问题，并收紧流水线缓存预算语义，确保性能参数在默认值、预加载、批处理和实际运行时之间完全一致。

**Architecture:** 继续沿用 `AdvancedParamsSnapshot -> ProcessingContext -> ResolvedPerformanceConfig` 三层模型，但把消费边界进一步压实：偏好层只在缺失时迁移 legacy，预加载改为运行时签名 refresh，批处理改为按文件解析运行时配置，流水线缓存预算改为更接近 MB 语义的分配模型。

**Tech Stack:** Python 3.12、PyQt6、pytest、OpenCV、PyTorch、FFmpeg

---

### Task 1: 锁住默认值与 legacy 迁移边界

**Files:**
- Modify: `tests/unit/app/config/preferences/test_advanced_params_preferences.py`
- Modify: `src/app/config/preferences/manager.py`

**Step 1: Write the failing test**

```python
def test_existing_advanced_params_defaults_are_not_overridden_by_legacy_fields() -> None:
    manager.preferences = {
        "advanced_params": AdvancedParamsSnapshot.defaults().to_dict(),
        "advanced": {"max_threads": 8, "cache_size_mb": 2048},
        "batch": {"max_concurrent_files": 4, "max_retry_count": 7},
    }

    snapshot = manager.get_advanced_params_snapshot()

    assert snapshot == AdvancedParamsSnapshot.defaults()
```

**Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest -q "tests/unit/app/config/preferences/test_advanced_params_preferences.py"`

Expected: FAIL，说明默认值仍会被 legacy 字段覆盖。

**Step 3: Write minimal implementation**

```python
if isinstance(current_preferences, dict) and current_preferences:
    migrated = dict(current_preferences)
else:
    migrated = migrate_legacy_performance_preferences(...)
```

**Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest -q "tests/unit/app/config/preferences/test_advanced_params_preferences.py"`

Expected: PASS，说明 `advanced_params` 已存在时不会再被 legacy 回灌。

### Task 2: 让预加载 refresh 改为运行时签名

**Files:**
- Create: `tests/unit/test_ai_handler_runtime_signature.py`
- Modify: `src/app/core/video/thread.py`

**Step 1: Write the failing test**

```python
def test_ai_handler_refreshes_when_gpu_memory_budget_changes() -> None:
    handler = DummyHandler({"gpu_memory_mb": 2048, ...})
    new_params = {**handler.ai_params, "gpu_memory_mb": 1024}

    assert _ai_handler_needs_refresh(handler, new_params) is True
```

**Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest -q "tests/unit/test_ai_handler_runtime_signature.py"`

Expected: FAIL，说明 refresh 仍遗漏预算字段。

**Step 3: Write minimal implementation**

```python
def _build_ai_handler_runtime_signature(ai_params: dict[str, Any]) -> dict[str, Any]:
    return {...}

def _ai_handler_needs_refresh(ai_handler, ai_params):
    return _build_ai_handler_runtime_signature(existing) != _build_ai_handler_runtime_signature(ai_params)
```

**Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest -q "tests/unit/test_ai_handler_runtime_signature.py"`

Expected: PASS，说明预算变化会触发 refresh。

### Task 3: 批处理改为按文件解析运行时配置

**Files:**
- Create: `tests/unit/test_batch_processor_file_level_runtime_config.py`
- Modify: `tests/unit/test_signal_handler_batch_manifest.py`
- Modify: `src/app/ui/signal_handler.py`
- Modify: `src/app/ui/widgets/batch/batch_processor_thread.py`

**Step 1: Write the failing test**

```python
def test_mixed_batch_uses_file_level_runtime_configs() -> None:
    queue = [{"input_path": "a.jpg"}, {"input_path": "b.mp4"}]
    ...
    assert first_file_kwargs["use_pipeline"] is False
    assert second_file_kwargs["use_pipeline"] is True
```

**Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest -q "tests/unit/test_batch_processor_file_level_runtime_config.py" "tests/unit/test_signal_handler_batch_manifest.py"`

Expected: FAIL，说明批处理仍整批共用同一份 `ai_params`。

**Step 3: Write minimal implementation**

```python
resolved = builder.build_resolved_performance_config(... input_file_path=input_path, is_batch=True)
ai_params = resolved.to_ai_params()
processor = VideoProcessorThread(... ai_params=ai_params, use_pipeline=resolved.use_pipeline, ...)
```

**Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest -q "tests/unit/test_batch_processor_file_level_runtime_config.py" "tests/unit/test_signal_handler_batch_manifest.py"`

Expected: PASS，说明混合队列已按文件级运行时配置执行并追溯。

### Task 4: 收紧流水线缓存预算公式

**Files:**
- Modify: `tests/unit/core/video/test_pipeline_cache_budget.py`
- Modify: `src/app/core/video/utils/backpressure.py`

**Step 1: Write the failing test**

```python
def test_pipeline_queue_budget_does_not_grossly_exceed_small_cache_budget() -> None:
    budget = calculate_runtime_queue_budget(True, 64, (2160, 3840))
    assert budget.approx_total_memory_mb <= 128
```

**Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest -q "tests/unit/core/video/test_pipeline_cache_budget.py"`

Expected: FAIL，说明当前 4K 小预算场景仍然严重超配。

**Step 3: Write minimal implementation**

```python
total_frame_budget = max(3, int(cache_size_mb / frame_mb))
frame_queue_size = ...
result_queue_size = ...
writer_buffer_size = ...
```

**Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest -q "tests/unit/core/video/test_pipeline_cache_budget.py"`

Expected: PASS，说明预算语义更接近 MB 上限。

### Task 5: 聚焦回归验证

**Files:**
- Test: `tests/unit/app/config/preferences/test_advanced_params_preferences.py`
- Test: `tests/unit/test_ai_handler_runtime_signature.py`
- Test: `tests/unit/test_preload_ai_params_snapshot.py`
- Test: `tests/unit/test_batch_processor_file_level_runtime_config.py`
- Test: `tests/unit/test_signal_handler_batch_manifest.py`
- Test: `tests/unit/core/video/test_pipeline_cache_budget.py`

**Step 1: Run focused regression**

Run:

```bash
./.venv/Scripts/python.exe -m pytest -q \
  "tests/unit/app/config/preferences/test_advanced_params_preferences.py" \
  "tests/unit/test_ai_handler_runtime_signature.py" \
  "tests/unit/test_preload_ai_params_snapshot.py" \
  "tests/unit/test_signal_handler_thread_mode_passthrough.py" \
  "tests/unit/test_signal_handler_batch_config_passthrough.py" \
  "tests/unit/test_batch_processor_file_level_runtime_config.py" \
  "tests/unit/test_signal_handler_batch_manifest.py" \
  "tests/unit/core/video/test_pipeline_cache_budget.py"
```

Expected: 全部 PASS。

**Step 2: Run lint/type hooks on touched files**

Run:

```bash
./.venv/Scripts/pre-commit.exe run --files \
  "src/app/config/preferences/manager.py" \
  "src/app/core/video/thread.py" \
  "src/app/ui/signal_handler.py" \
  "src/app/ui/widgets/batch/batch_processor_thread.py" \
  "src/app/core/video/utils/backpressure.py" \
  "tests/unit/app/config/preferences/test_advanced_params_preferences.py" \
  "tests/unit/test_ai_handler_runtime_signature.py" \
  "tests/unit/test_batch_processor_file_level_runtime_config.py" \
  "tests/unit/test_signal_handler_batch_manifest.py" \
  "tests/unit/core/video/test_pipeline_cache_budget.py"
```

Expected: 所有 hooks PASS。

**Step 3: Record residual risks**

```text
- cache_size_mb 仍是软预算，不保证精确约束到每个队列对象的真实进程内存占用
- 批处理 manifest 若需展示更详细的文件级 runtime_performance，可在后续独立优化导出结构
- runtime signature 仍需保持白名单策略，避免把纯 trace 字段纳入刷新判定
```
