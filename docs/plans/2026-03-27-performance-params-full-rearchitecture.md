# Performance Parameters Full Rearchitecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把性能参数升级为统一运行时配置架构，彻底解决 `auto` 模式伪自动、LaMa 路径显存预算伪生效、批处理旧配置旁路未收口这 3 个问题。

**Architecture:** 保留 `AdvancedParamsSnapshot` 作为 UI 与偏好层的统一快照，同时新增“处理上下文 + 解析后运行时配置”两层模型，把模式解析、显存预算、缓存预算、批处理策略全部集中到统一解析函数中。单文件、批处理、预加载、AI backend、manifest 只消费解析后的运行时配置，不再依赖散落的手写映射与旧配置旁路。

**Tech Stack:** Python 3.12、PyQt6、pytest、OpenCV、PyTorch、FFmpeg

---

### Task 1: 为彻底重构补齐解析层失败测试

**Files:**
- Modify: `tests/unit/test_advanced_params_schema.py`
- Modify: `tests/unit/test_ai_params_builder_runtime_strategy.py`
- Create: `tests/unit/test_resolved_performance_config.py`

**Step 1: Write the failing test**

```python
def test_auto_mode_for_video_resolves_to_pipeline_when_cpu_is_sufficient() -> None:
    snapshot = AdvancedParamsSnapshot.defaults()
    context = ProcessingContext(
        input_file_path="demo.mp4",
        is_batch=False,
        prefer_pipeline=True,
        cpu_count=8,
        gpu_enabled=True,
    )

    resolved = snapshot.resolve(context)

    assert resolved.requested_processing_mode == "auto"
    assert resolved.resolved_processing_mode == "pipeline"
    assert resolved.enable_multiprocess is True
    assert resolved.use_pipeline is True
    assert resolved.worker_count >= 2
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_resolved_performance_config.py" "tests/unit/test_advanced_params_schema.py" "tests/unit/test_ai_params_builder_runtime_strategy.py"`

Expected: FAIL，提示 `ProcessingContext` / `resolve()` / `ResolvedPerformanceConfig` 尚不存在。

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class ProcessingContext:
    input_file_path: str | None
    is_batch: bool
    prefer_pipeline: bool
    cpu_count: int
    gpu_enabled: bool


@dataclass(frozen=True)
class ResolvedPerformanceConfig:
    requested_processing_mode: str
    resolved_processing_mode: str
    worker_count: int
    enable_multiprocess: bool
    use_pipeline: bool
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_resolved_performance_config.py" "tests/unit/test_advanced_params_schema.py" "tests/unit/test_ai_params_builder_runtime_strategy.py"`

Expected: PASS，证明重构后的解析层接口已经建立。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add tests/unit/test_advanced_params_schema.py tests/unit/test_ai_params_builder_runtime_strategy.py tests/unit/test_resolved_performance_config.py
git commit -m "test(performance-params): 补齐运行时配置解析失败测试"
```

### Task 2: 重构 `advanced_params.py` 为“三层模型”

**Files:**
- Modify: `src/app/config/advanced_params.py`
- Modify: `src/app/config/__init__.py`
- Test: `tests/unit/test_resolved_performance_config.py`

**Step 1: Write the failing test**

```python
def test_snapshot_resolve_returns_runtime_config_with_budget_and_batch_policy() -> None:
    snapshot = AdvancedParamsSnapshot.defaults().replace(
        processing_mode="pipeline",
        worker_count=4,
        gpu_memory_limit_mb=1536,
        batch_max_concurrent_files=3,
    )
    resolved = snapshot.resolve(ProcessingContext(input_file_path="demo.mp4", is_batch=True))

    assert resolved.worker_count == 4
    assert resolved.gpu_memory_budget_mb == 1536
    assert resolved.batch_max_concurrent_files == 3
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_resolved_performance_config.py"`

Expected: FAIL，说明当前快照还不能解析出完整运行时配置。

