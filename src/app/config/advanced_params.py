#!/usr/bin/env python3
"""
统一高级性能参数模型。
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from dataclasses import replace as dataclass_replace
from pathlib import Path
from typing import Any, Mapping

EXPLICIT_PROCESSING_MODE_OPTIONS = ("single_process", "multiprocess", "pipeline")
PROCESSING_MODE_OPTIONS = ("auto", *EXPLICIT_PROCESSING_MODE_OPTIONS)
PROCESSING_MODE_UI_OPTIONS = EXPLICIT_PROCESSING_MODE_OPTIONS
PROCESSING_MODE_LABELS = {
    "auto": "自动",
    "single_process": "单进程",
    "multiprocess": "多进程分块",
    "pipeline": "流水线",
}
MODE_RESTRICTION_REASON_LABELS = {
    "gpu_deep_backend_serial_only": "GPU 深度修复仅支持串行，已自动切换为单进程",
}
PROCESSING_MODE_LABEL_TO_VALUE = {
    **{value: key for key, value in PROCESSING_MODE_LABELS.items()},
    "多进程": "multiprocess",
}
OUTPUT_FORMAT_OPTIONS = ("keep", "jpg", "png", "bmp", "tiff")
OUTPUT_FORMAT_LABELS = {
    "keep": "保持原格式",
    "jpg": "JPG",
    "png": "PNG",
    "bmp": "BMP",
    "tiff": "TIFF",
}
OUTPUT_FORMAT_LABEL_TO_VALUE = {
    **{value: key for key, value in OUTPUT_FORMAT_LABELS.items()},
    "jpeg": "jpg",
}
_DEFAULT_AUTO_WORKER_COUNT = 4
_GPU_DEEP_BACKENDS = {"lama", "mat"}
MASK_TRACKING_MAX_MISSING_DETECTIONS_MAX = 30
MASK_TRACKING_SCENE_SHIFT_CONFIRMATION_FRAMES_MAX = 30
_VIDEO_FILE_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
}


def _normalize_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _normalize_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = default
    return max(minimum, min(maximum, normalized))


def _normalize_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        normalized = default
    return max(minimum, min(maximum, normalized))


def _get_first_present_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def normalize_processing_mode(value: Any) -> str:
    normalized = str(value or "").strip()
    if normalized in PROCESSING_MODE_OPTIONS:
        return normalized

    lowered = normalized.lower()
    if lowered in PROCESSING_MODE_OPTIONS:
        return lowered

    if normalized in PROCESSING_MODE_LABEL_TO_VALUE:
        return PROCESSING_MODE_LABEL_TO_VALUE[normalized]
    if lowered in PROCESSING_MODE_LABEL_TO_VALUE:
        return PROCESSING_MODE_LABEL_TO_VALUE[lowered]

    aliases = {
        "single": "single_process",
        "singleprocess": "single_process",
        "single-process": "single_process",
        "multi": "multiprocess",
        "multiprocessing": "multiprocess",
        "multiprocesschunk": "multiprocess",
        "chunk": "multiprocess",
    }
    compact = lowered.replace("_", "").replace("-", "").replace(" ", "")
    return aliases.get(compact, "auto")


def processing_mode_to_label(value: str) -> str:
    return PROCESSING_MODE_LABELS.get(
        normalize_processing_mode(value), PROCESSING_MODE_LABELS["auto"]
    )


def mode_restriction_reason_to_label(value: Any) -> str:
    """将运行模式限制原因转换为用户可读文案。"""
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return MODE_RESTRICTION_REASON_LABELS.get(normalized, normalized)


def build_processing_mode_runtime_summary(
    *,
    requested_mode: Any,
    resolved_mode: Any,
) -> str:
    """构建运行模式摘要文案。"""
    normalized_requested = normalize_processing_mode(requested_mode)
    normalized_resolved = normalize_processing_mode(resolved_mode)

    has_requested = str(requested_mode or "").strip() != ""
    has_resolved = str(resolved_mode or "").strip() != ""
    if not has_requested and not has_resolved:
        return "运行模式：--"

    if not has_resolved:
        return f"运行模式：{processing_mode_to_label(normalized_requested)}"

    resolved_label = processing_mode_to_label(normalized_resolved)
    if has_requested and normalized_requested != normalized_resolved:
        requested_label = processing_mode_to_label(normalized_requested)
        return f"运行模式：请求{requested_label}，实际{resolved_label}"
    return f"运行模式：{resolved_label}"


def build_processing_mode_runtime_hint(reason: Any) -> str:
    """构建运行模式提示文案。"""
    label = mode_restriction_reason_to_label(reason)
    if not label:
        return ""
    return f"提示：{label}"


def _normalize_worker_count(value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = 0
    if normalized < 0:
        return 0
    return min(16, normalized)


def _normalize_compression_quality(value: Any, default: int) -> int:
    return _normalize_int(value, default, 1, 100)


def normalize_output_format(value: Any) -> str:
    normalized = str(value or "").strip()
    if normalized in OUTPUT_FORMAT_OPTIONS:
        return normalized

    lowered = normalized.lower()
    if lowered in OUTPUT_FORMAT_OPTIONS:
        return lowered

    if normalized in OUTPUT_FORMAT_LABEL_TO_VALUE:
        return OUTPUT_FORMAT_LABEL_TO_VALUE[normalized]
    if lowered in OUTPUT_FORMAT_LABEL_TO_VALUE:
        return OUTPUT_FORMAT_LABEL_TO_VALUE[lowered]

    return "keep"


def output_format_to_label(value: Any) -> str:
    return OUTPUT_FORMAT_LABELS.get(normalize_output_format(value), OUTPUT_FORMAT_LABELS["keep"])


def _resolve_auto_worker_count() -> int:
    cpu_count = os.cpu_count() or _DEFAULT_AUTO_WORKER_COUNT
    return max(1, min(cpu_count, _DEFAULT_AUTO_WORKER_COUNT))


def _normalize_cpu_count(value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = os.cpu_count() or _DEFAULT_AUTO_WORKER_COUNT
    return max(1, normalized)


def _looks_like_video_input(input_file_path: str | None) -> bool:
    if not input_file_path:
        return False
    return Path(str(input_file_path)).suffix.lower() in _VIDEO_FILE_EXTENSIONS


def _resolve_mode_restriction_reason(
    *,
    requested_inpainting_backend: Any,
    use_gpu_inpainting: Any,
) -> str | None:
    normalized_backend = str(requested_inpainting_backend or "").strip().lower()
    if _normalize_bool(use_gpu_inpainting, False) and normalized_backend in _GPU_DEEP_BACKENDS:
        return "gpu_deep_backend_serial_only"
    return None


def _apply_mode_restriction(
    *,
    resolved_processing_mode: str,
    worker_count: int,
    enable_multiprocess: bool,
    use_pipeline: bool,
    requested_inpainting_backend: Any,
    use_gpu_inpainting: Any,
) -> tuple[str, int, bool, bool, str | None]:
    reason = _resolve_mode_restriction_reason(
        requested_inpainting_backend=requested_inpainting_backend,
        use_gpu_inpainting=use_gpu_inpainting,
    )
    if reason and resolved_processing_mode in {"multiprocess", "pipeline"}:
        return ("single_process", 1, False, False, reason)
    return (
        resolved_processing_mode,
        worker_count,
        enable_multiprocess,
        use_pipeline,
        None,
    )


def migrate_legacy_performance_preferences(  # noqa: C901
    *,
    current: Mapping[str, Any] | None = None,
    advanced: Mapping[str, Any] | None = None,
    batch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """将旧结构中的性能参数迁移到统一字段。"""
    normalized_current = dict(current or {})
    normalized_advanced = dict(advanced or {})
    normalized_batch = dict(batch or {})

    result: dict[str, Any] = {}

    processing_mode = normalized_current.get("processing_mode")
    if processing_mode is None:
        use_pipeline = _normalize_bool(normalized_current.get("use_pipeline"), False)
        enable_multiprocess = _normalize_bool(
            normalized_current.get("enable_multiprocess"),
            use_pipeline,
        )
        if use_pipeline:
            processing_mode = "pipeline"
        elif enable_multiprocess:
            processing_mode = "multiprocess"
    if processing_mode is not None:
        result["processing_mode"] = processing_mode

    worker_count = normalized_current.get("worker_count", normalized_current.get("thread_count"))
    if worker_count is None:
        worker_count = normalized_advanced.get("max_threads")
    if worker_count is not None:
        result["worker_count"] = worker_count

    enable_gpu = normalized_current.get("enable_gpu", normalized_advanced.get("enable_gpu"))
    if enable_gpu is not None:
        result["enable_gpu"] = enable_gpu

    gpu_memory_limit_mb = normalized_current.get(
        "gpu_memory_limit_mb",
        normalized_current.get("gpu_memory_limit"),
    )
    if gpu_memory_limit_mb is not None:
        result["gpu_memory_limit_mb"] = gpu_memory_limit_mb

    enable_cache = normalized_current.get("enable_cache")
    if enable_cache is not None:
        result["enable_cache"] = enable_cache

    cache_size_mb = normalized_current.get("cache_size_mb", normalized_current.get("cache_size"))
    if cache_size_mb is None:
        cache_size_mb = normalized_advanced.get("cache_size_mb")
    if cache_size_mb is not None:
        result["cache_size_mb"] = cache_size_mb

    batch_max_concurrent_files = normalized_current.get(
        "batch_max_concurrent_files",
        normalized_batch.get("max_concurrent_files"),
    )
    if batch_max_concurrent_files is not None:
        result["batch_max_concurrent_files"] = batch_max_concurrent_files

    batch_auto_retry_failed = normalized_current.get(
        "batch_auto_retry_failed",
        normalized_batch.get("auto_retry_failed"),
    )
    if batch_auto_retry_failed is not None:
        result["batch_auto_retry_failed"] = batch_auto_retry_failed

    batch_max_retry_count = normalized_current.get(
        "batch_max_retry_count",
        normalized_batch.get("max_retry_count"),
    )
    if batch_max_retry_count is not None:
        result["batch_max_retry_count"] = batch_max_retry_count

    output_format = normalized_current.get("output_format")
    if output_format is not None:
        result["output_format"] = output_format

    compression_quality = normalized_current.get("compression_quality")
    if compression_quality is not None:
        result["compression_quality"] = compression_quality

    add_suffix = normalized_current.get("add_suffix")
    if add_suffix is not None:
        result["add_suffix"] = add_suffix

    add_timestamp = normalized_current.get("add_timestamp")
    if add_timestamp is not None:
        result["add_timestamp"] = add_timestamp

    preserve_audio = normalized_current.get("preserve_audio")
    if preserve_audio is not None:
        result["preserve_audio"] = preserve_audio

    mask_tracking_max_missing_detections = normalized_current.get(
        "mask_tracking_max_missing_detections",
        normalized_current.get("mask_tracking_max_missed_detections"),
    )
    if mask_tracking_max_missing_detections is not None:
        result["mask_tracking_max_missing_detections"] = mask_tracking_max_missing_detections

    mask_tracking_motion_iou_threshold = normalized_current.get(
        "mask_tracking_motion_iou_threshold",
        normalized_current.get(
            "mask_tracking_scene_change_iou_threshold",
            normalized_current.get("mask_tracking_scene_shift_iou_threshold"),
        ),
    )
    if mask_tracking_motion_iou_threshold is not None:
        result["mask_tracking_motion_iou_threshold"] = mask_tracking_motion_iou_threshold

    mask_tracking_scene_shift_confirmation_frames = normalized_current.get(
        "mask_tracking_scene_shift_confirmation_frames"
    )
    if mask_tracking_scene_shift_confirmation_frames is not None:
        result[
            "mask_tracking_scene_shift_confirmation_frames"
        ] = mask_tracking_scene_shift_confirmation_frames

    return result


@dataclass(frozen=True)
class ProcessingContext:
    """运行时性能参数解析上下文。"""

    input_file_path: str | None = None
    is_batch: bool = False
    prefer_pipeline: bool = True
    cpu_count: int = _DEFAULT_AUTO_WORKER_COUNT
    gpu_enabled: bool = True
    requested_inpainting_backend: str = "opencv"
    use_gpu_inpainting: bool = False

    def normalized_cpu_count(self) -> int:
        return _normalize_cpu_count(self.cpu_count)

    @property
    def is_video_input(self) -> bool:
        return _looks_like_video_input(self.input_file_path)


@dataclass(frozen=True)
class ResolvedPerformanceConfig:
    """解析后的统一运行时性能配置。"""

    requested_processing_mode: str
    resolved_processing_mode: str
    worker_count: int
    enable_multiprocess: bool
    use_pipeline: bool
    gpu_memory_budget_mb: int
    enable_cache: bool
    cache_size_mb: int
    batch_max_concurrent_files: int
    batch_auto_retry_failed: bool
    batch_max_retry_count: int
    mode_restriction_reason: str | None = None

    @classmethod
    def from_runtime_sources(
        cls,
        *,
        ai_params: Mapping[str, Any] | None = None,
        batch_config: Mapping[str, Any] | None = None,
    ) -> "ResolvedPerformanceConfig":
        """根据运行时导出字段重建统一配置对象。"""
        normalized_ai_params = dict(ai_params or {})
        normalized_batch_config = dict(batch_config or {})

        requested_processing_mode = normalize_processing_mode(
            normalized_ai_params.get("processing_mode")
        )
        use_pipeline = _normalize_bool(normalized_ai_params.get("use_pipeline"), False)
        enable_multiprocess = _normalize_bool(
            normalized_ai_params.get("enable_multiprocess"),
            use_pipeline,
        )

        resolved_processing_mode = normalize_processing_mode(
            normalized_ai_params.get("resolved_processing_mode")
        )
        if resolved_processing_mode == "auto":
            if use_pipeline:
                resolved_processing_mode = "pipeline"
            elif enable_multiprocess:
                resolved_processing_mode = "multiprocess"
            elif requested_processing_mode != "auto":
                resolved_processing_mode = requested_processing_mode
            else:
                resolved_processing_mode = "single_process"

        worker_count = _normalize_worker_count(
            normalized_ai_params.get(
                "num_processes",
                normalized_ai_params.get("worker_count", 1),
            )
        )
        if resolved_processing_mode == "single_process":
            worker_count = 1
        elif worker_count <= 0:
            worker_count = _resolve_auto_worker_count()

        (
            resolved_processing_mode,
            worker_count,
            enable_multiprocess,
            use_pipeline,
            mode_restriction_reason,
        ) = _apply_mode_restriction(
            resolved_processing_mode=resolved_processing_mode,
            worker_count=worker_count,
            enable_multiprocess=enable_multiprocess,
            use_pipeline=use_pipeline,
            requested_inpainting_backend=normalized_ai_params.get("requested_inpainting_backend"),
            use_gpu_inpainting=normalized_ai_params.get("use_gpu_inpainting"),
        )

        return cls(
            requested_processing_mode=requested_processing_mode,
            resolved_processing_mode=resolved_processing_mode,
            worker_count=worker_count,
            enable_multiprocess=enable_multiprocess,
            use_pipeline=use_pipeline,
            gpu_memory_budget_mb=_normalize_int(
                normalized_ai_params.get("gpu_memory_mb", 2048),
                2048,
                256,
                32768,
            ),
            enable_cache=_normalize_bool(normalized_ai_params.get("enable_cache"), True),
            cache_size_mb=_normalize_int(
                normalized_ai_params.get("cache_size_mb", 512),
                512,
                64,
                8192,
            ),
            batch_max_concurrent_files=_normalize_int(
                normalized_batch_config.get("max_concurrent_files", 1),
                1,
                1,
                16,
            ),
            batch_auto_retry_failed=_normalize_bool(
                normalized_batch_config.get("auto_retry_failed"),
                True,
            ),
            batch_max_retry_count=_normalize_int(
                normalized_batch_config.get("max_retry_count", 3),
                3,
                0,
                10,
            ),
            mode_restriction_reason=mode_restriction_reason,
        )

    def to_ai_params(self) -> dict[str, Any]:
        return {
            "processing_mode": self.requested_processing_mode,
            "resolved_processing_mode": self.resolved_processing_mode,
            "enable_multiprocess": self.enable_multiprocess,
            "use_pipeline": self.use_pipeline,
            "num_processes": self.worker_count,
            "gpu_memory_mb": self.gpu_memory_budget_mb,
            "enable_cache": self.enable_cache,
            "cache_size_mb": self.cache_size_mb,
            "mode_restriction_reason": self.mode_restriction_reason,
        }

    def to_batch_config(self) -> dict[str, Any]:
        return {
            "max_concurrent_files": self.batch_max_concurrent_files,
            "auto_retry_failed": self.batch_auto_retry_failed,
            "max_retry_count": self.batch_max_retry_count,
        }

    def to_manifest_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_trace_dict(self) -> dict[str, Any]:
        return self.to_manifest_dict()


@dataclass(frozen=True)
class ResolvedOutputConfig:
    """解析后的统一输出配置。"""

    output_format: str
    compression_quality: int
    add_suffix: bool
    add_timestamp: bool
    preserve_audio: bool

    def to_ai_params(self) -> dict[str, Any]:
        return {
            "output_format": self.output_format,
            "compression_quality": self.compression_quality,
            "add_suffix": self.add_suffix,
            "add_timestamp": self.add_timestamp,
            "preserve_audio": self.preserve_audio,
        }

    def to_ui_dict(self) -> dict[str, Any]:
        return {
            "output_format": output_format_to_label(self.output_format),
            "compression_quality": self.compression_quality,
            "add_suffix": self.add_suffix,
            "add_timestamp": self.add_timestamp,
            "preserve_audio": self.preserve_audio,
        }


@dataclass(frozen=True)
class AdvancedParamsSnapshot:
    """统一高级参数快照。"""

    processing_mode: str = "single_process"
    worker_count: int = 0
    enable_gpu: bool = True
    gpu_memory_limit_mb: int = 2048
    enable_cache: bool = True
    cache_size_mb: int = 512
    batch_max_concurrent_files: int = 1
    batch_auto_retry_failed: bool = True
    batch_max_retry_count: int = 3
    output_format: str = "keep"
    compression_quality: int = 85
    add_suffix: bool = True
    add_timestamp: bool = False
    preserve_audio: bool = True
    mask_tracking_max_missing_detections: int = 1
    mask_tracking_motion_iou_threshold: float = 0.2
    mask_tracking_scene_shift_confirmation_frames: int = 1

    @classmethod
    def defaults(cls) -> "AdvancedParamsSnapshot":
        return cls()

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any] | None = None) -> "AdvancedParamsSnapshot":
        merged = migrate_legacy_performance_preferences(current=raw)
        raw_mapping = dict(raw or {})
        defaults = cls.defaults()
        return cls(
            processing_mode=normalize_processing_mode(
                merged.get("processing_mode", defaults.processing_mode)
            ),
            worker_count=_normalize_worker_count(merged.get("worker_count", defaults.worker_count)),
            enable_gpu=_normalize_bool(merged.get("enable_gpu"), defaults.enable_gpu),
            gpu_memory_limit_mb=_normalize_int(
                merged.get("gpu_memory_limit_mb", defaults.gpu_memory_limit_mb),
                defaults.gpu_memory_limit_mb,
                256,
                32768,
            ),
            enable_cache=_normalize_bool(merged.get("enable_cache"), defaults.enable_cache),
            cache_size_mb=_normalize_int(
                merged.get("cache_size_mb", defaults.cache_size_mb),
                defaults.cache_size_mb,
                64,
                8192,
            ),
            batch_max_concurrent_files=_normalize_int(
                merged.get(
                    "batch_max_concurrent_files",
                    defaults.batch_max_concurrent_files,
                ),
                defaults.batch_max_concurrent_files,
                1,
                16,
            ),
            batch_auto_retry_failed=_normalize_bool(
                merged.get("batch_auto_retry_failed"),
                defaults.batch_auto_retry_failed,
            ),
            batch_max_retry_count=_normalize_int(
                merged.get("batch_max_retry_count", defaults.batch_max_retry_count),
                defaults.batch_max_retry_count,
                0,
                10,
            ),
            output_format=normalize_output_format(
                merged.get("output_format", defaults.output_format)
            ),
            compression_quality=_normalize_compression_quality(
                merged.get("compression_quality", defaults.compression_quality),
                defaults.compression_quality,
            ),
            add_suffix=_normalize_bool(
                merged.get("add_suffix", defaults.add_suffix),
                defaults.add_suffix,
            ),
            add_timestamp=_normalize_bool(
                merged.get("add_timestamp"),
                defaults.add_timestamp,
            ),
            preserve_audio=_normalize_bool(
                merged.get("preserve_audio"),
                defaults.preserve_audio,
            ),
            mask_tracking_max_missing_detections=_normalize_int(
                _get_first_present_value(
                    raw_mapping,
                    "mask_tracking_max_missing_detections",
                    "mask_tracking_max_missed_detections",
                ),
                defaults.mask_tracking_max_missing_detections,
                0,
                MASK_TRACKING_MAX_MISSING_DETECTIONS_MAX,
            ),
            mask_tracking_motion_iou_threshold=_normalize_float(
                _get_first_present_value(
                    raw_mapping,
                    "mask_tracking_motion_iou_threshold",
                    "mask_tracking_scene_change_iou_threshold",
                    "mask_tracking_scene_shift_iou_threshold",
                ),
                defaults.mask_tracking_motion_iou_threshold,
                0.0,
                1.0,
            ),
            mask_tracking_scene_shift_confirmation_frames=_normalize_int(
                _get_first_present_value(
                    raw_mapping,
                    "mask_tracking_scene_shift_confirmation_frames",
                ),
                defaults.mask_tracking_scene_shift_confirmation_frames,
                1,
                MASK_TRACKING_SCENE_SHIFT_CONFIRMATION_FRAMES_MAX,
            ),
        )

    def replace(self, **changes: Any) -> "AdvancedParamsSnapshot":
        return dataclass_replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_ui_dict(self) -> dict[str, Any]:
        params = self.to_dict()
        params["output_format"] = output_format_to_label(self.output_format)
        return params

    def _default_processing_context(self) -> ProcessingContext:
        return ProcessingContext(
            input_file_path=None,
            is_batch=False,
            prefer_pipeline=True,
            cpu_count=os.cpu_count() or _DEFAULT_AUTO_WORKER_COUNT,
            gpu_enabled=self.enable_gpu,
        )

    def resolve_processing_mode(self, context: ProcessingContext | None = None) -> str:
        current_context = context or self._default_processing_context()
        if self.processing_mode != "auto":
            return self.processing_mode
        if not current_context.is_video_input:
            return "single_process"
        if current_context.normalized_cpu_count() <= 2:
            return "single_process"
        if current_context.prefer_pipeline or current_context.is_batch:
            return "pipeline"
        return "single_process"

    def resolve_worker_count(self, context: ProcessingContext | None = None) -> int:
        resolved_mode = self.resolve_processing_mode(context)
        if resolved_mode == "single_process":
            return 1
        if self.worker_count > 0:
            return self.worker_count
        return _resolve_auto_worker_count()

    def resolve(
        self,
        context: ProcessingContext | None = None,
    ) -> ResolvedPerformanceConfig:
        current_context = context or self._default_processing_context()
        resolved_mode = self.resolve_processing_mode(current_context)
        resolved_worker_count = self.resolve_worker_count(current_context)
        enable_multiprocess = resolved_mode in {"multiprocess", "pipeline"}
        use_pipeline = resolved_mode == "pipeline"
        (
            resolved_mode,
            resolved_worker_count,
            enable_multiprocess,
            use_pipeline,
            mode_restriction_reason,
        ) = _apply_mode_restriction(
            resolved_processing_mode=resolved_mode,
            worker_count=resolved_worker_count,
            enable_multiprocess=enable_multiprocess,
            use_pipeline=use_pipeline,
            requested_inpainting_backend=current_context.requested_inpainting_backend,
            use_gpu_inpainting=current_context.use_gpu_inpainting,
        )
        return ResolvedPerformanceConfig(
            requested_processing_mode=self.processing_mode,
            resolved_processing_mode=resolved_mode,
            worker_count=resolved_worker_count,
            enable_multiprocess=enable_multiprocess,
            use_pipeline=use_pipeline,
            gpu_memory_budget_mb=self.gpu_memory_limit_mb,
            enable_cache=self.enable_cache,
            cache_size_mb=self.cache_size_mb,
            batch_max_concurrent_files=self.batch_max_concurrent_files,
            batch_auto_retry_failed=self.batch_auto_retry_failed,
            batch_max_retry_count=self.batch_max_retry_count,
            mode_restriction_reason=mode_restriction_reason,
        )

    def to_ai_params(self, context: ProcessingContext | None = None) -> dict[str, Any]:
        return self.resolve(context).to_ai_params()

    def to_batch_config(self, context: ProcessingContext | None = None) -> dict[str, Any]:
        return self.resolve(context).to_batch_config()

    def resolve_output_config(self) -> ResolvedOutputConfig:
        return ResolvedOutputConfig(
            output_format=self.output_format,
            compression_quality=self.compression_quality,
            add_suffix=self.add_suffix,
            add_timestamp=self.add_timestamp,
            preserve_audio=self.preserve_audio,
        )


__all__ = [
    "AdvancedParamsSnapshot",
    "MASK_TRACKING_MAX_MISSING_DETECTIONS_MAX",
    "MASK_TRACKING_SCENE_SHIFT_CONFIRMATION_FRAMES_MAX",
    "OUTPUT_FORMAT_LABELS",
    "OUTPUT_FORMAT_OPTIONS",
    "ProcessingContext",
    "MODE_RESTRICTION_REASON_LABELS",
    "PROCESSING_MODE_LABELS",
    "PROCESSING_MODE_OPTIONS",
    "PROCESSING_MODE_UI_OPTIONS",
    "ResolvedOutputConfig",
    "ResolvedPerformanceConfig",
    "build_processing_mode_runtime_hint",
    "build_processing_mode_runtime_summary",
    "migrate_legacy_performance_preferences",
    "mode_restriction_reason_to_label",
    "normalize_output_format",
    "normalize_processing_mode",
    "output_format_to_label",
    "processing_mode_to_label",
]
