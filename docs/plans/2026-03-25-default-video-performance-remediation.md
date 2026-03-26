# Default Video Performance Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收敛“默认参数下视频处理特别慢”的主根因，让首个视频任务不再因为冷启动、串行路径和重复 backend 初始化而明显卡顿。

**Architecture:** 先统一默认参数快照，让预加载、单文件入口、批处理入口共享同一组运行时默认值；再把单文件视频策略从固定 `single-process` 改成可显式透传的策略选择；最后清理 OpenCV backend 生命周期、LaMa 回退、日志与音频配置等放大项。整个修复按 TDD 推进，优先保护入口参数契约和性能关键路径。

**Tech Stack:** Python 3.12、PyQt6、OpenCV、PyTorch、Ultralytics YOLO、FFmpeg、pytest

---

### Task 1: 统一默认参数快照

**Files:**
- Modify: `src/app/ui/main_window.py`
- Modify: `src/app/ui/utils/ai_params_builder.py`
- Modify: `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- Test: `tests/unit/test_ai_params_builder_runtime_defaults.py`
- Test: `tests/unit/test_main_window_preload_snapshot.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_build_default_runtime_params_matches_widget_defaults():
    params = builder.build_default_runtime_params(preferences=fake_preferences)
    assert params["conf_threshold"] == 0.5
    assert params["requested_inpainting_backend"] == "lama"
    assert params["num_processes"] == 4
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_ai_params_builder_runtime_defaults.py tests/unit/test_main_window_preload_snapshot.py -q`
Expected: FAIL，提示默认参数快照 helper 或预加载快照接线不存在。

**Step 3: Write minimal implementation**

```python
default_params = self.control_panel.get_advanced_parameters()
runtime_defaults = AIParamsBuilder().build_from_ui(...)
self.ai_preload_thread = AIModelPreloader(self.config, runtime_defaults, self)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_ai_params_builder_runtime_defaults.py tests/unit/test_main_window_preload_snapshot.py -q`
Expected: PASS，且预加载不再使用 `ai_params={}`。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/main_window.py src/app/ui/utils/ai_params_builder.py src/app/ui/widgets/advanced/advanced_parameters_widget.py tests/unit/test_ai_params_builder_runtime_defaults.py tests/unit/test_main_window_preload_snapshot.py
git commit -m "perf(video-runtime): 对齐默认参数快照"
```

### Task 2: 打通单文件与批处理入口的模式透传

**Files:**
- Modify: `src/app/ui/signal_handler.py`
- Modify: `src/app/ui/widgets/batch/batch_processor_thread.py`
- Test: `tests/unit/test_signal_handler_thread_mode_passthrough.py`
- Test: `tests/unit/test_batch_processor_video_mode_passthrough.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_signal_handler_passes_video_mode_flags(monkeypatch):
    kwargs = captured_thread_kwargs(monkeypatch)
    handler.handle_start_processing()
    assert kwargs["num_processes"] == 4
    assert "enable_multiprocess" in kwargs
    assert "use_pipeline" in kwargs
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_signal_handler_thread_mode_passthrough.py tests/unit/test_batch_processor_video_mode_passthrough.py -q`
Expected: FAIL，提示 `VideoProcessorThread` 构造参数缺失。

**Step 3: Write minimal implementation**

```python
mode_flags = self._build_video_mode_flags(ai_params)
processor = VideoProcessorThread(
    ...,
    num_processes=mode_flags["num_processes"],
    enable_multiprocess=mode_flags["enable_multiprocess"],
    use_pipeline=mode_flags["use_pipeline"],
)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_signal_handler_thread_mode_passthrough.py tests/unit/test_batch_processor_video_mode_passthrough.py -q`
Expected: PASS，单文件和批处理入口都透传模式开关。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/signal_handler.py src/app/ui/widgets/batch/batch_processor_thread.py tests/unit/test_signal_handler_thread_mode_passthrough.py tests/unit/test_batch_processor_video_mode_passthrough.py
git commit -m "perf(video-runtime): 打通视频模式参数透传"
```

### Task 3: 引入默认视频策略选择

**Files:**
- Modify: `src/app/core/video/thread.py`
- Modify: `src/app/core/video/modes/single_process.py`
- Modify: `src/app/core/video/modes/pipeline.py`
- Modify: `src/app/core/video/modes/multiprocess.py`
- Test: `tests/integration/core/ai/video/test_video_modes.py`
- Test: `tests/integration/runtime/task6_runtime_smoke.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_video_thread_prefers_pipeline_for_gpu_video():
    strategy = choose_processing_strategy(
        is_video=True, device="cuda", total_frames=300, num_processes=4
    )
    assert strategy.use_pipeline is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/core/ai/video/test_video_modes.py tests/integration/runtime/task6_runtime_smoke.py -q`
Expected: FAIL，提示默认策略仍固定为 `single-process`。

**Step 3: Write minimal implementation**

```python
if self.enable_multiprocess:
    ...