**Step 3: Write minimal implementation**

```python
def resolve(self, context: ProcessingContext) -> ResolvedPerformanceConfig:
    ...
    return ResolvedPerformanceConfig(...)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_resolved_performance_config.py"`

Expected: PASS，说明统一解析函数已经能生成运行时配置。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/config/advanced_params.py src/app/config/__init__.py tests/unit/test_resolved_performance_config.py
git commit -m "refactor(performance-params): 建立运行时性能配置解析层"
```

### Task 3: 重构偏好与 UI，仅保留快照职责

**Files:**
- Modify: `src/app/config/preferences/defaults.py`
- Modify: `src/app/config/preferences/manager.py`
- Modify: `src/app/config/preferences/validator.py`
- Modify: `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- Modify: `src/app/ui/widgets/advanced/tabs/performance_tab.py`
- Test: `tests/unit/app/config/preferences/test_advanced_params_preferences.py`
- Test: `tests/unit/test_advanced_parameters_widget_runtime_model.py`

**Step 1: Write the failing test**

```python
def test_widget_and_preferences_roundtrip_snapshot_without_runtime_logic(qtbot) -> None:
    widget = AdvancedParametersWidget()
    widget.set_parameters({"processing_mode": "auto", "worker_count": 0, "gpu_memory_limit_mb": 1024})

    params = widget.get_parameters()
    assert params["processing_mode"] == "auto"
    assert params["worker_count"] == 0
    assert params["gpu_memory_limit_mb"] == 1024
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/app/config/preferences/test_advanced_params_preferences.py" "tests/unit/test_advanced_parameters_widget_runtime_model.py"`

Expected: FAIL，说明 widget / 偏好层仍耦合旧逻辑或默认值漂移。

**Step 3: Write minimal implementation**

```python
# widget 只读写 snapshot 字段，不自行推导运行时标志
params = snapshot.to_ui_dict()
preferences.set_preference("advanced_params", key, value)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/app/config/preferences/test_advanced_params_preferences.py" "tests/unit/test_advanced_parameters_widget_runtime_model.py"`

Expected: PASS，确认 UI 与偏好层只负责快照读写。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/config/preferences/defaults.py src/app/config/preferences/manager.py src/app/config/preferences/validator.py src/app/ui/widgets/advanced/advanced_parameters_widget.py src/app/ui/widgets/advanced/tabs/performance_tab.py tests/unit/app/config/preferences/test_advanced_params_preferences.py tests/unit/test_advanced_parameters_widget_runtime_model.py
git commit -m "refactor(performance-params): 收窄快照与偏好层职责"
```

### Task 4: 入口层全部改为消费 `ResolvedPerformanceConfig`

**Files:**
- Modify: `src/app/ui/utils/ai_params_builder.py`
- Modify: `src/app/ui/signal_handler.py`
- Modify: `src/app/ui/main_window.py`
- Test: `tests/unit/test_signal_handler_thread_mode_passthrough.py`
- Test: `tests/unit/test_signal_handler_batch_config_passthrough.py`
- Create: `tests/unit/test_preload_runtime_performance_config.py`

**Step 1: Write the failing test**

```python
def test_signal_handler_uses_resolved_performance_config_for_video_thread() -> None:
    kwargs = capture_thread_kwargs()
    assert kwargs["enable_multiprocess"] is True
    assert kwargs["use_pipeline"] is True
    assert kwargs["num_processes"] >= 2


def test_preload_path_uses_same_resolved_runtime_config() -> None:
    payload = capture_preload_ai_params()
    assert payload["resolved_processing_mode"] in {"single_process", "multiprocess", "pipeline"}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_signal_handler_thread_mode_passthrough.py" "tests/unit/test_signal_handler_batch_config_passthrough.py" "tests/unit/test_preload_runtime_performance_config.py"`

Expected: FAIL，说明入口层仍在直接拼装旧 `ai_params`。

**Step 3: Write minimal implementation**

