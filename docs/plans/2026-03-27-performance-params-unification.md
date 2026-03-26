# Performance Parameters Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收敛性能参数的默认值、持久化、单文件/批处理运行时映射与真实消费点，让性能参数真正“可调、可存、可生效、可追溯”。

**Architecture:** 先新增统一的高级参数快照模型，作为 UI、偏好、预加载、单文件、批处理共同依赖的单一事实来源；再重构性能参数页与参数构建器，把显式处理模式、批处理策略、GPU 显存预算和流水线缓冲预算分别接入对应运行时消费点。整体按 TDD 推进，优先保护“参数模型正确性”和“入口透传契约”，再补运行时预算生效测试。

**Tech Stack:** Python 3.12、PyQt6、OpenCV、PyTorch、FFmpeg、pytest

---

### Task 1: 新增统一高级参数模型

**Files:**
- Create: `src/app/config/advanced_params.py`
- Modify: `src/app/config/__init__.py`
- Test: `tests/unit/test_advanced_params_schema.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
from app.config.advanced_params import AdvancedParamsSnapshot


def test_advanced_params_defaults_are_single_source_of_truth() -> None:
    snapshot = AdvancedParamsSnapshot.defaults()

    assert snapshot.processing_mode == "auto"
    assert snapshot.worker_count == 0
    assert snapshot.enable_gpu is True
    assert snapshot.gpu_memory_limit_mb == 2048
    assert snapshot.enable_cache is True
    assert snapshot.cache_size_mb == 512
    assert snapshot.batch_max_concurrent_files == 1
    assert snapshot.batch_auto_retry_failed is True
    assert snapshot.batch_max_retry_count == 3
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_advanced_params_schema.py"`
Expected: FAIL，提示 `advanced_params.py` 或 `AdvancedParamsSnapshot` 尚不存在。

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class AdvancedParamsSnapshot:
    processing_mode: str
    worker_count: int
    enable_gpu: bool
    gpu_memory_limit_mb: int
    enable_cache: bool
    cache_size_mb: int
    batch_max_concurrent_files: int
    batch_auto_retry_failed: bool
    batch_max_retry_count: int

    @classmethod
    def defaults(cls) -> "AdvancedParamsSnapshot":
        return cls(...)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_advanced_params_schema.py"`
Expected: PASS，确认统一默认值模型已建立。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/config/advanced_params.py src/app/config/__init__.py tests/unit/test_advanced_params_schema.py
git commit -m "refactor(performance-params): 新增统一高级参数模型"
```

### Task 2: 接通偏好默认值与旧结构迁移

**Files:**
- Modify: `src/app/config/preferences/defaults.py`
- Modify: `src/app/config/preferences/validator.py`
- Modify: `src/app/config/preferences/manager.py`
- Test: `tests/unit/app/config/preferences/test_advanced_params_preferences.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_manager_migrates_legacy_advanced_and_batch_preferences() -> None:
    manager = build_manager_with_preferences(
        {
            "advanced": {"max_threads": 6, "enable_gpu": False, "cache_size_mb": 768},
            "batch": {"max_concurrent_files": 2, "auto_retry_failed": False, "max_retry_count": 1},
        }
    )

    snapshot = manager.get_advanced_params_snapshot()

    assert snapshot.worker_count == 6
    assert snapshot.enable_gpu is False
    assert snapshot.cache_size_mb == 768
    assert snapshot.batch_max_concurrent_files == 2
    assert snapshot.batch_auto_retry_failed is False
    assert snapshot.batch_max_retry_count == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/app/config/preferences/test_advanced_params_preferences.py"`
Expected: FAIL，提示偏好管理器还没有统一读取或迁移 `advanced_params`。

**Step 3: Write minimal implementation**