else:
    strategy = choose_processing_strategy(...)
    self.enable_multiprocess = strategy.enable_multiprocess
    self.use_pipeline = strategy.use_pipeline
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/core/ai/video/test_video_modes.py tests/integration/runtime/task6_runtime_smoke.py -q`
Expected: PASS，且日志/状态能反映实际策略。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/core/video/thread.py src/app/core/video/modes/single_process.py src/app/core/video/modes/pipeline.py src/app/core/video/modes/multiprocess.py tests/integration/core/ai/video/test_video_modes.py tests/integration/runtime/task6_runtime_smoke.py
git commit -m "perf(video-core): 引入默认视频策略选择"
```

### Task 4: 修复 OpenCV backend 重复加载

**Files:**
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `src/app/core/ai/inpainting_backends/opencv_backend.py`
- Modify: `src/app/core/ai/image_inpainter.py`
- Test: `tests/unit/test_ai_handler_opencv_backend_load_once.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_opencv_backend_load_only_once(monkeypatch):
    handler = build_ai_handler()
    handler.inpaint_frame(frame, mask)
    handler.inpaint_frame(frame, mask)
    assert backend_load_calls == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_ai_handler_opencv_backend_load_once.py -q`
Expected: FAIL，显示 `load()` 被调用多次。

**Step 3: Write minimal implementation**

```python
class OpenCVInpaintingBackend:
    def load(self) -> bool:
        if self._loaded:
            return True
        self._loaded = self.image_inpainter.load_model()
        return self._loaded
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_ai_handler_opencv_backend_load_once.py -q`
Expected: PASS，且日志不再逐帧刷 `Loading lightweight image inpainting model...`。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/core/ai/ai_handler.py src/app/core/ai/inpainting_backends/opencv_backend.py src/app/core/ai/image_inpainter.py tests/unit/test_ai_handler_opencv_backend_load_once.py
git commit -m "perf(ai-core): 修复opencv后端重复加载"
```

### Task 5: 前置 LaMa 可用性与默认后端选择

**Files:**
- Modify: `src/app/ui/main_window.py`
- Modify: `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Test: `tests/unit/test_inpainting_backend_selection.py`
- Test: `tests/unit/test_lama_backend_runtime_fallback.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_default_ui_backend_falls_back_to_opencv_when_lama_missing():
    params = runtime_defaults_without_lama()
    assert params["requested_inpainting_backend"] == "opencv"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_inpainting_backend_selection.py tests/unit/test_lama_backend_runtime_fallback.py -q`
Expected: FAIL，默认值仍然优先选择 LaMa。

**Step 3: Write minimal implementation**

```python
if not lama_asset_available:
    default_inpainting_method = "TELEA 快速修复 (OpenCV)"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_inpainting_backend_selection.py tests/unit/test_lama_backend_runtime_fallback.py -q`
Expected: PASS，默认值与真实可用 backend 一致。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/ui/main_window.py src/app/ui/widgets/advanced/advanced_parameters_widget.py src/app/core/ai/ai_handler.py tests/unit/test_inpainting_backend_selection.py tests/unit/test_lama_backend_runtime_fallback.py
git commit -m "perf(video-runtime): 前置lama可用性判定"
```

### Task 6: 接入批量检测并收敛尾部开销

**Files:**
- Modify: `src/app/core/ai/yolo_detector.py`
- Modify: `src/app/core/video/modes/pipeline.py`
- Modify: `src/app/core/video/modes/single_process.py`
- Modify: `src/app/core/audio/ffmpeg_audio_processor.py`
- Test: `tests/integration/test_yolo_detector.py`
- Test: `tests/unit/test_preserve_audio_runtime.py`

**Step 1: Write the failing test (@superpowers:test-driven-development)**

```python
def test_pipeline_uses_detect_batch(monkeypatch):
    process_video_pipeline(processor)
    assert detect_batch_calls > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_yolo_detector.py tests/unit/test_preserve_audio_runtime.py -q`
Expected: FAIL，默认视频链路未命中 `detect_batch()`，且 `preserve_audio` 不生效。

**Step 3: Write minimal implementation**

```python
batch_masks = detector.detect_batch(batch_frames)
if not preserve_audio:
    return copy_video_without_audio(...)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_yolo_detector.py tests/unit/test_preserve_audio_runtime.py -q`
Expected: PASS，批量检测接线成功，音频保留开关开始生效。

**Step 5: Commit（仅在获得用户确认后执行）**

```bash
git add src/app/core/ai/yolo_detector.py src/app/core/video/modes/pipeline.py src/app/core/video/modes/single_process.py src/app/core/audio/ffmpeg_audio_processor.py tests/integration/test_yolo_detector.py tests/unit/test_preserve_audio_runtime.py
git commit -m "perf(video-core): 接入批量检测并收敛尾部开销"
```
