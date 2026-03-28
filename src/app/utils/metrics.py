#!/usr/bin/env python3
"""
性能监控指标模块

Phase 6 新增: 提供视频处理性能监控和指标收集功能

主要功能：
1. 处理速度跟踪（FPS、处理时间）
2. 内存使用监控
3. GPU 利用率监控（如果可用）
4. 队列深度和背压状态监控
5. 性能指标导出和报告生成
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FrameMetrics:
    """单帧处理指标"""

    frame_index: int
    detection_time_ms: float = 0.0
    inpainting_time_ms: float = 0.0
    total_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class MemorySnapshot:
    """内存快照"""

    timestamp: float
    process_memory_mb: float
    gpu_memory_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None


@dataclass
class ProcessingStats:
    """处理统计摘要"""

    total_frames: int = 0
    processed_frames: int = 0
    failed_frames: int = 0
    avg_fps: float = 0.0
    avg_detection_time_ms: float = 0.0
    avg_inpainting_time_ms: float = 0.0
    avg_total_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    peak_gpu_memory_mb: float = 0.0
    total_processing_time_s: float = 0.0


class ProcessingMetrics:
    """
    视频处理性能监控器

    收集和分析视频处理过程中的性能指标，
    支持实时监控和事后分析。

    Usage:
        metrics = ProcessingMetrics()
        metrics.start_session(total_frames=1000)

        for frame in frames:
            metrics.start_frame(frame_idx)
            # 处理帧...
            metrics.record_detection_time(detection_ms)
            metrics.record_inpainting_time(inpainting_ms)
            metrics.end_frame()

        stats = metrics.end_session()
        print(f"Average FPS: {stats.avg_fps:.2f}")
    """

    def __init__(self, history_size: int = 1000):
        """
        初始化性能监控器

        Args:
            history_size: 保留的历史帧指标数量（用于滑动窗口统计）
        """
        self._lock = threading.Lock()
        self._history_size = history_size

        # 会话状态
        self._session_active = False
        self._session_start_time: float = 0.0
        self._total_frames: int = 0

        # 帧指标
        self._current_frame: Optional[FrameMetrics] = None
        self._frame_history: List[FrameMetrics] = []

        # 内存快照
        self._memory_snapshots: List[MemorySnapshot] = []

        # 回调
        self._progress_callbacks: List[Callable[[ProcessingStats], None]] = []

        # 滑动窗口 FPS 计算
        self._recent_timestamps: List[float] = []
        self._fps_window_size = 30  # 使用最近30帧计算实时 FPS

    def start_session(self, total_frames: int) -> None:
        """
        开始新的处理会话

        Args:
            total_frames: 预计处理的总帧数
        """
        with self._lock:
            self._session_active = True
            self._session_start_time = time.time()
            self._total_frames = total_frames
            self._frame_history.clear()
            self._memory_snapshots.clear()
            self._recent_timestamps.clear()
            self._current_frame = None

            logger.info(f"性能监控会话开始，预计处理 {total_frames} 帧")

    def end_session(self) -> ProcessingStats:
        """
        结束处理会话并返回统计摘要

        Returns:
            处理统计摘要
        """
        with self._lock:
            if not self._session_active:
                return ProcessingStats()

            self._session_active = False
            total_time = time.time() - self._session_start_time

            stats = self._calculate_stats()
            stats.total_processing_time_s = total_time

            logger.info(
                f"性能监控会话结束: "
                f"处理 {stats.processed_frames}/{stats.total_frames} 帧, "
                f"平均 FPS: {stats.avg_fps:.2f}, "
                f"耗时: {total_time:.2f}s"
            )

            return stats

    def start_frame(self, frame_index: int) -> None:
        """
        开始记录帧处理

        Args:
            frame_index: 帧索引
        """
        with self._lock:
            self._current_frame = FrameMetrics(frame_index=frame_index, timestamp=time.time())

    def record_detection_time(self, time_ms: float) -> None:
        """记录检测耗时（毫秒）"""
        with self._lock:
            if self._current_frame:
                self._current_frame.detection_time_ms = time_ms

    def record_inpainting_time(self, time_ms: float) -> None:
        """记录修复耗时（毫秒）"""
        with self._lock:
            if self._current_frame:
                self._current_frame.inpainting_time_ms = time_ms

    def end_frame(self, success: bool = True) -> None:
        """
        结束帧处理记录

        Args:
            success: 帧是否处理成功
        """
        with self._lock:
            if not self._current_frame:
                return

            end_time = time.time()
            self._current_frame.total_time_ms = (end_time - self._current_frame.timestamp) * 1000

            # 添加到历史
            self._frame_history.append(self._current_frame)

            # 限制历史大小
            if len(self._frame_history) > self._history_size:
                self._frame_history.pop(0)

            # 更新实时 FPS 时间戳
            self._recent_timestamps.append(end_time)
            if len(self._recent_timestamps) > self._fps_window_size:
                self._recent_timestamps.pop(0)

            self._current_frame = None

            # 通知回调
            if self._progress_callbacks:
                stats = self._calculate_stats()
                for callback in self._progress_callbacks:
                    try:
                        callback(stats)
                    except Exception as e:
                        logger.warning(f"性能指标回调失败: {e}")

    def record_memory_snapshot(self) -> MemorySnapshot:
        """
        记录当前内存使用快照

        Returns:
            内存快照
        """
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            process_memory_mb=self._get_process_memory_mb(),
            gpu_memory_mb=self._get_gpu_memory_mb(),
            gpu_memory_total_mb=self._get_gpu_total_memory_mb(),
        )

        with self._lock:
            self._memory_snapshots.append(snapshot)

            # 限制快照数量
            if len(self._memory_snapshots) > 100:
                self._memory_snapshots.pop(0)

        return snapshot

    def get_current_fps(self) -> float:
        """
        获取当前实时 FPS（基于滑动窗口）

        Returns:
            当前 FPS
        """
        with self._lock:
            if len(self._recent_timestamps) < 2:
                return 0.0

            time_span = self._recent_timestamps[-1] - self._recent_timestamps[0]
            if time_span <= 0:
                return 0.0

            return (len(self._recent_timestamps) - 1) / time_span

    def get_progress(self) -> float:
        """
        获取处理进度（0.0 - 1.0）

        Returns:
            进度比例
        """
        with self._lock:
            if self._total_frames <= 0:
                return 0.0
            return len(self._frame_history) / self._total_frames

    def get_eta_seconds(self) -> float:
        """
        获取预计剩余时间（秒）

        Returns:
            预计剩余秒数
        """
        fps = self.get_current_fps()
        if fps <= 0:
            return float("inf")

        with self._lock:
            remaining_frames = self._total_frames - len(self._frame_history)
            return remaining_frames / fps

    def register_progress_callback(self, callback: Callable[[ProcessingStats], None]) -> None:
        """
        注册进度回调

        Args:
            callback: 回调函数，接收 ProcessingStats 参数
        """
        with self._lock:
            self._progress_callbacks.append(callback)

    def unregister_progress_callback(self, callback: Callable[[ProcessingStats], None]) -> None:
        """移除进度回调"""
        with self._lock:
            if callback in self._progress_callbacks:
                self._progress_callbacks.remove(callback)

    def get_stats(self) -> ProcessingStats:
        """获取当前统计摘要"""
        with self._lock:
            return self._calculate_stats()

    def export_report(self) -> Dict:
        """
        导出详细性能报告

        Returns:
            包含所有性能数据的字典
        """
        with self._lock:
            stats = self._calculate_stats()

            return {
                "summary": {
                    "total_frames": stats.total_frames,
                    "processed_frames": stats.processed_frames,
                    "failed_frames": stats.failed_frames,
                    "avg_fps": stats.avg_fps,
                    "total_time_s": stats.total_processing_time_s,
                },
                "timing": {
                    "avg_detection_ms": stats.avg_detection_time_ms,
                    "avg_inpainting_ms": stats.avg_inpainting_time_ms,
                    "avg_total_ms": stats.avg_total_time_ms,
                },
                "memory": {
                    "peak_process_mb": stats.peak_memory_mb,
                    "peak_gpu_mb": stats.peak_gpu_memory_mb,
                },
                "frame_history_count": len(self._frame_history),
                "memory_snapshot_count": len(self._memory_snapshots),
            }

    def _calculate_stats(self) -> ProcessingStats:
        """计算统计摘要（内部方法，需要持有锁）"""
        stats = ProcessingStats(
            total_frames=self._total_frames,
            processed_frames=len(self._frame_history),
        )

        if self._frame_history:
            # 计算平均时间
            detection_times = [f.detection_time_ms for f in self._frame_history]
            inpainting_times = [f.inpainting_time_ms for f in self._frame_history]
            total_times = [f.total_time_ms for f in self._frame_history]

            stats.avg_detection_time_ms = sum(detection_times) / len(detection_times)
            stats.avg_inpainting_time_ms = sum(inpainting_times) / len(inpainting_times)
            stats.avg_total_time_ms = sum(total_times) / len(total_times)

            # 计算平均 FPS
            if stats.avg_total_time_ms > 0:
                stats.avg_fps = 1000.0 / stats.avg_total_time_ms

        # 计算峰值内存
        if self._memory_snapshots:
            stats.peak_memory_mb = max(s.process_memory_mb for s in self._memory_snapshots)
            gpu_memories = [
                s.gpu_memory_mb for s in self._memory_snapshots if s.gpu_memory_mb is not None
            ]
            if gpu_memories:
                stats.peak_gpu_memory_mb = max(gpu_memories)

        return stats

    @staticmethod
    def _get_process_memory_mb() -> float:
        """获取当前进程内存使用（MB）"""
        try:
            import psutil  # type: ignore[import-untyped]

            process = psutil.Process()
            return float(process.memory_info().rss / (1024 * 1024))
        except ImportError:
            return 0.0
        except Exception:  # noqa: S110
            # 内存监控失败时静默返回0，不影响主流程
            return 0.0

    @staticmethod
    def _get_gpu_memory_mb() -> Optional[float]:
        """获取 GPU 显存使用（MB）"""
        try:
            import torch

            if torch.cuda.is_available():
                return float(torch.cuda.memory_allocated() / (1024 * 1024))
        except ImportError:
            return None
        except Exception as exc:  # noqa: S110
            logger.debug("获取 GPU 显存使用失败，降级为无 GPU 指标: %s", exc, exc_info=True)
            return None
        return None

    @staticmethod
    def _get_gpu_total_memory_mb() -> Optional[float]:
        """获取 GPU 总显存（MB）"""
        try:
            import torch

            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                return float(props.total_memory / (1024 * 1024))
        except ImportError:
            return None
        except Exception as exc:  # noqa: S110
            logger.debug("获取 GPU 总显存失败，降级为无 GPU 指标: %s", exc, exc_info=True)
            return None
        return None


# 全局单例
_global_metrics: Optional[ProcessingMetrics] = None


def get_processing_metrics() -> ProcessingMetrics:
    """
    获取全局性能监控器单例

    Returns:
        ProcessingMetrics 实例
    """
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = ProcessingMetrics()
    return _global_metrics


__all__ = [
    "FrameMetrics",
    "MemorySnapshot",
    "ProcessingStats",
    "ProcessingMetrics",
    "get_processing_metrics",
]
