"""视频处理运行模式安全护栏。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from ...config.advanced_params import ResolvedPerformanceConfig, normalize_processing_mode
from .utils.backpressure import resolve_runtime_mode_constraint
from .utils.resource_pressure import is_resource_pressure_error


@dataclass(frozen=True)
class VideoRuntimeModeDecision:
    """视频运行模式护栏的最终决策。"""

    requested_mode: str
    effective_mode: str
    worker_count: int
    enable_multiprocess: bool
    use_pipeline: bool
    reason: Optional[str] = None

    def to_ai_params_overrides(self) -> dict[str, Any]:
        return {
            "resolved_processing_mode": self.effective_mode,
            "enable_multiprocess": self.enable_multiprocess,
            "use_pipeline": self.use_pipeline,
            "num_processes": self.worker_count,
            "runtime_processing_guard_reason": self.reason,
        }


def resolve_video_runtime_mode(
    ai_params: Mapping[str, Any] | None,
) -> VideoRuntimeModeDecision:
    """根据 AI 参数与资源约束收敛出最终安全运行模式。"""
    normalized_ai_params = dict(ai_params or {})
    runtime_config = ResolvedPerformanceConfig.from_runtime_sources(ai_params=normalized_ai_params)
    requested_mode = normalize_processing_mode(normalized_ai_params.get("processing_mode"))
    if requested_mode == "auto":
        if bool(normalized_ai_params.get("use_pipeline", False)):
            requested_mode = "pipeline"
        elif bool(normalized_ai_params.get("enable_multiprocess", False)):
            requested_mode = "multiprocess"
        else:
            requested_mode = normalize_processing_mode(runtime_config.resolved_processing_mode)
    constraint = resolve_runtime_mode_constraint(
        ai_params=normalized_ai_params,
        requested_worker_count=runtime_config.worker_count,
    )

    effective_mode = requested_mode
    worker_count = runtime_config.worker_count
    reason = None

    if requested_mode in {"multiprocess", "pipeline"} and (
        constraint.deep_gpu_backend or not constraint.pipeline_allowed
    ):
        effective_mode = "single_process"
        worker_count = 1
        reason = constraint.reason or "runtime_mode_constraint"
    else:
        worker_count = max(1, min(worker_count, constraint.effective_worker_count))
        if effective_mode == "single_process":
            worker_count = 1

    enable_multiprocess = effective_mode in {"multiprocess", "pipeline"}
    use_pipeline = effective_mode == "pipeline"
    return VideoRuntimeModeDecision(
        requested_mode=requested_mode,
        effective_mode=effective_mode,
        worker_count=worker_count,
        enable_multiprocess=enable_multiprocess,
        use_pipeline=use_pipeline,
        reason=reason,
    )


def is_resource_exhaustion_error(error: Exception | str | None) -> bool:
    """判断异常是否属于资源耗尽类错误。"""
    return is_resource_pressure_error(error)


__all__ = [
    "VideoRuntimeModeDecision",
    "is_resource_exhaustion_error",
    "resolve_video_runtime_mode",
]
