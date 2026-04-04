# 复杂检测与修复优化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不破坏现有默认稳定性的前提下，修复已确认缺陷，并分阶段提升复杂图片与复杂视频的检测精度、修复质量和时序一致性。

**Architecture:** 先修正现有正确性与能力声明问题，再在当前 `YOLO + OpenCV / LaMa + 视频模式护栏` 主链上分层引入 `MaskRefiner` 与 `TemporalCoordinator`。默认主路径保持轻量稳定，高质量视频能力作为后续实验模式独立演进。

**Tech Stack:** Python、PyQt6、OpenCV、NumPy、PyTorch、Ultralytics、FFmpeg、pytest

---

### Task 1: 修复多进程分块合并顺序

**Files:**
- Modify: `src/app/core/video/modes/multiprocess.py`
- Test: `tests/unit/core/video/test_multiprocess_chunk_merge_order.py`

**Step 1: Write the failing test**

```python
def test_merge_chunk_paths_uses_numeric_chunk_order():
    chunk_paths = [
        "chunk_0.mp4",
        "chunk_1.mp4",
        "chunk_10.mp4",
        "chunk_2.mp4",
    ]
    ordered = _sort_chunk_paths(chunk_paths)
    assert ordered == [
        "chunk_0.mp4",
        "chunk_1.mp4",
        "chunk_2.mp4",
        "chunk_10.mp4",
    ]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/video/test_multiprocess_chunk_merge_order.py -v`
Expected: FAIL，因为当前仍按字符串排序。

**Step 3: Write minimal implementation**

```python
def _extract_chunk_index(path: str) -> int:
    match = re.search(r"chunk_(\d+)", os.path.basename(path))
    return int(match.group(1)) if match else 10**9


def _sort_chunk_paths(chunk_paths: list[str]) -> list[str]:
    return sorted(chunk_paths, key=lambda item: (_extract_chunk_index(item), item))
```

并把原来的：

```python
chunk_paths.sort()
```

替换成：

```python
chunk_paths = _sort_chunk_paths(chunk_paths)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/video/test_multiprocess_chunk_merge_order.py -v`
Expected: PASS

**Step 5: Run focused regression**

Run: `pytest tests/integration/test_multiprocess_video.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add src/app/core/video/modes/multiprocess.py tests/unit/core/video/test_multiprocess_chunk_merge_order.py
git commit -m "fix(video-core): 修复多进程分块合并顺序"
```

### Task 2: 解耦 GPU 修复能力判断与 torch 预加载

**Files:**
- Modify: `src/app/ui/utils/ai_params_builder.py`
- Test: `tests/unit/test_inpainting_backend_selection.py`

**Step 1: Write the failing test**

在现有测试中补一组“未预加载 torch 但可显式探测 CUDA 能力”的用例：

```python
def test_builder_enables_lama_backend_without_torch_preload(monkeypatch):
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr("app.ui.utils.ai_params_builder.detect_cuda_available", lambda: True)
    params = _build_with_method("LaMa 深度学习修复（推荐）", enable_gpu=True)
    assert params["requested_inpainting_backend"] == "lama"
    assert params["use_gpu_inpainting"] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_inpainting_backend_selection.py -v`
Expected: FAIL，当前实现只看 `sys.modules["torch"]`。

**Step 3: Write minimal implementation**

```python
def detect_cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _is_cuda_available(self) -> bool:
    return detect_cuda_available()
```

保持异常安全，但不再依赖标准入口是否先 preload `torch`。

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_inpainting_backend_selection.py -v`
Expected: PASS

**Step 5: Run focused regression**

Run: `pytest tests/unit/test_dynamic_watermark_tracking.py tests/unit/test_ai_handler_gpu_runtime_fallback.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add src/app/ui/utils/ai_params_builder.py tests/unit/test_inpainting_backend_selection.py
git commit -m "fix(ai-config): 修复GPU修复能力判断对预加载的隐式依赖"
```

### Task 3: 修复批处理重试包装器测试契约漂移

**Files:**
- Modify: `tests/unit/test_batch_processor_preloaded_policy.py`
- Test: `tests/unit/test_batch_processor_preloaded_policy.py`

**Step 1: Write the failing test**

当前已有失败用例，保留并明确桩函数签名：

```python
def _fake_process_single_file(input_path: str, output_path: str, file_index: int, *, file_id=None):
    return (ProcessingStatus.FAILED, "首次失败", {"file_id": file_id})
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_batch_processor_preloaded_policy.py -v`
Expected: FAIL，旧桩函数不接受 `file_id`。

**Step 3: Write minimal implementation**

只更新测试桩签名与断言，确保门禁反映当前实现，而不是回退实现去兼容旧测试。

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_batch_processor_preloaded_policy.py -v`
Expected: PASS