```python
def get_advanced_params_snapshot(self) -> AdvancedParamsSnapshot:
    raw = self.preferences.get("advanced_params", {})
    migrated = migrate_legacy_performance_preferences(
        advanced=self.preferences.get("advanced", {}),
        batch=self.preferences.get("batch", {}),
        current=raw,
    )
    return AdvancedParamsSnapshot.from_dict(migrated)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/app/config/preferences/test_advanced_params_preferences.py"`
Expected: PASS，说明旧偏好能够安全迁移到新结构。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/config/preferences/defaults.py src/app/config/preferences/validator.py src/app/config/preferences/manager.py tests/unit/app/config/preferences/test_advanced_params_preferences.py
git commit -m "refactor(performance-params): 统一高级参数偏好与迁移"
```

### Task 3: 重构性能参数页并接通 widget 持久化

**Files:**
- Modify: `src/app/ui/widgets/advanced/tabs/performance_tab.py`
- Modify: `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- Modify: `src/app/ui/components/control_panel.py`
- Test: `tests/unit/test_advanced_parameters_widget_runtime_model.py`
- Test: `tests/integration/ui/test_ui_components.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_widget_reads_and_writes_unified_performance_params(qtbot) -> None:
    widget = AdvancedParametersWidget()
    widget.set_parameters(
        {
            "processing_mode": "pipeline",
            "worker_count": 0,
            "batch_max_concurrent_files": 3,
            "batch_auto_retry_failed": True,
            "batch_max_retry_count": 2,
        }
    )

    params = widget.get_parameters()
    assert params["processing_mode"] == "pipeline"
    assert params["worker_count"] == 0
    assert params["batch_max_concurrent_files"] == 3
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_advanced_parameters_widget_runtime_model.py" "tests/integration/ui/test_ui_components.py"`
Expected: FAIL，提示当前性能页还没有 `processing_mode` 和批处理参数控件。

**Step 3: Write minimal implementation**

```python
self.processing_mode_combo = QComboBox()
self.processing_mode_combo.addItems(["自动", "单进程", "多进程分块", "流水线"])

self.worker_count_spin = QSpinBox()
self.worker_count_spin.setMinimum(0)
self.worker_count_spin.setSpecialValueText("自动")

self.batch_max_concurrent_spin = QSpinBox()
self.batch_auto_retry_check = QCheckBox("失败后自动重试")
self.batch_retry_count_spin = QSpinBox()
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_advanced_parameters_widget_runtime_model.py" "tests/integration/ui/test_ui_components.py"`
Expected: PASS，确认新控件能够被正确读写。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/widgets/advanced/tabs/performance_tab.py src/app/ui/widgets/advanced/advanced_parameters_widget.py src/app/ui/components/control_panel.py tests/unit/test_advanced_parameters_widget_runtime_model.py tests/integration/ui/test_ui_components.py
git commit -m "feat(performance-params): 重构性能参数界面与持久化入口"
```

### Task 4: 统一运行时导出规则

**Files:**
- Modify: `src/app/ui/utils/ai_params_builder.py`
- Modify: `src/app/config/advanced_params.py`
- Test: `tests/unit/test_ai_params_builder_runtime_strategy.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_snapshot_exports_runtime_flags_and_batch_config() -> None:
    snapshot = AdvancedParamsSnapshot.defaults().replace(
        processing_mode="pipeline",
        worker_count=4,
        batch_max_concurrent_files=2,
    )

    ai_params = snapshot.to_ai_params()
    batch_config = snapshot.to_batch_config()

    assert ai_params["enable_multiprocess"] is True
    assert ai_params["use_pipeline"] is True
    assert ai_params["num_processes"] == 4
    assert batch_config["max_concurrent_files"] == 2
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_ai_params_builder_runtime_strategy.py"`
Expected: FAIL，提示当前模型还不能统一导出运行时标志。

**Step 3: Write minimal implementation**

