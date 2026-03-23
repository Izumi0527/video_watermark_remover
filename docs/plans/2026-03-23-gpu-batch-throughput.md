# GPU Batch 吞吐优化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 `DeepLearningInpainter.inpaint_batch()` 在同尺寸且同 profile 的批次上执行真实 GPU batch 前向，不满足条件时整批回退到稳定的逐帧模式。

**Architecture:** 保持 `inpaint_batch()` 外部接口不变，只在 `src/app/core/ai/dl_inpainter.py` 内部增加批次预检查、真实 batch 前向和整批回退逻辑。通过新增 batch 专项单测，验证“真实只做一次前向”“不齐整批次整批回退”“异常时仍可回退”这三类关键行为。

**Tech Stack:** Python 3.12、NumPy、OpenCV、PyTorch、pytest

---

### Task 1: 建立真实 batch 的失败测试

**Files:**
- Create: `tests/unit/test_dl_inpainter_batch.py`
- Modify: `src/app/core/ai/dl_inpainter.py`
- Test: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 写失败测试，锁定真实 batch 命中条件**

```python
def test_inpaint_batch_uses_single_model_forward_for_same_shape_and_profile():
    model = _CountingModel()
    inpainter = _build_inpainter_with_model(model)

    frames = [_create_frame(64, 64), _create_frame(64, 64)]
    masks = [_create_mask(64, 64), _create_mask(64, 64)]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 2
    assert model.forward_call_count == 1
    assert inpainter.last_batch_execution_mode == "true_batch"
```

**Step 2: 跑测试，确认当前确实失败**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py::test_inpaint_batch_uses_single_model_forward_for_same_shape_and_profile" -q`

Expected:
- FAIL
- 当前大概率表现为前向次数不是 `1`
- 或 `last_batch_execution_mode` 尚不存在

**Step 3: 再补两个失败测试，锁定回退条件**

```python
def test_inpaint_batch_falls_back_when_input_shapes_differ():
    ...
    assert model.forward_call_count == 2
    assert inpainter.last_batch_execution_mode == "fallback_sequential"


def test_inpaint_batch_falls_back_when_profiles_differ():
    ...
    assert model.forward_call_count == 2
    assert inpainter.last_batch_execution_mode == "fallback_sequential"
```

**Step 4: 跑这 3 个测试，确认全部先红**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`

Expected:
- 至少 3 个 FAIL

**Step 5: Commit**

```bash
git add tests/unit/test_dl_inpainter_batch.py
git commit -m "test(ai): 增加GPU批量推理失败测试"
```

---

### Task 2: 在 GPU 内核里加入批次预检查和真实 batch 前向

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Test: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 新增内部批次数据结构和执行模式状态**

```python
@dataclass
class PreparedBatchItem:
    original_rgb: np.ndarray
    prepared_mask: np.ndarray
    profile: GPUInpaintingProfile
    inference_frame_rgb: np.ndarray
    inference_mask: np.ndarray
    original_shape: tuple[int, ...]
    inference_shape: tuple[int, ...]


self.last_batch_execution_mode: Optional[str] = None
```

**Step 2: 新增批次预处理与资格判断辅助方法**

```python
def _prepare_batch_items(...):
    ...

def _can_use_true_batch(items: list[PreparedBatchItem]) -> bool:
    ...

def _run_true_batch(items: list[PreparedBatchItem]) -> list[np.ndarray]:
    ...
```

**Step 3: 用最小代码改写 `inpaint_batch()`**

```python
def inpaint_batch(...):
    items = self._prepare_batch_items(...)
    if self._can_use_true_batch(items):
        self.last_batch_execution_mode = "true_batch"
        return self._run_true_batch(items)

    self.last_batch_execution_mode = "fallback_sequential"
    return [
        self.inpaint_frame(...)
        for ...
    ]
```

**Step 4: 跑 batch 单测，确认转绿**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/app/core/ai/dl_inpainter.py tests/unit/test_dl_inpainter_batch.py
git commit -m "feat(ai): 支持同profile批次真实GPU前向"
```

---

### Task 3: 补异常回退与结果尺寸保护

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Modify: `tests/unit/test_dl_inpainter_batch.py`
- Test: `tests/unit/test_dl_inpainter_batch.py`

