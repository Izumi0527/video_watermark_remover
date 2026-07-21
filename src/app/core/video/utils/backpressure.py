#!/usr/bin/env python3
"""
背压控制器模块

提供精确的生产者-消费者背压控制：
1. 基于 Condition 变量的精确等待/唤醒
2. 高低水位线控制
3. 避免轮询浪费CPU

"""

import sys
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class QueueBudget:
    """流水线运行时缓冲预算。"""

    frame_queue_size: int
    result_queue_size: int
    writer_buffer_size: int
    requested_worker_count: int
    effective_worker_count: int
    pipeline_viable: bool
    estimated_total_memory_mb: float
    minimum_viable_memory_mb: float


@dataclass(frozen=True)
class RuntimeModeConstraint:
    """运行模式的资源约束解析结果。"""

    requested_worker_count: int
    effective_worker_count: int
    pipeline_allowed: bool
    deep_gpu_backend: bool
    reserved_memory_mb: int
    serialization_overhead_factor: float
    reason: Optional[str] = None


_DEEP_GPU_BACKENDS = {"lama", "mat"}


def resolve_runtime_mode_constraint(
    *,
    ai_params: Optional[Mapping[str, Any]],
    requested_worker_count: int,
    platform_name: Optional[str] = None,
) -> RuntimeModeConstraint:
    """解析特定 AI 后端下的运行时约束。"""
    normalized_requested_workers = max(1, int(requested_worker_count or 1))
    normalized_platform = str(platform_name or sys.platform).lower()
    normalized_ai_params = dict(ai_params or {})
    requested_backend = (
        str(normalized_ai_params.get("requested_inpainting_backend", "") or "").strip().lower()
    )
    use_gpu_inpainting = bool(normalized_ai_params.get("use_gpu_inpainting", False))
    deep_gpu_backend = use_gpu_inpainting and requested_backend in _DEEP_GPU_BACKENDS

    if not deep_gpu_backend:
        return RuntimeModeConstraint(
            requested_worker_count=normalized_requested_workers,
            effective_worker_count=normalized_requested_workers,
            pipeline_allowed=True,
            deep_gpu_backend=False,
            reserved_memory_mb=0,
            serialization_overhead_factor=1.0,
            reason=None,
        )

    gpu_memory_budget_mb = max(256, int(normalized_ai_params.get("gpu_memory_mb", 2048) or 2048))
    serialization_overhead_factor = 3.0 if normalized_platform.startswith("win") else 2.0
    reserved_memory_mb = max(256, min(gpu_memory_budget_mb // 2, 2048))

    return RuntimeModeConstraint(
        requested_worker_count=normalized_requested_workers,
        effective_worker_count=1,
        pipeline_allowed=False,
        deep_gpu_backend=True,
        reserved_memory_mb=reserved_memory_mb,
        serialization_overhead_factor=serialization_overhead_factor,
        reason="gpu_deep_backend_serial_only",
    )


def calculate_runtime_queue_budget(
    enable_cache: bool,
    cache_size_mb: int,
    frame_shape: tuple[int, int],
    requested_worker_count: int = 1,
    runtime_constraint: Optional[RuntimeModeConstraint] = None,
) -> QueueBudget:
    """根据缓存预算推导流水线队列与写入缓冲大小。"""
    constraint = runtime_constraint or RuntimeModeConstraint(
        requested_worker_count=max(1, int(requested_worker_count or 1)),
        effective_worker_count=max(1, int(requested_worker_count or 1)),
        pipeline_allowed=True,
        deep_gpu_backend=False,
        reserved_memory_mb=0,
        serialization_overhead_factor=1.0,
        reason=None,
    )
    if not constraint.pipeline_allowed:
        return QueueBudget(
            frame_queue_size=0,
            result_queue_size=0,
            writer_buffer_size=0,
            requested_worker_count=constraint.requested_worker_count,
            effective_worker_count=constraint.effective_worker_count,
            pipeline_viable=False,
            estimated_total_memory_mb=0.0,
            minimum_viable_memory_mb=0.0,
        )

    height, width = frame_shape[:2]
    frame_bytes = max(1, int(height) * int(width) * 3)
    frame_mb = max(1.0, frame_bytes / (1024 * 1024)) * max(
        1.0, float(constraint.serialization_overhead_factor)
    )
    normalized_cache_mb = max(64, int(cache_size_mb)) if enable_cache else 64
    normalized_cache_mb = max(64, normalized_cache_mb - int(constraint.reserved_memory_mb))
    normalized_requested_workers = max(1, int(constraint.effective_worker_count or 1))

    # 预算不仅要覆盖三个显式缓冲区，还要覆盖：
    # - 读取线程手上的 1 帧
    # - 每个 worker 在处理中的“输入帧 + 输出帧”两份在途数据
    reader_inflight_slots = 1
    worker_inflight_slots_per_worker = 2
    minimum_queue_slots = 3  # reader/result/writer 每段至少保留 1 个槽位
    minimum_viable_slots = (
        reader_inflight_slots + worker_inflight_slots_per_worker + minimum_queue_slots
    )
    minimum_viable_memory_mb = minimum_viable_slots * frame_mb

    total_buffer_slots = max(1, int(normalized_cache_mb / frame_mb))
    total_buffer_slots = min(total_buffer_slots, 240)

    available_worker_slots = total_buffer_slots - reader_inflight_slots - minimum_queue_slots
    if available_worker_slots < worker_inflight_slots_per_worker:
        return QueueBudget(
            frame_queue_size=0,
            result_queue_size=0,
            writer_buffer_size=0,
            requested_worker_count=constraint.requested_worker_count,
            effective_worker_count=0,
            pipeline_viable=False,
            estimated_total_memory_mb=0.0,
            minimum_viable_memory_mb=minimum_viable_memory_mb,
        )

    effective_worker_count = min(
        normalized_requested_workers,
        max(1, available_worker_slots // worker_inflight_slots_per_worker),
    )
    reserved_inflight_slots = reader_inflight_slots + (
        effective_worker_count * worker_inflight_slots_per_worker
    )
    distributable_queue_slots = max(
        minimum_queue_slots, total_buffer_slots - reserved_inflight_slots
    )

    frame_queue_size = max(1, min(80, distributable_queue_slots // 4))
    remaining_slots = max(2, distributable_queue_slots - frame_queue_size)
    result_queue_size = max(1, min(160, remaining_slots // 2))
    writer_buffer_size = max(
        1,
        min(160, distributable_queue_slots - frame_queue_size - result_queue_size),
    )
    total_estimated_slots = (
        reader_inflight_slots
        + (effective_worker_count * worker_inflight_slots_per_worker)
        + frame_queue_size
        + result_queue_size
        + writer_buffer_size
    )

    return QueueBudget(
        frame_queue_size=frame_queue_size,
        result_queue_size=result_queue_size,
        writer_buffer_size=writer_buffer_size,
        requested_worker_count=constraint.requested_worker_count,
        effective_worker_count=effective_worker_count,
        pipeline_viable=True,
        estimated_total_memory_mb=(total_estimated_slots * frame_mb),
        minimum_viable_memory_mb=minimum_viable_memory_mb,
    )


class BackpressureController:
    """
    背压控制器

    使用 Condition 变量实现精确的流量控制，
    避免固定 sleep 带来的性能损失。

    工作原理：
    - 当缓冲区达到 high_watermark 时，生产者阻塞等待
    - 当缓冲区降到 low_watermark 以下时，唤醒所有等待的生产者
    - 支持可选的超时机制，防止死锁
    """

    def __init__(
        self,
        high_watermark: int = 50,
        low_watermark: int = 25,
        timeout: Optional[float] = 5.0,
    ):
        """
        初始化背压控制器

        Args:
            high_watermark: 高水位线，达到此值时生产者阻塞
            low_watermark: 低水位线，降到此值时唤醒生产者
            timeout: 等待超时时间（秒），None 表示无限等待
        """
        if low_watermark >= high_watermark:
            raise ValueError("low_watermark must be less than high_watermark")

        self.high_watermark = high_watermark
        self.low_watermark = low_watermark
        self.timeout = timeout

        self._current_size = 0
        self._lock = threading.Lock()
        self._not_full = threading.Condition(self._lock)
        self._stopped = False

    @property
    def current_size(self) -> int:
        """当前缓冲区大小"""
        with self._lock:
            return self._current_size

    @property
    def is_full(self) -> bool:
        """缓冲区是否已满（达到高水位）"""
        with self._lock:
            return self._current_size >= self.high_watermark

    def acquire_slot(self) -> bool:
        """
        生产者：获取一个槽位

        如果缓冲区已满，会阻塞等待直到有空间。

        Returns:
            True 表示成功获取，False 表示已停止或超时
        """
        with self._not_full:
            # 等待直到有空间或被停止
            while self._current_size >= self.high_watermark and not self._stopped:
                # 使用 wait_for 简化条件检查
                notified = self._not_full.wait(timeout=self.timeout)
                if not notified and self._current_size >= self.high_watermark:
                    # 超时且仍然满
                    return False

            if self._stopped:
                return False

            self._current_size += 1
            return True

    def release_slot(self) -> None:
        """
        消费者：释放一个槽位

        如果缓冲区降到低水位以下，唤醒等待的生产者。
        """
        with self._not_full:
            self._current_size = max(0, self._current_size - 1)

            # 降到低水位时唤醒所有等待的生产者
            if self._current_size <= self.low_watermark:
                self._not_full.notify_all()

    def stop(self) -> None:
        """
        停止控制器，唤醒所有等待的线程
        """
        with self._not_full:
            self._stopped = True
            self._not_full.notify_all()

    def reset(self) -> None:
        """
        重置控制器状态
        """
        with self._not_full:
            self._current_size = 0
            self._stopped = False

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
        return False


class AdaptiveBackpressure(BackpressureController):
    """
    自适应背压控制器

    根据处理速率动态调整水位线，优化吞吐量。
    """

    def __init__(
        self,
        initial_high: int = 50,
        initial_low: int = 25,
        min_high: int = 10,
        max_high: int = 200,
        adjustment_interval: int = 100,
    ):
        """
        初始化自适应背压控制器

        Args:
            initial_high: 初始高水位线
            initial_low: 初始低水位线
            min_high: 最小高水位线
            max_high: 最大高水位线
            adjustment_interval: 调整间隔（处理帧数）
        """
        super().__init__(high_watermark=initial_high, low_watermark=initial_low)
        self.min_high = min_high
        self.max_high = max_high
        self.adjustment_interval = adjustment_interval

        self._acquire_count = 0
        self._wait_count = 0  # 发生等待的次数

    def acquire_slot(self) -> bool:
        """获取槽位，并记录等待情况"""
        was_full = self.is_full

        result = super().acquire_slot()

        if result:
            with self._lock:
                self._acquire_count += 1
                if was_full:
                    self._wait_count += 1

                # 定期调整水位线
                if self._acquire_count % self.adjustment_interval == 0:
                    self._adjust_watermarks()

        return result

    def _adjust_watermarks(self) -> None:
        """根据等待比例调整水位线"""
        wait_ratio = self._wait_count / self.adjustment_interval

        if wait_ratio > 0.3:
            # 等待过多，增加缓冲区
            new_high = min(self.high_watermark + 10, self.max_high)
        elif wait_ratio < 0.05:
            # 几乎不等待，减少缓冲区节省内存
            new_high = max(self.high_watermark - 5, self.min_high)
        else:
            # 保持不变
            new_high = self.high_watermark

        if new_high != self.high_watermark:
            self.high_watermark = new_high
            self.low_watermark = new_high // 2

        # 重置计数器
        self._wait_count = 0


__all__ = [
    "AdaptiveBackpressure",
    "BackpressureController",
    "QueueBudget",
    "RuntimeModeConstraint",
    "calculate_runtime_queue_budget",
    "resolve_runtime_mode_constraint",
]
