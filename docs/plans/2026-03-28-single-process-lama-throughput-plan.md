# Single-Process LaMa Throughput Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在保持 GPU 深度修复串行护栏不变的前提下，提升单进程 LaMa 路径的吞吐，并降低整帧后处理与整帧复制开销。

**Architecture:** 通过在 AI 层新增“批量检测 + 逐帧修复”的共享入口，让单进程视频模式只负责读取、写出、进度和状态；同时把后处理收敛到 ROI 子区域，并减少无意义的整帧复制。整个改造以 TDD 渐进实施，每一步都保留稳定降级路径。

**Tech Stack:** Python 3.12、OpenCV、NumPy、PyTorch、pytest

---

### Task 1: 为单进程批量检测补失败测试

**Files:**
- Modify: `tests/unit/core/video/test_single_process_runtime_observability.py`
- Create: `tests/unit/core/video/test_single_process_batch_detection.py`
- Modify: `src/app/core/video/modes/single_process.py`
- Modify: `src/app/core/ai/ai_handler.py`

**Step 1: Write the failing test**

补一个单进程自动检测回归测试，断言：

- 自动检测模式下，`single_process.py` 会优先调用 AI 层的批处理入口
- 写出帧顺序与输入顺序一致
- 不会退回成每帧单独调用 `process_frame()`

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/video/test_single_process_batch_detection.py -v`
Expected: FAIL，表现为当前实现没有批处理入口或仍然逐帧调用。

**Step 3: Write minimal implementation**

实现最小批处理通路：

- 在 `AIHandler` 中新增 `process_frames_batch()`
- 在 `single_process.py` 中引入小批量读帧与批量处理分支
- 对手动掩码或检测器不可用场景保留逐帧回退

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/video/test_single_process_batch_detection.py -v`
Expected: PASS

**Step 5: Commit**

本轮先不单独提交，待后续任务完成后一并验证。

### Task 2: 为 ROI 后处理补失败测试

**Files:**
- Create: `tests/unit/test_image_postprocess_roi.py`
- Modify: `src/app/core/ai/image_processor.py`
- Modify: `src/app/core/ai/ai_handler.py`

**Step 1: Write the failing test**

补两个测试：

- 小掩码场景下，局部后处理只处理 ROI，而不是把整帧交给后处理子步骤
- 大掩码或异常场景下，会安全回退到整帧后处理

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_image_postprocess_roi.py -v`
Expected: FAIL，表现为当前 `apply_postprocessing()` 仍对整帧执行。

**Step 3: Write minimal implementation**

在 `image_processor.py` 中新增 ROI 计算与局部写回逻辑，并让 `AIHandler` 调用该逻辑。

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_image_postprocess_roi.py -v`
Expected: PASS

**Step 5: Commit**

本轮先不单独提交，继续累积到最终验证。

### Task 3: 为复制优化补失败测试

**Files:**
- Create: `tests/unit/test_ai_handler_copy_optimization.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `src/app/core/ai/inpainting_backends/lama_backend.py`

**Step 1: Write the failing test**

补三个行为测试：

- 未启用后处理时，不创建 `original_frame` 的整帧副本
- 无水印路径不再做额外 `frame.copy()`
- LaMa ROI 写回不会修改 mask 外区域

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_ai_handler_copy_optimization.py tests/unit/test_lama_backend_roi_inpainting.py -v`
Expected: FAIL，表现为当前实现仍会创建额外整帧副本。

**Step 3: Write minimal implementation**

在 `AIHandler` 中引入 lazy copy 和 no-watermark fast path；必要时收敛 `lama_backend.py` 的写回复制点。

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_ai_handler_copy_optimization.py tests/unit/test_lama_backend_roi_inpainting.py -v`
Expected: PASS

**Step 5: Commit**

本轮先不单独提交，待整轮验证通过后统一提交。

### Task 4: 回归与文档校验

**Files:**
- Modify: `docs/plans/2026-03-28-single-process-lama-throughput-design.md`
- Modify: `docs/plans/2026-03-28-single-process-lama-throughput-plan.md`
- Verify: `tests/unit/core/video/test_single_process_runtime_observability.py`
- Verify: `tests/unit/test_dynamic_watermark_tracking.py`
- Verify: `tests/unit/test_ai_handler_gpu_runtime_fallback.py`

**Step 1: Run focused regression**

Run:

```bash
pytest tests/unit/core/video/test_single_process_batch_detection.py -v
pytest tests/unit/test_image_postprocess_roi.py -v
pytest tests/unit/test_ai_handler_copy_optimization.py -v
pytest tests/unit/core/video/test_single_process_runtime_observability.py -v
pytest tests/unit/test_dynamic_watermark_tracking.py -v
pytest tests/unit/test_ai_handler_gpu_runtime_fallback.py -v
pytest tests/unit/test_lama_backend_roi_inpainting.py -v
```

Expected: 全部 PASS，且无新的告警或异常栈。

**Step 2: 修正文档**

若最终实现与原设计有轻微偏差，同步更新设计与计划文档，保持文档和代码一致。

**Step 3: 整理提交**

统一整理代码、测试、文档改动，准备中文主题 + 详细正文提交信息。

**Step 4: 最终校验**

Run: `git status --short`
Expected: 仅保留本轮预期改动文件。

**Step 5: Commit**

待用户确认需要提交时，按项目规范统一提交。
