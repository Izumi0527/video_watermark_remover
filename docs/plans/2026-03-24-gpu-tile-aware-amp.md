# GPU Tile-Aware Batch And Mixed Precision Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `DeepLearningInpainter` 同阶段补齐 `tile_aware_true_batch` 与最小 mixed precision 统一前向包装，在不改变现有 profile 语义的前提下提升大图组吞吐并缓解显存压力。

**Architecture:** grouped batch 分组逻辑保持不变，只在组内新增 `tile_aware_true_batch` 执行模式；mixed precision 只作为统一前向包装层，复用于单帧、顺序 tile、普通 true batch 与 tile-aware true batch。失败顺序固定为“AMP 降回 FP32”优先于“profile 保守重试”。

**Tech Stack:** Python 3.9、NumPy、OpenCV、Torch、Pytest、pre-commit

---

### Task 1: 先锁定 tile-aware batch 与 AMP 的失败测试

**Files:**
- Modify: `tests/unit/test_dl_inpainter_batch.py`
- Modify: `tests/unit/test_dl_inpainter_profile.py`

**Step 1: 写失败测试，锁定组内 tile plan 一致时会走 `tile_aware_true_batch`**

```python
def test_inpaint_batch_uses_tile_aware_true_batch_when_tile_plan_matches(...):
    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=5)
    assert inpainter.last_batch_execution_mode == "tile_aware_true_batch"
    assert model.forward_call_count < sequential_tile_call_count
```

**Step 2: 跑测试确认先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py::test_inpaint_batch_uses_tile_aware_true_batch_when_tile_plan_matches" -q`
Expected: FAIL，因为 tile-aware batch helper 还不存在。

**Step 3: 写失败测试，锁定 tile plan 不一致时会回退**

```python
def test_inpaint_batch_falls_back_when_tile_plan_differs(...):
    assert inpainter.last_batch_execution_mode == "fallback_sequential"
```

**Step 4: 写失败测试，锁定 mixed precision 前向包装会被多条路径复用**

```python
def test_forward_paths_share_precision_wrapper(...):
    assert precision_wrapper_calls == ["single", "true_batch", "tile_aware_batch"]
```

**Step 5: 写失败测试，锁定 AMP 失败会先降到 FP32**

```python
def test_mixed_precision_falls_back_to_fp32_before_profile_retry(...):
    assert forward_attempts == ["amp", "fp32"]
    assert inpainter.last_retry_info is None
```

**Step 6: 写失败测试，锁定 AMP + tile-aware batch 下 OOM 仍只算一次整帧级 retry**

```python
def test_tile_aware_batch_keeps_single_oom_retry_semantics(...):
    assert inpainter.last_retry_info == {"applied": True, "count": 1, "reason": "oom"}
```

**Step 7: 跑相关测试确认新增场景先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: 新增 tile-aware batch / AMP 场景失败，其余现有用例维持通过。

### Task 2: 新增 tile-aware batch 决策与执行 helper

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Test: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 新增 tile plan 解析 helper**

```python
def _resolve_tile_plan_for_item(self, item: PreparedBatchItem) -> TilePlan:
    ...
```

**Step 2: 新增 tile-aware batch 资格判定 helper**

```python
def _can_use_tile_aware_true_batch(self, batch_items, tile_plans) -> bool:
    ...
```

**Step 3: 新增 tile-aware batch 主执行 helper**

```python
def _run_tile_aware_true_batch(self, batch_items, tile_plan) -> list[np.ndarray]:
    ...
```

**Step 4: 在 `_execute_batch_group()` 中接入组内三态执行**

```python
if self._can_use_true_batch(batch_items):
    ...
elif self._can_use_tile_aware_true_batch(batch_items, tile_plans):
    ...
else:
    ...
```

**Step 5: 跑 batch 单测确认 tile-aware batch 场景转绿**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: PASS

### Task 3: 接入最小 mixed precision 统一前向包装

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Test: `tests/unit/test_dl_inpainter_profile.py`
- Test: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 新增 precision policy helper**

```python
def _resolve_precision_policy(self, prefer_mixed_precision: bool = True) -> bool:
    ...
```

**Step 2: 新增统一前向包装 helper**

```python
def _run_forward_with_precision(self, input_tensor, prefer_mixed_precision: bool = True):
    ...
```

**Step 3: 让单帧、顺序 tile、普通 true batch、tile-aware true batch 复用该 helper**

```python
output_tensor = self._run_forward_with_precision(batch_tensor, prefer_mixed_precision=True)
```

**Step 4: 跑 profile + batch 单测确认 AMP fallback 场景转绿**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: PASS

### Task 4: 固化 AMP / OOM / 顺序回退的优先级

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Modify: `tests/unit/test_dl_inpainter_profile.py`
- Modify: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 固化“AMP 降回 FP32”优先于“profile 保守重试”**

```python
try:
    return self._run_forward_with_precision(...)
except PrecisionFallbackError:
    ...
except OOMError:
    ...
```

**Step 2: 固化 tile-aware batch 内部校验失败直接回退顺序，不记 retry**

```python
if not self._can_use_tile_aware_true_batch(...):
    return self._run_group_sequential(...)
```

**Step 3: 跑定向回归**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" "tests/unit/test_dynamic_watermark_tracking.py" -q`
Expected: PASS

### Task 5: 更新文档并做静态检查

**Files:**
- Modify: `docs/inpainting_parameter_fix_record.md`
- Create: `docs/plans/2026-03-24-gpu-tile-aware-amp-design.md`
- Create: `docs/plans/2026-03-24-gpu-tile-aware-amp.md`

**Step 1: 更新阶段记录文档**

```text
- grouped batch 已支持 tile-aware true batch
- mixed precision 已接入统一前向包装
- 当前仍未支持 second pass 与更复杂精度档位
```

**Step 2: 跑 pre-commit**

Run: `./.venv/Scripts/pre-commit.exe run --files "src/app/core/ai/dl_inpainter.py" "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" "docs/inpainting_parameter_fix_record.md" "docs/plans/2026-03-24-gpu-tile-aware-amp-design.md" "docs/plans/2026-03-24-gpu-tile-aware-amp.md"`
Expected: 全部 Passed

**Step 3: 计划提交**

```bash
git add src/app/core/ai/dl_inpainter.py tests/unit/test_dl_inpainter_profile.py tests/unit/test_dl_inpainter_batch.py docs/inpainting_parameter_fix_record.md docs/plans/2026-03-24-gpu-tile-aware-amp-design.md docs/plans/2026-03-24-gpu-tile-aware-amp.md
git commit -m "feat(core-ai): 支持tile-aware批量推理与混合精度" -m "<详细正文>"
```
