# LaMa 默认修复后端接入 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 以“统一 inpainting backend 抽象层”为基础，把 LaMa 接入为默认深度修复后端，保留 legacy U-Net 兼容路径，并补齐参数迁移、trace 与 batch manifest 回归测试。

**Architecture:** 新增 `inpainting_backends` 适配层，把 `AIHandler` 从“直接操纵 OpenCV/U-Net 细节”改为“选择 backend、协调加载、运行期 fallback、聚合 trace”；UI 与 builder 输出统一的 `requested_inpainting_backend`，batch/manifest 只消费统一 trace 契约。MAT 只预留枚举和扩展位，不在本计划中实现具体 backend。

**Tech Stack:** Python 3.12、PyTorch、PyQt6、pytest

---

### Task 1: 先锁定参数迁移与 trace 契约的失败测试

**Files:**
- Create: `tests/unit/test_inpainting_backend_selection.py`
- Create: `tests/unit/test_processing_info_backend_trace.py`
- Modify: `tests/unit/test_ai_params_builder_inpainting_compatibility.py`

**Step 1: Write the failing tests**

新增至少覆盖这些断言：

- UI 选择 `LaMa 深度学习修复（推荐）` 时，builder 输出 `requested_inpainting_backend == "lama"`。
- 历史 `inpainting_algorithm=gpu_dl` 仍会映射到 `requested_inpainting_backend == "legacy_unet"`。
- OpenCV 路径会输出 `requested_inpainting_backend == "opencv"`，并带上 `opencv_inpainting_method`。
- `processing_info` 同时包含 `requested_inpainting_backend`、`actual_inpainting_backend`、`inpainting_fallback_reason`。
- 兼容字段 `inpainting_backend`、`gpu_inpainting_fallback_reason` 仍存在。

**Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_backend_selection.py tests/unit/test_processing_info_backend_trace.py tests/unit/test_ai_params_builder_inpainting_compatibility.py -q`

Expected: 失败，暴露当前没有统一 backend 枚举与 trace 字段的问题。

**Step 3: Write minimal implementation**

先只补：

- builder 的新字段输出
- validator 的新枚举
- 兼容映射

暂时不要实现完整 LaMa backend，只让测试从“导入/字段缺失”收敛到真正的运行期行为缺口。

**Step 4: Run tests to verify they fail correctly**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_backend_selection.py tests/unit/test_processing_info_backend_trace.py -q`

Expected: 失败原因收敛到 `AIHandler` 还没有产出新的 trace 字段或 backend 选择逻辑。

### Task 2: 建立统一 inpainting backend 抽象层

**Files:**
- Create: `src/app/core/ai/inpainting_backends/__init__.py`
- Create: `src/app/core/ai/inpainting_backends/base.py`
- Create: `src/app/core/ai/inpainting_backends/factory.py`
- Create: `src/app/core/ai/inpainting_backends/opencv_backend.py`
- Create: `src/app/core/ai/inpainting_backends/legacy_unet_backend.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `src/app/core/ai/dl_inpainter.py`

**Step 1: Write the failing test for backend factory behavior**

在 `tests/unit/test_inpainting_backend_selection.py` 中新增断言：

- 请求 `opencv` 返回 OpenCV backend
- 请求 `legacy_unet` 返回 legacy U-Net backend
- 请求未知 backend 安全回退到 OpenCV

**Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_backend_selection.py -q`

Expected: 失败，提示还没有 backend factory 或返回对象不符合预期。

**Step 3: Write minimal implementation**

实现最小 backend 契约：

- backend id
- `load()`
- `inpaint_frame()`
- `get_last_trace()`
- `cleanup()`

先让 OpenCV 与 legacy U-Net 能通过抽象层工作，再把 `AIHandler` 改为消费 factory。

**Step 4: Run tests to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_backend_selection.py tests/unit/test_processing_info_backend_trace.py -q`

Expected: backend 选择与基础 trace 测试通过。

### Task 3: 接入 LaMa backend 与运行期 fallback

**Files:**
- Create: `src/app/core/ai/inpainting_backends/lama_backend.py`
- Create: `src/app/utils/inpainting_model_downloader.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `src/app/core/video/thread.py`
- Create: `tests/unit/test_lama_backend_runtime_fallback.py`

**Step 1: Write the failing tests**

新增至少覆盖：

- 请求 `lama` 且资源缺失时，实际后端回退到 `opencv`
- 请求 `lama` 且运行期抛异常时，`processing_info` 记录：
  - `requested_inpainting_backend == "lama"`
  - `actual_inpainting_backend == "opencv"`
  - `inpainting_fallback_reason == "lama_runtime_exception"`
- `AI_HANDLER_REFRESH_KEYS` 在 `requested_inpainting_backend`、LaMa 资源路径变化时会触发重建

**Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_lama_backend_runtime_fallback.py tests/unit/test_inpainting_backend_selection.py -q`

Expected: 失败，暴露 LaMa backend 不存在、refresh keys 不完整或 fallback trace 不完整。

**Step 3: Write minimal implementation**

实现：

- LaMa backend 最小加载接口
- 资源引用解析
- `AIHandler` 中的 `lama -> opencv` fallback
- `thread.py` 中新的 refresh keys 与资源参数注入

**Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_lama_backend_runtime_fallback.py tests/unit/test_inpainting_backend_selection.py tests/unit/test_processing_info_backend_trace.py -q`