**Step 1: 写失败测试，锁定异常回退行为**

```python
def test_inpaint_batch_falls_back_when_true_batch_forward_raises():
    model = _FailingBatchModel()
    inpainter = _build_inpainter_with_model(model)

    frames = [_create_frame(64, 64), _create_frame(64, 64)]
    masks = [_create_mask(64, 64), _create_mask(64, 64)]

    results = inpainter.inpaint_batch(frames, masks, radius=3, quality_level=4)

    assert len(results) == 2
    assert inpainter.last_batch_execution_mode == "fallback_sequential"
```

**Step 2: 写失败测试，锁定输出尺寸不变**

```python
def test_inpaint_batch_keeps_original_output_shapes_after_true_batch():
    ...
    assert results[0].shape == frames[0].shape
    assert results[1].shape == frames[1].shape
```

**Step 3: 在实现里补 try/except 和尺寸恢复**

```python
try:
    return self._run_true_batch(items)
except Exception:
    self.last_batch_execution_mode = "fallback_sequential"
    return [self.inpaint_frame(...) for ...]
```

**Step 4: 跑 batch 单测，确认所有场景通过**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" -q`

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/app/core/ai/dl_inpainter.py tests/unit/test_dl_inpainter_batch.py
git commit -m "fix(ai): 增强GPU批量推理回退稳定性"
```

---

### Task 4: 跑 GPU profile 与主链路回归

**Files:**
- Modify: `docs/inpainting_parameter_fix_record.md`
- Test: `tests/unit/test_dl_inpainter_profile.py`
- Test: `tests/unit/test_dynamic_watermark_tracking.py`
- Test: `tests/integration/test_dl_inpainter_gpu.py`

**Step 1: 跑定向单测**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dl_inpainter_batch.py" "tests/unit/test_dl_inpainter_profile.py" -q`

Expected:
- PASS

**Step 2: 跑 AI 主链路回归**

Run: `./.venv/Scripts/python.exe -m pytest "tests/unit/test_dynamic_watermark_tracking.py" "tests/unit/test_image_inpainter.py" "tests/unit/test_yolo_detector_mask_refinement.py" "tests/unit/core/ai/video/test_video_module_split.py" "tests/integration/ai/test_ai_processing.py" -q`

Expected:
- PASS

**Step 3: 跑 GPU 批处理集成测试**

Run: `./.venv/Scripts/python.exe -m pytest "tests/integration/test_dl_inpainter_gpu.py" -q`

Expected:
- PASS
- 若环境无 GPU，可接受 SKIP，但不能报新增失败

**Step 4: 更新文档说明本轮 batch 优化边界**

```markdown
- 同尺寸 + 同 profile 时走真实 GPU batch 前向
- 不满足条件时整批回退逐帧
- 暂不支持按组 batch / tile / overlap
```

**Step 5: Commit**

```bash
git add docs/inpainting_parameter_fix_record.md tests/unit/test_dl_inpainter_batch.py src/app/core/ai/dl_inpainter.py
git commit -m "docs(ai): 补充GPU批量推理优化边界"
```

---

### Task 5: 最终核对与交付

**Files:**
- Modify: `docs/plans/2026-03-23-gpu-batch-throughput-design.md`
- Modify: `docs/plans/2026-03-23-gpu-batch-throughput.md`

**Step 1: 逐条核对验收标准**

检查：
- 同尺寸 + 同 profile 是否只做一次前向
- 不齐整批次是否整批回退
- 输出尺寸是否正确
- 异常是否能整批回退
- 回归测试是否通过

**Step 2: 保存最终执行证据**

记录：
- 关键测试命令
- 实际通过结果
- 若有 SKIP，写明原因

**Step 3: 若发现偏差，回到对应任务补修**

```text
不要带着已知偏差进入交付说明
```

**Step 4: 输出最终总结**

```text
说明已实现边界、未实现边界、验证结果、后续建议
```

**Step 5: Commit**

```bash
git add docs/plans/2026-03-23-gpu-batch-throughput-design.md docs/plans/2026-03-23-gpu-batch-throughput.md
git commit -m "docs(ai): 增加GPU批量推理设计与实施计划"
```