```python
snapshot = AdvancedParamsSnapshot.from_dict(advanced_params)
context = ProcessingContext(...)
resolved = snapshot.resolve(context)

ai_params = resolved.to_ai_params()
batch_config = resolved.to_batch_config()
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_signal_handler_thread_mode_passthrough.py" "tests/unit/test_signal_handler_batch_config_passthrough.py" "tests/unit/test_preload_runtime_performance_config.py"`

Expected: PASS，入口层全部统一走解析后配置。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/utils/ai_params_builder.py src/app/ui/signal_handler.py src/app/ui/main_window.py tests/unit/test_signal_handler_thread_mode_passthrough.py tests/unit/test_signal_handler_batch_config_passthrough.py tests/unit/test_preload_runtime_performance_config.py
git commit -m "refactor(performance-params): 统一入口层运行时配置消费"
```

### Task 5: 定义深度修复 backend 的统一 runtime profile 协议

**Files:**
- Modify: `src/app/core/ai/inpainting_backends/base.py`
- Modify: `src/app/core/ai/inpainting_backends/factory.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Create: `tests/unit/test_ai_backend_runtime_profile_contract.py`

**Step 1: Write the failing test**

```python
def test_ai_handler_pushes_runtime_profile_to_active_deep_backend() -> None:
    backend = StubBackend()
    handler = build_handler_with_backend(backend, gpu_memory_mb=1024)

    profile = handler.build_gpu_runtime_profile((1080, 1920, 3))

    assert backend.received_profile["memory_budget_mb"] == profile["memory_budget_mb"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_ai_backend_runtime_profile_contract.py" "tests/unit/test_ai_handler_gpu_runtime_fallback.py"`

Expected: FAIL，说明 backend 还没有统一 runtime profile 协议。

**Step 3: Write minimal implementation**

```python
class BaseInpaintingBackend:
    def set_runtime_profile(self, profile: dict[str, object]) -> None:
        self._runtime_profile = dict(profile)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_ai_backend_runtime_profile_contract.py" "tests/unit/test_ai_handler_gpu_runtime_fallback.py"`

Expected: PASS，说明 `AIHandler -> backend` 的统一 profile 契约成立。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/core/ai/inpainting_backends/base.py src/app/core/ai/inpainting_backends/factory.py src/app/core/ai/ai_handler.py tests/unit/test_ai_backend_runtime_profile_contract.py
git commit -m "refactor(ai-runtime): 建立深度修复运行时profile协议"
```

### Task 6: 重构 LaMa backend，使预算真实生效

**Files:**
- Modify: `src/app/core/ai/inpainting_backends/lama_backend.py`
- Modify: `src/app/core/ai/lama_runtime.py`
- Test: `tests/unit/test_lama_backend_runtime_budget.py`
- Modify: `tests/unit/test_lama_backend_roi_inpainting.py`
- Modify: `tests/unit/test_lama_runtime.py`

**Step 1: Write the failing test**

```python
def test_lama_backend_applies_runtime_budget_to_resize_limit() -> None:
    backend = build_lama_backend_with_stub_runner()
    backend.set_runtime_profile({"memory_budget_mb": 1024, "resize_limit": 640})

    result = backend.inpaint_frame(frame, mask, inpaint_radius=3, quality_level=3)

    assert backend.get_last_trace()["memory_budget_mb"] == 1024
    assert backend.get_last_trace()["resize_limit"] == 640
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_lama_backend_runtime_budget.py" "tests/unit/test_lama_backend_roi_inpainting.py" "tests/unit/test_lama_runtime.py"`

Expected: FAIL，说明 LaMa 路径尚未真实消费 runtime budget。

**Step 3: Write minimal implementation**

```python
def set_runtime_profile(self, profile: dict[str, object]) -> None:
    self._runtime_profile = dict(profile)


def inpaint_frame(...):
    profile = self._runtime_profile or {}
    ...
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_lama_backend_runtime_budget.py" "tests/unit/test_lama_backend_roi_inpainting.py" "tests/unit/test_lama_runtime.py"`