**Step 5: Run focused regression**

Run: `pytest tests/unit/test_signal_handler_batch_manifest.py tests/unit/test_signal_handler_thread_mode_passthrough.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add tests/unit/test_batch_processor_preloaded_policy.py
git commit -m "test(batch): 修复批处理重试包装器测试契约"
```

### Task 4: 抽出复杂图片的 MaskRefiner

**Files:**
- Create: `src/app/core/ai/mask_refiner.py`
- Modify: `src/app/core/ai/yolo_detector.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Test: `tests/unit/core/ai/test_mask_refiner.py`
- Test: `tests/unit/test_yolo_detector_mask_refinement.py`

**Step 1: Write the failing test**

```python
def test_mask_refiner_preserves_hollow_logo_edges():
    refiner = MaskRefiner(profile="complex_logo")
    refined = refiner.refine(raw_mask, frame_shape=(1080, 1920, 3))
    assert refined.sum() >= raw_mask.sum()
    assert refined[center_y, center_x] == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/ai/test_mask_refiner.py -v`
Expected: FAIL，因为 `MaskRefiner` 尚不存在。

**Step 3: Write minimal implementation**

```python
class MaskRefiner:
    def __init__(self, profile: str = "default") -> None:
        self.profile = profile

    def refine(self, raw_mask: np.ndarray, frame_shape: tuple[int, ...]) -> np.ndarray:
        mask = np.asarray(raw_mask, dtype=np.uint8)
        # 第一版只做统一入口与保守形态学细化
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
```

并在 `YOLOWatermarkDetector` 中把现有 `_postprocess_mask()` 调整为委托 `MaskRefiner`。

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/ai/test_mask_refiner.py tests/unit/test_yolo_detector_mask_refinement.py -v`
Expected: PASS

**Step 5: Run focused regression**

Run: `pytest tests/unit/test_dynamic_watermark_tracking.py tests/unit/test_ai_handler_lama_batch_inpainting.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add src/app/core/ai/mask_refiner.py src/app/core/ai/yolo_detector.py src/app/core/ai/ai_handler.py tests/unit/core/ai/test_mask_refiner.py tests/unit/test_yolo_detector_mask_refinement.py
git commit -m "feat(ai-core): 新增复杂图片掩码细化层"
```

### Task 5: 引入视频时序协调器

**Files:**
- Create: `src/app/core/ai/temporal_coordinator.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `src/app/core/video/modes/single_process.py`
- Test: `tests/unit/core/ai/test_temporal_coordinator.py`
- Test: `tests/unit/test_dynamic_watermark_tracking.py`

**Step 1: Write the failing test**

```python
def test_temporal_coordinator_reuses_mask_between_keyframes():
    coordinator = TemporalCoordinator(keyframe_interval=3)
    first = coordinator.update(frame_index=0, detected_mask=mask_a)
    second = coordinator.update(frame_index=1, detected_mask=None)
    assert np.array_equal(first, second)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/ai/test_temporal_coordinator.py -v`
Expected: FAIL，因为 `TemporalCoordinator` 尚不存在。

**Step 3: Write minimal implementation**

```python
class TemporalCoordinator:
    def __init__(self, keyframe_interval: int = 3) -> None:
        self.keyframe_interval = max(1, keyframe_interval)
        self.last_mask: np.ndarray | None = None

    def should_detect(self, frame_index: int) -> bool:
        return frame_index % self.keyframe_interval == 0 or self.last_mask is None

    def update(self, frame_index: int, detected_mask: np.ndarray | None) -> np.ndarray | None:
        if detected_mask is not None:
            self.last_mask = detected_mask.copy()
        return None if self.last_mask is None else self.last_mask.copy()
