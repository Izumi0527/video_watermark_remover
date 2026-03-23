# GPU Grouped Batch Throughput Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 `DeepLearningInpainter.inpaint_batch()` 在混合尺寸或混合 profile 的输入中，按兼容分组执行真实 GPU batch 前向，并保留逐组降级能力。

**Architecture:** 保持 `inpaint_batch()` 的外部签名和单帧语义不变，只在 `src/app/core/ai/dl_inpainter.py` 内部新增“按组分桶、逐组真实 batch、逐组回退顺序执行”的编排层。通过扩展 `tests/unit/test_dl_inpainter_batch.py`，先锁定混合批次的行为，再以最小代码实现 grouped batch 和执行模式观测。

**Tech Stack:** Python 3.9、NumPy、OpenCV、Torch 兼容桩、Pytest

---

### Task 1: 先锁定按组 batch 的失败测试

**Files:**
- Modify: `tests/unit/test_dl_inpainter_batch.py`
- Test: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 写失败测试，锁定混合尺寸按组 batch**

```python
def test_inpaint_batch_groups_compatible_items_by_inference_shape(...):
    frames = [_create_frame(64, 64), _create_frame(64, 64), _create_frame(32, 32), _create_frame(32, 32)]
    masks = [_create_mask(...), ...]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 4
    assert model.forward_call_count == 2
    assert inpainter.last_batch_execution_mode == "grouped_true_batch"
```

**Step 2: 运行测试确认先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py::test_inpaint_batch_groups_compatible_items_by_inference_shape" -q`
Expected: FAIL，因为当前实现对混合尺寸仍整批回退逐帧。

**Step 3: 写失败测试，锁定混合 profile 按组 batch**

```python
def test_inpaint_batch_groups_compatible_items_by_effective_profile(...):
    profiles = [None, None, high_profile, high_profile]
    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4, profiles=profiles)
    assert model.forward_call_count == 2
    assert inpainter.last_batch_execution_mode == "grouped_true_batch"
```

**Step 4: 写失败测试，锁定“部分分组 batch + 部分顺序”混合场景**

```python
def test_inpaint_batch_uses_mixed_mode_when_empty_mask_blocks_one_group(...):
    masks = [_create_mask(64, 64), _create_empty_mask(64, 64), _create_mask(64, 64)]
    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)
    assert model.forward_call_count == 1
    assert inpainter.last_batch_execution_mode == "mixed_grouped_batch"
```

**Step 5: 跑整份 batch 单测确认新场景都先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: 新增 grouped batch 相关用例失败，其余旧用例维持现状。

### Task 2: 在 GPU 内核里加入按组 batch 编排

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Test: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 给内部 batch item 增加索引信息**

```python
@dataclass
class PreparedBatchItem:
    index: int
    ...
```

**Step 2: 增加按组 key 与分组助手**

```python
def _get_batch_group_key(self, item: PreparedBatchItem) -> Optional[tuple]:
    ...

def _group_batch_items(self, batch_items: list[PreparedBatchItem]) -> list[list[PreparedBatchItem]]:
    ...
```

**Step 3: 用最小代码改写 `inpaint_batch()` 的调度**

```python
def inpaint_batch(...):
    batch_items = self._prepare_batch_items(...)
    results = [None] * len(batch_items)
    used_true_batch = False
    used_sequential = False

    for group in self._group_batch_items(batch_items):
        if len(group) >= 2:
            try:
                grouped_results = self._run_true_batch(group)
                used_true_batch = True
            except Exception:
                grouped_results = self._run_group_sequential(...)
                used_sequential = True
        else:
            grouped_results = self._run_group_sequential(...)
            used_sequential = True
```

**Step 4: 收口执行模式**

```python
def _resolve_batch_execution_mode(...):
    if used_true_batch and used_sequential:
        return "mixed_grouped_batch"
    if used_true_batch:
        return "grouped_true_batch"
    return "fallback_sequential"
```

**Step 5: 跑 batch 单测确认转绿**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: PASS

### Task 3: 补逐组回退与顺序保持验证

**Files:**
- Modify: `tests/unit/test_dl_inpainter_batch.py`
- Test: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 写失败测试，锁定“某一组 batch 失败，只回退该组”**

```python
def test_inpaint_batch_falls_back_only_for_failed_group(...):
    results = inpainter.inpaint_batch(...)
    assert model.forward_call_count == 4
    assert inpainter.last_batch_execution_mode == "mixed_grouped_batch"
```

**Step 2: 若需要，补最小实现以支持逐组回退**

```python
def _run_group_sequential(...):
    ...
```

**Step 3: 跑 batch 单测确认所有 grouped 场景通过**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: PASS

### Task 4: 更新文档并做定向回归

**Files:**
- Modify: `docs/inpainting_parameter_fix_record.md`
- Modify: `docs/plans/2026-03-23-gpu-grouped-batch-throughput.md`
- Test: `tests/unit/test_dl_inpainter_batch.py`
- Test: `tests/unit/test_dl_inpainter_profile.py`
- Test: `tests/unit/test_dynamic_watermark_tracking.py`
- Test: `tests/integration/test_dl_inpainter_gpu.py`

**Step 1: 更新文档说明 grouped batch 边界**

```text
- 同 profile 且同实际推理输入尺寸的样本会按组走真实 batch
- 不兼容组只对该组顺序执行，不再整批退化
- 某一组 batch 前向失败时，只回退该组
```

**Step 2: 跑定向回归**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dynamic_watermark_tracking.py" "tests/integration/test_dl_inpainter_gpu.py" -q`
Expected: PASS

**Step 3: 跑 pre-commit 级别检查**

Run: `./.venv/Scripts/pre-commit.exe run --files "src/app/core/ai/dl_inpainter.py" "tests/unit/test_dl_inpainter_batch.py" "docs/inpainting_parameter_fix_record.md" "docs/plans/2026-03-23-gpu-grouped-batch-throughput.md"`
Expected: 全部 Passed

**Step 4: 提交本阶段改动**

```bash
git add src/app/core/ai/dl_inpainter.py tests/unit/test_dl_inpainter_batch.py docs/inpainting_parameter_fix_record.md docs/plans/2026-03-23-gpu-grouped-batch-throughput.md
git commit -m "feat(core-ai): 支持GPU按组批量推理" -m "<详细正文>"
```