Expected: PASS，说明 LaMa 路径已经具备预算驱动的真实收缩逻辑。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/core/ai/inpainting_backends/lama_backend.py src/app/core/ai/lama_runtime.py tests/unit/test_lama_backend_runtime_budget.py tests/unit/test_lama_backend_roi_inpainting.py tests/unit/test_lama_runtime.py
git commit -m "feat(lama-backend): 接通预算驱动运行时profile"
```

### Task 7: 对齐 legacy U-Net 与 LaMa 的预算语义

**Files:**
- Modify: `src/app/core/ai/dl_inpainter.py`
- Modify: `src/app/core/ai/inpainting_backends/legacy_unet_backend.py`
- Modify: `tests/unit/test_dl_inpainter_profile.py`
- Create: `tests/unit/test_legacy_unet_backend_runtime_budget.py`

**Step 1: Write the failing test**

```python
def test_legacy_unet_backend_and_lama_share_same_budget_semantics() -> None:
    backend = build_legacy_unet_backend()
    backend.set_runtime_profile({"memory_budget_mb": 1536, "resize_limit": 768})
    assert backend.get_last_trace()["memory_budget_mb"] == 1536
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_legacy_unet_backend_runtime_budget.py"`

Expected: FAIL，说明旧 GPU 路径与 LaMa 还没有统一预算语义。

**Step 3: Write minimal implementation**

```python
def set_runtime_profile(self, profile: dict[str, object]) -> None:
    self.dl_inpainter.set_runtime_memory_budget(profile.get("memory_budget_mb"))
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_legacy_unet_backend_runtime_budget.py"`

Expected: PASS，说明所有深度后端已经共享统一预算协议。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/core/ai/dl_inpainter.py src/app/core/ai/inpainting_backends/legacy_unet_backend.py tests/unit/test_dl_inpainter_profile.py tests/unit/test_legacy_unet_backend_runtime_budget.py
git commit -m "refactor(ai-runtime): 统一深度后端预算语义"
```

### Task 8: 删除批处理旧配置旁路并统一边界

**Files:**
- Modify: `src/app/ui/widgets/batch/batch_processing_widget.py`
- Modify: `src/app/ui/widgets/batch/batch_processor_thread.py`
- Modify: `tests/integration/test_batch_processing.py`
- Create: `tests/unit/test_batch_processing_widget_runtime_config.py`

**Step 1: Write the failing test**

```python
def test_batch_processing_widget_no_longer_reads_config_manager_batch_fields() -> None:
    widget = BatchProcessingWidget()
    widget.set_advanced_params({"batch_max_concurrent_files": 12})

    assert widget.max_concurrent_files == 12
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_batch_processing_widget_runtime_config.py" "tests/integration/test_batch_processing.py"`

Expected: FAIL，说明 widget 仍依赖旧 `set_config()` 逻辑或边界不一致。

**Step 3: Write minimal implementation**

```python
def set_config(self, config):
    self.config = config
    # 不再从 config 读取 batch 性能参数
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_batch_processing_widget_runtime_config.py" "tests/integration/test_batch_processing.py"`

Expected: PASS，说明批处理旁路已被彻底收口。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/widgets/batch/batch_processing_widget.py src/app/ui/widgets/batch/batch_processor_thread.py tests/unit/test_batch_processing_widget_runtime_config.py tests/integration/test_batch_processing.py
git commit -m "refactor(batch-processing): 删除旧批处理性能参数旁路"
```

### Task 9: 统一 manifest 与 trace 输出

**Files:**
- Modify: `src/app/ui/signal_handler.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `tests/unit/test_signal_handler_batch_manifest.py`
- Create: `tests/unit/test_resolved_performance_manifest_trace.py`

**Step 1: Write the failing test**