```

第一版先替换“裸上一帧掩码复用”，不直接上光流。

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/ai/test_temporal_coordinator.py tests/unit/test_dynamic_watermark_tracking.py -v`
Expected: PASS

**Step 5: Run focused regression**

Run: `pytest tests/unit/core/video/test_single_process_batch_detection.py tests/unit/core/video/test_runtime_guard.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add src/app/core/ai/temporal_coordinator.py src/app/core/ai/ai_handler.py src/app/core/video/modes/single_process.py tests/unit/core/ai/test_temporal_coordinator.py tests/unit/test_dynamic_watermark_tracking.py
git commit -m "feat(video-ai): 引入关键帧检测与掩码时序协调器"
```

### Task 6: 增加复杂场景指标与基线

**Files:**
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `src/app/core/video/modes/single_process.py`
- Create: `tests/integration/runtime/test_complex_media_baseline.py`
- Create: `docs/plans/2026-04-04-complex-media-baseline-notes.md`

**Step 1: Write the failing test**

```python
def test_processing_info_contains_temporal_quality_fields():
    info = handler._create_processing_info(frame)
    assert "temporal_flicker_score" in info
    assert "residual_watermark_score" in info
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/runtime/test_complex_media_baseline.py -v`
Expected: FAIL，因为新字段与基线记录尚未加入。

**Step 3: Write minimal implementation**

```python
processing_info.update(
    {
        "temporal_flicker_score": None,
        "residual_watermark_score": None,
        "runtime_fps": None,
        "peak_gpu_memory_mb": None,
    }
)
```

第一版先把字段与采样入口建起来，不先做复杂评估器。

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/runtime/test_complex_media_baseline.py -v`
Expected: PASS

**Step 5: Run focused regression**

Run: `pytest tests/unit/test_processing_info_backend_trace.py tests/unit/core/video/test_single_process_runtime_observability.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add src/app/core/ai/ai_handler.py src/app/core/video/modes/single_process.py tests/integration/runtime/test_complex_media_baseline.py docs/plans/2026-04-04-complex-media-baseline-notes.md
git commit -m "feat(observability): 增加复杂媒体优化基线观测字段"
```

### Task 7: 预留实验性高质量视频模式扩展位

**Files:**
- Modify: `src/app/core/ai/inpainting_backends/factory.py`
- Modify: `src/app/core/ai/ai_handler.py`
- Modify: `src/app/config/advanced_params.py`
- Create: `docs/plans/2026-04-04-experimental-video-hq-mode-notes.md`
- Test: `tests/unit/test_inpainting_backend_selection.py`

**Step 1: Write the failing test**

```python
def test_factory_marks_experimental_video_backend_as_unavailable_but_known():
    backend = create_inpainting_backend("video_hq_experimental", config=None, torch_device="cpu")
    assert backend.backend_id == "opencv"
    assert backend.get_last_trace()["requested_backend"] == "video_hq_experimental"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_inpainting_backend_selection.py -v`
Expected: FAIL，因为当前没有显式“已知但未实现”的实验后端语义。

**Step 3: Write minimal implementation**

```python
KNOWN_EXPERIMENTAL_BACKENDS = {"video_hq_experimental"}
```

对工厂做显式识别和 trace 标记，但不真正接入沉重模型。

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_inpainting_backend_selection.py -v`
Expected: PASS

**Step 5: Run focused regression**

Run: `pytest tests/unit/test_ai_handler_gpu_runtime_fallback.py tests/unit/test_processing_info_backend_trace.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add src/app/core/ai/inpainting_backends/factory.py src/app/core/ai/ai_handler.py src/app/config/advanced_params.py tests/unit/test_inpainting_backend_selection.py docs/plans/2026-04-04-experimental-video-hq-mode-notes.md
git commit -m "feat(ai-core): 预留实验性高质量视频模式扩展位"
```

---

Plan complete and saved to `docs/plans/2026-04-04-complex-detection-repair-optimization.md`. Two execution options:

**1. Subagent-Driven (this session)** - 我在当前会话按任务逐项推进，边做边验证，适合现在立刻开始。

**2. Parallel Session (separate)** - 你开一个新会话，按该计划配合 `executing-plans` 技能批量执行，适合长任务。

Which approach?