Expected: 全部通过。

### Task 4: 完成 UI、builder、validator 与 batch manifest 迁移

**Files:**
- Modify: `src/app/ui/widgets/advanced/tabs/inpainting_tab.py`
- Modify: `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- Modify: `src/app/ui/utils/ai_params_builder.py`
- Modify: `src/app/config/validators.py`
- Modify: `src/app/ui/widgets/batch/batch_processor_thread.py`
- Modify: `src/app/ui/signal_handler.py`
- Modify: `tests/unit/test_batch_processing_details_effective_params.py`
- Modify: `tests/unit/test_signal_handler_batch_manifest.py`

**Step 1: Write the failing tests**

新增或增强断言：

- batch `processing_details` 会保留：
  - `requested_inpainting_backend`
  - `actual_inpainting_backend`
  - `inpainting_fallback_reason`
- manifest 导出后：
  - `run.ai_params.requested_inpainting_backend` 正确
  - `items[0].processing_details.actual_inpainting_backend` 正确
- UI 新文案仍能经 builder 正常映射

**Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_batch_processing_details_effective_params.py tests/unit/test_signal_handler_batch_manifest.py tests/unit/test_ai_params_builder_inpainting_compatibility.py -q`

Expected: 失败，暴露 keep_keys 未透传、manifest 未导出新字段或 UI/validator 文案未同步。

**Step 3: Write minimal implementation**

完成：

- UI 文案切换到 LaMa 默认
- builder/validator 输出新协议
- batch keep_keys 补齐
- manifest run/processing_details 透传新字段

**Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_batch_processing_details_effective_params.py tests/unit/test_signal_handler_batch_manifest.py tests/unit/test_ai_params_builder_inpainting_compatibility.py -q`

Expected: 全部通过。

### Task 5: 补真实 GPU subprocess smoke 与定向回归

**Files:**
- Create: `tests/integration/runtime/lama_smoke.py`
- Modify: `tests/integration/test_dl_inpainter_gpu.py`
- Verify: `tests/unit/test_lama_backend_runtime_fallback.py`
- Verify: `tests/unit/test_processing_info_backend_trace.py`
- Verify: `tests/unit/test_signal_handler_batch_manifest.py`

**Step 1: Write the failing smoke wrapper**

增加 subprocess 包装测试：

- 先在子进程探测 `torch` 可导入
- 再运行 `tests/integration/runtime/lama_smoke.py`
- 不在默认 pytest 主进程里直接导入 Qt + torch GPU 运行时

**Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/integration/test_dl_inpainter_gpu.py -q`

Expected: 失败或跳过逻辑不完整，说明 subprocess smoke 还没接好。

**Step 3: Write minimal implementation**

补齐：

- LaMa smoke 脚本
- subprocess 包装逻辑
- 必要的跳过条件和错误摘要
- 新增 `lama_runtime.py`，让 `VWR_LAMA_MODEL_PATH` 指向 TorchScript `.pt/.jit/.ts` 文件
  或包含该文件的目录时，能够真实创建 runner 并执行单帧推理
- 对官方 `config.yaml + models/*.ckpt` 目录输出明确的“不支持直接加载，需要转换为 TorchScript”
  诊断，而不是继续落回模糊的 `lama_runner_unavailable`

**Step 4: Run targeted regression suite**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_backend_selection.py tests/unit/test_processing_info_backend_trace.py tests/unit/test_lama_backend_runtime_fallback.py tests/unit/test_batch_processing_details_effective_params.py tests/unit/test_signal_handler_batch_manifest.py -q`

Expected: 全部通过。

**Step 5: Run integration smoke**

Run: `.venv/Scripts/python.exe -m pytest tests/integration/test_dl_inpainter_gpu.py -q`

Expected:

- 无 GPU / 无 torch 时安全跳过
- 环境满足时通过 subprocess 跑完 LaMa smoke
- 给定临时 TorchScript 资产时，smoke 必须真实通过，不能再以 `lama_runner_unavailable`
  为由跳过

### Task 6: 文档与收尾验证

**Files:**
- Verify: `docs/plans/2026-03-25-lama-backend-integration-design.md`
- Verify: `docs/plans/2026-03-25-mat-backend-followup-design.md`
- Verify: `docs/plans/2026-03-25-lama-backend-integration.md`

**Step 1: Review changed behavior**

重点确认：

- LaMa 是默认深度修复后端
- legacy U-Net 仅作为兼容备用
- `run.ai_params` 代表请求配置
- `processing_details` 代表实际执行观测
- MAT 仅保留枚举与扩展位，没有混进第一阶段主链

**Step 2: Final verification**

Run:

- `.venv/Scripts/python.exe -m pytest tests/unit/test_inpainting_backend_selection.py tests/unit/test_processing_info_backend_trace.py tests/unit/test_lama_backend_runtime_fallback.py tests/unit/test_batch_processing_details_effective_params.py tests/unit/test_signal_handler_batch_manifest.py -q`
- `.venv/Scripts/python.exe -m pytest tests/integration/test_dl_inpainter_gpu.py -q`

Expected: 单元回归通过；真实 GPU smoke 在环境满足时通过，不满足时明确跳过。
