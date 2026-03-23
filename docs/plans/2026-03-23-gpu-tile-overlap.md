# GPU Tile Overlap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `DeepLearningInpainter` 增加最小可落地的 GPU `tile / overlap` 推理能力，并确保 grouped batch 在大图组上稳定回退而不破坏现有 profile 与重试语义。

**Architecture:** tile 只作为 `DeepLearningInpainter` 内部执行策略接入 `_run_single_inference()`；真正的模型前向提取为共享 helper，统一处理模型步幅对齐；grouped batch 继续按“同生效 profile + 同推理尺寸”分组，但对需要 tile 的组直接走顺序路径。

**Tech Stack:** Python 3.9、NumPy、OpenCV、Torch 兼容桩、Pytest

---

### Task 1: 先锁定 tile / overlap 的失败测试

**Files:**
- Modify: `tests/unit/test_dl_inpainter_profile.py`
- Modify: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 写失败测试，锁定单帧 tile 路径会走 tiled helper**

```python
def test_inpaint_frame_uses_tiled_path_when_inference_shape_requires_it(...):
    result = inpainter.inpaint_frame(frame, mask, radius=3, quality_level=5)
    assert result.shape == frame.shape
    assert tiled_call_count == 1
    assert inpainter.last_profile_used == expected_profile.to_dict()
```

**Step 2: 跑单测确认先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py::test_inpaint_frame_uses_tiled_path_when_inference_shape_requires_it" -q`
Expected: FAIL，因为 tile helper 还不存在。

**Step 3: 写失败测试，锁定 tile 路径下 OOM 仍只做一次整帧级重试**

```python
def test_inpaint_frame_tiled_path_keeps_single_oom_retry_semantics(...):
    assert inpainter.last_retry_info == {"applied": True, "count": 1, "reason": "oom"}
```

**Step 4: 写失败测试，锁定需要 tile 的组不会进入 true batch**

```python
def test_inpaint_batch_skips_true_batch_for_group_requiring_tile(...):
    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=5)
    assert true_batch_call_count == 0
    assert inpainter.last_batch_execution_mode == "fallback_sequential"
```

**Step 5: 写失败测试，锁定 mixed case 的分组行为**

```python
def test_inpaint_batch_uses_mixed_mode_when_large_group_requires_tile(...):
    assert inpainter.last_batch_execution_mode == "mixed_grouped_batch"
```

**Step 6: 跑相关测试确认新增场景先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: 新增 tile / overlap 场景失败，其余现有用例维持通过。

### Task 2: 在单帧路径实现最小 tile / overlap

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Test: `tests/unit/test_dl_inpainter_profile.py`

**Step 1: 新增内部 tile 判定与 tile 计划 helper**

```python
def _should_use_tiled_inference(self, inference_shape, profile):
    ...

def _build_tile_regions(self, image_shape, tile_size, overlap):
    ...
```

**Step 2: 抽出共享模型前向 helper**

```python
def _run_model_forward(self, frame_rgb, mask):
    ...
```

**Step 3: 新增 overlap 融合 helper**

```python
def _run_tiled_model_forward(self, inference_frame_rgb, inference_mask, profile):
    ...
```

**Step 4: 用最小代码改写 `_run_single_inference()`**

```python
if self._should_use_tiled_inference(inference_frame_rgb.shape, profile):
    output_tensor = self._run_tiled_model_forward(...)
else:
    output_tensor = self._run_model_forward(...)
```

**Step 5: 跑 profile 相关测试确认转绿**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" -q`
Expected: PASS

### Task 3: 让 grouped batch 正确绕开 tile 组

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Modify: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 新增“样本是否需要 tile”判定 helper**

```python
def _requires_tiled_execution(self, item):
    ...
```

**Step 2: 在 `_can_use_true_batch()` 中排除需要 tile 的样本**

```python
if self._requires_tiled_execution(item):
    return False
```

**Step 3: 跑 batch 单测确认 grouped 行为转绿**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: PASS

### Task 4: 更新阶段记录并做定向回归

**Files:**
- Modify: `docs/inpainting_parameter_fix_record.md`
- Modify: `docs/plans/2026-03-23-gpu-tile-overlap-design.md`
- Modify: `docs/plans/2026-03-23-gpu-tile-overlap.md`

**Step 1: 在阶段记录文档补充 tile / overlap 已落地边界**

```text
- tile / overlap 当前只影响 DeepLearningInpainter 内部推理
- 需要 tile 的组当前会回退到顺序执行，不代表 tile-aware true batch 已完成
- `gpu_inpainting_profile` 仍只记录最终成功那次真正生效的 profile
```

**Step 2: 跑定向回归**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" -q`
Expected: PASS

**Step 3: 跑格式与静态检查**

Run: `./.venv/Scripts/pre-commit.exe run --files "src/app/core/ai/dl_inpainter.py" "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_dl_inpainter_batch.py" "docs/inpainting_parameter_fix_record.md" "docs/plans/2026-03-23-gpu-tile-overlap-design.md" "docs/plans/2026-03-23-gpu-tile-overlap.md"`
Expected: 全部 Passed