```python
def to_ai_params(self) -> dict[str, object]:
    return {
        "enable_multiprocess": self.processing_mode in {"multiprocess", "pipeline"} or resolved_auto_mode != "single_process",
        "use_pipeline": self.processing_mode == "pipeline" or resolved_auto_mode == "pipeline",
        "num_processes": self.resolve_worker_count(),
        "gpu_memory_mb": self.gpu_memory_limit_mb,
        "cache_size_mb": self.cache_size_mb,
        "enable_cache": self.enable_cache,
    }
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_ai_params_builder_runtime_strategy.py"`
Expected: PASS，说明 UI 快照已经能稳定导出单文件和批处理运行时配置。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/utils/ai_params_builder.py src/app/config/advanced_params.py tests/unit/test_ai_params_builder_runtime_strategy.py
git commit -m "refactor(performance-params): 统一运行时参数导出"
```

### Task 5: 接通预加载与单文件处理入口

**Files:**
- Modify: `src/app/ui/main_window.py`
- Modify: `src/app/ui/signal_handler.py`
- Test: `tests/unit/test_preload_ai_params_snapshot.py`
- Test: `tests/unit/test_signal_handler_thread_mode_passthrough.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_main_window_preload_uses_unified_runtime_snapshot() -> None:
    snapshot = capture_preload_snapshot()
    assert snapshot["enable_multiprocess"] is not None
    assert snapshot["use_pipeline"] is not None
    assert snapshot["gpu_memory_mb"] == 2048


def test_signal_handler_passes_runtime_mode_and_budget_to_video_thread() -> None:
    kwargs = capture_thread_kwargs()
    assert kwargs["enable_multiprocess"] is True
    assert kwargs["use_pipeline"] is True
    assert kwargs["num_processes"] == 4
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_preload_ai_params_snapshot.py" "tests/unit/test_signal_handler_thread_mode_passthrough.py"`
Expected: FAIL，说明预加载和单文件入口还没有统一使用新快照。

**Step 3: Write minimal implementation**

```python
snapshot = self.preferences.get_advanced_params_snapshot()
preload_ai_params = snapshot.to_ai_params()

runtime_snapshot = self.preferences.get_advanced_params_snapshot()
ai_params = params_builder.build_from_snapshot(runtime_snapshot, ...)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_preload_ai_params_snapshot.py" "tests/unit/test_signal_handler_thread_mode_passthrough.py"`
Expected: PASS，预加载和单文件入口都只依赖统一参数快照。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/main_window.py src/app/ui/signal_handler.py tests/unit/test_preload_ai_params_snapshot.py tests/unit/test_signal_handler_thread_mode_passthrough.py
git commit -m "refactor(performance-params): 接通预加载与单文件运行时参数"
```

### Task 6: 移除批处理硬编码并统一旧入口

**Files:**
- Modify: `src/app/ui/signal_handler.py`
- Modify: `src/app/ui/widgets/batch/batch_processor_thread.py`
- Modify: `src/app/ui/widgets/batch/batch_processing_widget.py`
- Test: `tests/unit/test_batch_processor_thread_mode_passthrough.py`
- Test: `tests/unit/test_signal_handler_batch_config_passthrough.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_signal_handler_uses_snapshot_batch_config_instead_of_hardcoded_defaults() -> None:
    batch = capture_batch_processor_kwargs()
    assert batch["max_concurrent_files"] == 2
    assert batch["auto_retry_failed"] is False
    assert batch["max_retry_count"] == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_batch_processor_thread_mode_passthrough.py" "tests/unit/test_signal_handler_batch_config_passthrough.py"`
Expected: FAIL，提示当前仍使用 `4 / True / 3` 硬编码值。

**Step 3: Write minimal implementation**

