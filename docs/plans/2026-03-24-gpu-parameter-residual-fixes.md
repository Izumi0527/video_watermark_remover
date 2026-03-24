# GPU 参数残余风险修复 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 GPU 参数链路中的兼容误映射、运行期异常不降级和质量等级追溯失真问题，并补齐回归测试。

**Architecture:** 保持现有 `AdvancedParametersWidget -> AIParamsBuilder -> AIHandler -> processing_info -> batch manifest` 主链路不变，只在参数归一化、GPU 局部降级和追溯字段补充三个位置做最小改动。所有变更先用失败测试锁定，再补最小实现，最后做定向回归验证。

**Tech Stack:** Python 3.12、PyQt6、pytest

---

### Task 1: 修复 inpainting_method 兼容映射

**Files:**
- Modify: `src/app/ui/utils/ai_params_builder.py`
- Modify: `src/app/config/validators.py`
- Create: `tests/unit/test_ai_params_builder_inpainting_compatibility.py`

**Step 1: Write the failing tests**

新增兼容映射测试，至少覆盖：

- `ns` / `navier_stokes` 能映射到 `navier_stokes`
- `custom` 能映射到 `custom_interpolation`
- `gpu_dl` / `unet` 能映射到 `gpu_dl`
- 未知值会安全回退到 `auto`，且不会误启用 `use_gpu_inpainting`

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/unit/test_ai_params_builder_inpainting_compatibility.py`

Expected: 失败，暴露当前未知值默认 `gpu_dl` 的问题。

**Step 3: Write minimal implementation**

- 扩展 `_map_inpainting_method()` 的兼容别名表。
- 将未知值回退到 `auto`。
- 扩展验证器允许的 `inpainting_algorithm` 值，补上 `auto`。

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/unit/test_ai_params_builder_inpainting_compatibility.py`

Expected: 全部通过。

### Task 2: 修复 GPU 运行期异常降级与有效质量等级追溯

**Files:**
- Modify: `src/app/core/ai/ai_handler.py`
- Create: `tests/unit/test_ai_handler_gpu_runtime_fallback.py`
- Create: `tests/unit/test_processing_info_quality_trace.py`

**Step 1: Write the failing tests**

新增 2 个测试：

- GPU 路径运行期抛异常时，当前帧会降级到 OpenCV，并记录明确降级原因。
- `processing_info` 同时包含兼容字段 `quality_level`、显式请求字段 `requested_quality_level` 和实际值 `effective_quality_level`，且后者优先来自底层真实生效值。

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/unit/test_ai_handler_gpu_runtime_fallback.py`

Expected: 失败，暴露当前 GPU 异常直接返回原帧和缺少 `effective_quality_level` 的问题。

**Step 3: Write minimal implementation**

- 在 `inpaint_frame()` 中把 GPU 分支异常局部拦截，失败后继续走 OpenCV。
- 增加运行期降级原因记录。
- 增加 `effective_quality_level` 计算与写入。

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/unit/test_ai_handler_gpu_runtime_fallback.py`

Expected: 全部通过。

### Task 3: 让 batch manifest 透传新的追溯字段

**Files:**
- Modify: `src/app/ui/widgets/batch/batch_processor_thread.py`
- Modify: `tests/unit/test_signal_handler_batch_manifest.py`

**Step 1: Write the failing test**

在已有 manifest 回归测试基础上增加断言，确认导出的 `processing_details` 会保留 `requested_quality_level` 与 `effective_quality_level`，且不丢失兼容字段 `quality_level`。

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/unit/test_signal_handler_batch_manifest.py -k quality`

Expected: 失败，暴露 manifest 未透传新字段。

**Step 3: Write minimal implementation**

在 `_build_processing_details()` 的 `keep_keys` 中加入 `requested_quality_level` 与 `effective_quality_level`，必要时补齐从 handler 侧的兜底逻辑。

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/unit/test_signal_handler_batch_manifest.py`

Expected: 全部通过。

### Task 4: 定向回归验证

**Files:**
- Verify: `tests/unit/test_ai_params_builder_inpainting_compatibility.py`
- Verify: `tests/unit/test_ai_handler_gpu_runtime_fallback.py`
- Verify: `tests/unit/test_processing_info_quality_trace.py`
- Verify: `tests/unit/test_signal_handler_batch_manifest.py`
- Verify: `tests/unit/test_dynamic_watermark_tracking.py`
- Verify: `tests/unit/test_batch_processor_preloaded_policy.py`

**Step 1: Run targeted regression suite**

Run: `pytest -q tests/unit/test_ai_params_builder_inpainting_compatibility.py tests/unit/test_ai_handler_gpu_runtime_fallback.py tests/unit/test_processing_info_quality_trace.py tests/unit/test_signal_handler_batch_manifest.py tests/unit/test_dynamic_watermark_tracking.py tests/unit/test_batch_processor_preloaded_policy.py`

Expected: 全部通过。

**Step 2: Review changed behavior**

检查：

- 历史/未知 `inpainting_method` 不再误导向 GPU。
- GPU 运行期异常时，当前帧能回退到 OpenCV，而不是直接原样返回。
- `processing_info` 与 manifest 能同时表达请求质量等级和实际生效质量等级。