```python
def test_manifest_and_trace_record_requested_and_resolved_runtime_values() -> None:
    payload = capture_manifest_payload()
    assert "requested_processing_mode" in payload
    assert "resolved_processing_mode" in payload
    assert "gpu_memory_budget_mb" in payload
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_signal_handler_batch_manifest.py" "tests/unit/test_resolved_performance_manifest_trace.py"`

Expected: FAIL，说明 manifest / trace 还没有完整记录解析结果。

**Step 3: Write minimal implementation**

```python
manifest.update(resolved_config.to_manifest_dict())
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_signal_handler_batch_manifest.py" "tests/unit/test_resolved_performance_manifest_trace.py"`

Expected: PASS，说明请求值与解析值都已可追溯。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/signal_handler.py src/app/core/ai/ai_handler.py tests/unit/test_signal_handler_batch_manifest.py tests/unit/test_resolved_performance_manifest_trace.py
git commit -m "feat(performance-params): 补齐解析值trace与manifest导出"
```

### Task 10: 跑聚焦回归并记录残余风险

**Files:**
- Test: `tests/unit/test_resolved_performance_config.py`
- Test: `tests/unit/test_signal_handler_thread_mode_passthrough.py`
- Test: `tests/unit/test_signal_handler_batch_config_passthrough.py`
- Test: `tests/unit/test_ai_backend_runtime_profile_contract.py`
- Test: `tests/unit/test_lama_backend_runtime_budget.py`
- Test: `tests/unit/test_legacy_unet_backend_runtime_budget.py`
- Test: `tests/unit/test_batch_processing_widget_runtime_config.py`
- Test: `tests/unit/test_signal_handler_batch_manifest.py`

**Step 1: Run the focused regression suite**

Run:

```bash
python -m pytest -q \
  "tests/unit/test_advanced_params_schema.py" \
  "tests/unit/test_ai_params_builder_runtime_strategy.py" \
  "tests/unit/test_resolved_performance_config.py" \
  "tests/unit/app/config/preferences/test_advanced_params_preferences.py" \
  "tests/unit/test_advanced_parameters_widget_runtime_model.py" \
  "tests/unit/test_signal_handler_thread_mode_passthrough.py" \
  "tests/unit/test_signal_handler_batch_config_passthrough.py" \
  "tests/unit/test_preload_runtime_performance_config.py" \
  "tests/unit/test_ai_backend_runtime_profile_contract.py" \
  "tests/unit/test_ai_handler_gpu_runtime_fallback.py" \
  "tests/unit/test_lama_backend_runtime_budget.py" \
  "tests/unit/test_lama_backend_roi_inpainting.py" \
  "tests/unit/test_lama_runtime.py" \
  "tests/unit/test_dl_inpainter_profile.py" \
  "tests/unit/test_legacy_unet_backend_runtime_budget.py" \
  "tests/unit/test_batch_processing_widget_runtime_config.py" \
  "tests/unit/test_signal_handler_batch_manifest.py"
```

Expected: 全部 PASS。

**Step 2: Run secondary integration checks**

Run:

```bash
python -m pytest -q \
  "tests/integration/test_batch_processing.py" \
  "tests/integration/test_dl_inpainter_gpu.py"
```

Expected: PASS，确认单文件、批处理、LaMa 路径仍然可用。

**Step 3: Record residual risks**

```text
- cache_size_mb 仍然只代表流水线缓冲预算，不代表跨任务结果缓存
- gpu_memory_limit_mb 是软预算，不承诺对所有 CUDA 分配做硬隔离
- auto 策略首版主要基于任务类型与 CPU 核数，后续如需纳入更多维度应增量扩展
```

**Step 4: Manual verification**

Run: 手动启动应用，确认性能参数页修改后，重启仍能恢复；单文件视频与批处理都能展示真实解析模式与预算值。

Expected: 行为与 manifest / trace 一致。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add tests/unit tests/integration
git commit -m "test(performance-params): 补齐性能参数彻底重构回归覆盖"
```