```python
batch_config = snapshot.to_batch_config()
self.batch_processor = BatchProcessorThread(
    ...,
    max_concurrent_files=batch_config["max_concurrent_files"],
    auto_retry_failed=batch_config["auto_retry_failed"],
    max_retry_count=batch_config["max_retry_count"],
)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_batch_processor_thread_mode_passthrough.py" "tests/unit/test_signal_handler_batch_config_passthrough.py"`
Expected: PASS，确认批处理入口和旧批处理 widget 都已脱离硬编码。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/signal_handler.py src/app/ui/widgets/batch/batch_processor_thread.py src/app/ui/widgets/batch/batch_processing_widget.py tests/unit/test_batch_processor_thread_mode_passthrough.py tests/unit/test_signal_handler_batch_config_passthrough.py
git commit -m "refactor(performance-params): 统一批处理配置来源"
```

### Task 7: 让 GPU 显存预算真正生效

**Files:**
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `src/app/core/ai/dl_inpainter.py`
- Modify: `src/app/core/ai/inpainting_backends/legacy_unet_backend.py`
- Test: `tests/unit/test_dl_inpainter_profile.py`
- Test: `tests/unit/test_ai_handler_gpu_runtime_fallback.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_ai_handler_applies_gpu_memory_budget_to_deep_inpainting_profile() -> None:
    handler = build_handler(ai_params={"gpu_memory_mb": 1024, "use_gpu_inpainting": True})
    profile = handler.build_gpu_runtime_profile(frame_shape=(1080, 1920, 3))
    assert profile["memory_budget_mb"] == 1024
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_ai_handler_gpu_runtime_fallback.py"`
Expected: FAIL，提示运行时 profile 或预算字段尚不存在。

**Step 3: Write minimal implementation**

```python
self.gpu_memory_limit_mb = int(self.ai_params.get("gpu_memory_mb", 2048))

profile = self._build_gpu_runtime_profile(...)
profile["memory_budget_mb"] = min(self.gpu_memory_limit_mb, detected_free_mb)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/test_dl_inpainter_profile.py" "tests/unit/test_ai_handler_gpu_runtime_fallback.py"`
Expected: PASS，说明 GPU 修复链路已消费显存预算。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/core/ai/ai_handler.py src/app/core/ai/dl_inpainter.py src/app/core/ai/inpainting_backends/legacy_unet_backend.py tests/unit/test_dl_inpainter_profile.py tests/unit/test_ai_handler_gpu_runtime_fallback.py
git commit -m "feat(performance-params): 接通GPU显存预算"
```

### Task 8: 让缓存预算真正影响流水线缓冲

**Files:**
- Modify: `src/app/core/video/modes/pipeline.py`
- Modify: `src/app/core/video/workers/frame_writer.py`
- Modify: `src/app/core/video/utils/backpressure.py`
- Test: `tests/unit/core/video/test_pipeline_cache_budget.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_pipeline_queue_sizes_follow_cache_budget() -> None:
    small = calculate_runtime_queue_sizes(enable_cache=False, cache_size_mb=128, frame_shape=(1080, 1920))
    large = calculate_runtime_queue_sizes(enable_cache=True, cache_size_mb=1024, frame_shape=(1080, 1920))

    assert large.frame_queue_size > small.frame_queue_size
    assert large.result_queue_size > small.result_queue_size
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q "tests/unit/core/video/test_pipeline_cache_budget.py"`
Expected: FAIL，说明当前 `pipeline` 仍只按机器内存猜测队列大小。

**Step 3: Write minimal implementation**

```python
def calculate_runtime_queue_sizes(enable_cache: bool, cache_size_mb: int, frame_shape: tuple[int, int]) -> QueueBudget:
    if not enable_cache:
        return QueueBudget(frame_queue_size=10, result_queue_size=20, writer_buffer_size=20)
    ...
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q "tests/unit/core/video/test_pipeline_cache_budget.py"`
Expected: PASS，说明缓存预算已经能影响流水线缓冲策略。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/core/video/modes/pipeline.py src/app/core/video/workers/frame_writer.py src/app/core/video/utils/backpressure.py tests/unit/core/video/test_pipeline_cache_budget.py
git commit -m "feat(performance-params): 接通流水线缓存预算"
```

