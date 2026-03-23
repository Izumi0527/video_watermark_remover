# GPU OOM Retry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `DeepLearningInpainter` 增加仅针对 GPU OOM 类失败的一次性更保守 profile 自动重试，并把最小重试观测透传到 `AIHandler.processing_info`。

**Architecture:** 单帧路径抽出“按指定 profile 执行一次完整 GPU 修复”的内部 helper，保证 OOM 重试能真正重建 mask、缩放结果和 tensor；grouped batch 在组级调度层追加一次 OOM 重试，不影响已成功组。`AIHandler` 只补最小观测字段透传，不修改外部接口。

**Tech Stack:** Python 3.9、NumPy、OpenCV、Torch 兼容桩、Pytest

---

### Task 1: 先锁定 OOM 重试的失败测试

**Files:**
- Modify: `tests/unit/test_dl_inpainter_profile.py`
- Modify: `tests/unit/test_dl_inpainter_batch.py`
- Modify: `tests/unit/test_dynamic_watermark_tracking.py`

**Step 1: 写失败测试，锁定更保守 retry profile 的收紧行为**

```python
def test_build_oom_retry_profile_reduces_resize_limit_and_blend_ratio():
    retry_profile = inpainter._build_oom_retry_profile(original_profile)
    assert retry_profile.resize_limit < original_profile.resize_limit
    assert retry_profile.blend_ratio <= original_profile.blend_ratio
```

**Step 2: 跑测试确认先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py::test_build_oom_retry_profile_reduces_resize_limit_and_blend_ratio" -q`
Expected: FAIL，因为 helper 还不存在。

**Step 3: 写失败测试，锁定单帧 OOM 会重试一次**

```python
def test_inpaint_frame_retries_once_with_conservative_profile_on_oom(...):
    result = inpainter.inpaint_frame(frame, mask, radius=6, quality_level=5)
    assert model.forward_call_count == 2
    assert inpainter.last_oom_retry_used is True
    assert inpainter.last_oom_retry_count == 1
```

**Step 4: 写失败测试，锁定非 OOM 不重试**

```python
def test_inpaint_frame_does_not_retry_non_oom_error(...):
    with pytest.raises(dl_module.InpaintingError):
        inpainter.inpaint_frame(frame, mask, radius=6, quality_level=5)
    assert model.forward_call_count == 1
```

**Step 5: 写失败测试，锁定 grouped batch 只重试失败组**

```python
def test_inpaint_batch_retries_only_failed_group_on_oom(...):
    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=5)
    assert inpainter.last_batch_execution_mode == "mixed_grouped_batch"
    assert inpainter.last_oom_retry_used is True
```

**Step 6: 写失败测试，锁定 AIHandler 透传重试观测**

```python
def test_ai_handler_reports_gpu_oom_retry_info(...):
    _, info = handler.process_frame(frame, user_input)
    assert info["gpu_inpainting_oom_retry_used"] is True
    assert info["gpu_inpainting_retry_count"] == 1
```

**Step 7: 跑相关测试确认新增场景先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" "tests/unit/test_dynamic_watermark_tracking.py" -q`
Expected: 新增 OOM 重试相关用例失败，其余现有用例维持通过。

### Task 2: 在 `DeepLearningInpainter` 内实现单帧 OOM 重试

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Test: `tests/unit/test_dl_inpainter_profile.py`

**Step 1: 新增最小重试状态字段**

```python
self.last_oom_retry_used: bool = False
self.last_oom_retry_count: int = 0
self.last_retry_profile_used: Optional[Dict[str, Union[int, float]]] = None
```

**Step 2: 新增 OOM 判定与更保守 profile helper**

```python
def _is_gpu_oom_error(self, exc: Exception) -> bool:
    ...

def _build_oom_retry_profile(self, profile: GPUInpaintingProfile) -> GPUInpaintingProfile:
    ...
```

**Step 3: 抽出单次执行 helper**

```python
def _run_single_inpainting_attempt(...):
    ...
```

**Step 4: 用最小代码改写 `inpaint_frame()`**

```python
try:
    return self._run_single_inpainting_attempt(...)
except Exception as exc:
    if not self._is_gpu_oom_error(exc):
        raise
    retry_profile = self._build_oom_retry_profile(active_profile)
    return self._run_single_inpainting_attempt(..., profile=retry_profile)
```

**Step 5: 跑 profile 与单帧相关测试确认转绿**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" -q`
Expected: PASS

### Task 3: 在 grouped batch 路径加入组级 OOM 重试

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Modify: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 新增“按指定 profile 重建 batch items”的 helper**

```python
def _clone_batch_items_with_profile(self, batch_items, profile):
    ...
```

**Step 2: 在 `_execute_batch_group()` 中加入组级 OOM 重试**

```python
try:
    return self._run_true_batch(batch_items), True
except Exception as exc:
    if self._is_gpu_oom_error(exc):
        retry_items = self._rebuild_group_with_retry_profile(batch_items)
        return self._run_true_batch(retry_items), True
```

**Step 3: 若重试仍失败，则只回退该组顺序执行**

```python
return self._run_group_sequential(batch_items, ...), False
```

**Step 4: 跑 batch 单测确认 grouped OOM 场景转绿**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: PASS

### Task 4: 透传最小观测并更新文档

**Files:**
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `tests/unit/test_dynamic_watermark_tracking.py`
- Modify: `docs/inpainting_parameter_fix_record.md`
- Modify: `docs/plans/2026-03-23-gpu-oom-retry-design.md`
- Modify: `docs/plans/2026-03-23-gpu-oom-retry.md`

**Step 1: 在 `AIHandler` 里透传 retry 观测**

```python
processing_info["gpu_inpainting_oom_retry_used"] = ...
processing_info["gpu_inpainting_retry_count"] = ...
processing_info["gpu_inpainting_retry_profile"] = ...
```

**Step 2: 更新文档说明本阶段边界**

```text
- 仅 OOM 类错误才会触发一次更保守 profile 重试
- 最终 `gpu_inpainting_profile` 代表最终成功 profile
- `gpu_inpainting_oom_retry_used / retry_count / retry_profile` 记录本次是否发生过重试
```

**Step 3: 跑定向回归**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" "tests/unit/test_dynamic_watermark_tracking.py" "tests/integration/test_dl_inpainter_gpu.py" -q`
Expected: PASS

**Step 4: 跑 pre-commit 级别检查**

Run: `./.venv/Scripts/pre-commit.exe run --files "src/app/core/ai/dl_inpainter.py" "src/app/core/ai/ai_handler.py" "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" "tests/unit/test_dynamic_watermark_tracking.py" "docs/inpainting_parameter_fix_record.md" "docs/plans/2026-03-23-gpu-oom-retry-design.md" "docs/plans/2026-03-23-gpu-oom-retry.md"`
Expected: 全部 Passed

**Step 5: 提交本阶段改动**

```bash
git add src/app/core/ai/dl_inpainter.py src/app/core/ai/ai_handler.py tests/unit/test_dl_inpainter_profile.py tests/unit/test_dl_inpainter_batch.py tests/unit/test_dynamic_watermark_tracking.py docs/inpainting_parameter_fix_record.md docs/plans/2026-03-23-gpu-oom-retry-design.md docs/plans/2026-03-23-gpu-oom-retry.md
git commit -m "feat(core-ai): 增加GPU OOM 降级重试" -m "<详细正文>"
```