### Task 9: 更新文档与回归说明

**Files:**
- Modify: `docs/parameters_analysis.md`
- Modify: `docs/default-video-processing-fix-plan.md`
- Modify: `docs/default-video-processing-slow-investigation.md`
- Test: `tests/unit/test_pyproject_metadata.py`

**Step 1: Write the failing test / verification note**

```python
def test_docs_reference_current_runtime_semantics() -> None:
    # 这里可用轻量 smoke 方式，至少保护文档路径与项目元数据不被误删
    assert True
```

**Step 2: Run verification**

Run: `python -m pytest -q "tests/unit/test_pyproject_metadata.py"`
Expected: PASS，确保文档更新不会伴随项目元数据异常。

**Step 3: Write minimal documentation update**

```markdown
- 处理模式现已显式提供：自动 / 单进程 / 多进程分块 / 流水线
- GPU内存限制现用于深度修复显存预算
- 缓存设置现用于视频流水线帧缓冲预算
- 批处理并发与重试策略统一纳入性能参数
```

**Step 4: Run verification again**

Run: `python -m pytest -q "tests/unit/test_pyproject_metadata.py"`
Expected: PASS，文档与代码现状保持一致。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add docs/parameters_analysis.md docs/default-video-processing-fix-plan.md docs/default-video-processing-slow-investigation.md tests/unit/test_pyproject_metadata.py
git commit -m "docs(performance-params): 更新性能参数统一方案说明"
```

### Task 10: 收口回归测试

**Files:**
- Test: `tests/unit/test_preload_ai_params_snapshot.py`
- Test: `tests/unit/test_signal_handler_thread_mode_passthrough.py`
- Test: `tests/unit/test_batch_processor_thread_mode_passthrough.py`
- Test: `tests/unit/test_dl_inpainter_profile.py`
- Test: `tests/unit/core/video/test_pipeline_cache_budget.py`

**Step 1: Run the focused regression suite**

Run:

```bash
python -m pytest -q \
  "tests/unit/test_advanced_params_schema.py" \
  "tests/unit/app/config/preferences/test_advanced_params_preferences.py" \
  "tests/unit/test_advanced_parameters_widget_runtime_model.py" \
  "tests/unit/test_ai_params_builder_runtime_strategy.py" \
  "tests/unit/test_preload_ai_params_snapshot.py" \
  "tests/unit/test_signal_handler_thread_mode_passthrough.py" \
  "tests/unit/test_batch_processor_thread_mode_passthrough.py" \
  "tests/unit/test_signal_handler_batch_config_passthrough.py" \
  "tests/unit/test_dl_inpainter_profile.py" \
  "tests/unit/test_ai_handler_gpu_runtime_fallback.py" \
  "tests/unit/core/video/test_pipeline_cache_budget.py"
```

Expected: 全部 PASS。

**Step 2: Run secondary smoke tests**

Run:

```bash
python -m pytest -q \
  "tests/integration/ui/test_ui_components.py" \
  "tests/integration/core/ai/video/test_video_modes.py"
```

Expected: PASS，确认新参数模型未破坏 UI 与视频模式主链路。

**Step 3: Record residual risks**

```text
- cache_size_mb 当前只作用于流水线缓冲预算，不是跨任务结果缓存
- gpu_memory_limit_mb 当前主要约束深度修复路径，不承诺统一约束所有 CUDA 分配
```

**Step 4: Optional manual verification**

Run: 启动主程序，手动确认性能页能保存并恢复 `处理模式 / GPU预算 / 缓冲预算 / 批处理策略`。
Expected: 重启后仍保持上次设置，单文件与批处理都按新参数生效。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add tests/unit tests/integration
git commit -m "test(performance-params): 补齐性能参数统一回归覆盖"
```
