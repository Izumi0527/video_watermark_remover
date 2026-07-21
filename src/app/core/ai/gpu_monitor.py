#!/usr/bin/env python3
"""
GPU 显存监控模块

提供 GPU 显存监控和自适应批处理功能：
1. 显存使用量监控
2. 自适应批大小计算
3. 显存不足警告和自动清理
4. 安全检查和降级策略

"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GPUMemoryInfo:
    """GPU 显存信息"""

    total_mb: float
    used_mb: float
    free_mb: float
    utilization_percent: float

    @property
    def is_low(self) -> bool:
        """显存是否处于低水位"""
        return self.free_mb < 500 or self.utilization_percent > 90


class GPUMemoryMonitor:
    """
    GPU 显存监控器

    提供显存监控、自适应批处理和安全检查功能
    """

    # 显存阈值配置
    MIN_FREE_MB: float = 500  # 最小保留显存 (MB)
    WARNING_THRESHOLD: float = 0.85  # 警告阈值 (85% 使用率)
    CRITICAL_THRESHOLD: float = 0.95  # 临界阈值 (95% 使用率)

    # 帧显存估算参数 (基于经验值)
    # 1080p 帧 ≈ 50MB GPU 显存 (包括推理中间结果)
    BYTES_PER_PIXEL: int = 3  # BGR
    GPU_MEMORY_MULTIPLIER: int = 10  # 推理时的显存倍数

    def __init__(self):
        self._torch_available = False
        self._cuda_available = False
        self._init_torch()

    def _init_torch(self) -> None:
        """初始化 PyTorch 并检查 CUDA 可用性"""
        try:
            import torch

            self._torch_available = True
            self._cuda_available = torch.cuda.is_available()

            if self._cuda_available:
                device_name = torch.cuda.get_device_name(0)
                total_mem = torch.cuda.get_device_properties(0).total_memory
                logger.info(
                    f"GPU Memory Monitor initialized: {device_name}, "
                    f"Total VRAM: {total_mem / (1024**3):.1f} GB"
                )
            else:
                logger.info("GPU Memory Monitor: CUDA not available, running in CPU mode")

        except ImportError:
            logger.warning("GPU Memory Monitor: PyTorch not installed")
            self._torch_available = False
            self._cuda_available = False

    @property
    def is_available(self) -> bool:
        """GPU 是否可用"""
        return self._cuda_available

    def get_memory_info(self) -> Optional[GPUMemoryInfo]:
        """
        获取当前 GPU 显存信息

        Returns:
            GPUMemoryInfo 对象，如果 GPU 不可用则返回 None
        """
        if not self._cuda_available:
            return None

        try:
            import torch

            free, total = torch.cuda.mem_get_info()
            used = total - free

            return GPUMemoryInfo(
                total_mb=total / (1024**2),
                used_mb=used / (1024**2),
                free_mb=free / (1024**2),
                utilization_percent=(used / total) * 100 if total > 0 else 0,
            )

        except Exception as e:
            logger.warning(f"Failed to get GPU memory info: {e}")
            return None

    def get_free_memory_mb(self) -> float:
        """
        获取可用显存 (MB)

        Returns:
            可用显存，如果 GPU 不可用则返回无限大
        """
        info = self.get_memory_info()
        return info.free_mb if info else float("inf")

    def check_memory_available(self, required_mb: float = 500) -> bool:
        """
        检查是否有足够的显存

        Args:
            required_mb: 所需显存 (MB)

        Returns:
            是否有足够显存
        """
        if not self._cuda_available:
            return True  # CPU 模式，不受限

        free = self.get_free_memory_mb()
        return free >= required_mb

    def ensure_memory(self, min_free_mb: float = 500) -> bool:
        """
        确保有足够显存，必要时清理缓存

        Args:
            min_free_mb: 最小保留显存 (MB)

        Returns:
            清理后是否有足够显存
        """
        if not self._cuda_available:
            return True

        try:
            import torch

            free = self.get_free_memory_mb()

            if free < min_free_mb:
                logger.warning(
                    f"Low GPU memory ({free:.0f}MB < {min_free_mb:.0f}MB), clearing cache..."
                )
                torch.cuda.empty_cache()
                free = self.get_free_memory_mb()
                logger.info(f"GPU memory after cleanup: {free:.0f}MB")

            return free >= min_free_mb

        except Exception as e:
            logger.warning(f"Failed to ensure GPU memory: {e}")
            return False

    def estimate_frame_memory(self, frame_size: Tuple[int, int]) -> float:
        """
        估算单帧处理所需显存

        Args:
            frame_size: 帧尺寸 (height, width)

        Returns:
            估算的显存需求 (MB)
        """
        height, width = frame_size
        # 基础帧内存
        frame_bytes = height * width * self.BYTES_PER_PIXEL
        # 推理时的显存（包括中间结果、梯度等）
        estimated_bytes = frame_bytes * self.GPU_MEMORY_MULTIPLIER
        return estimated_bytes / (1024**2)

    def calculate_safe_batch_size(
        self,
        base_batch_size: int,
        frame_size: Tuple[int, int],
        safety_margin: float = 0.7,
    ) -> int:
        """
        根据可用显存计算安全的批处理大小

        Args:
            base_batch_size: 基础批大小
            frame_size: 帧尺寸 (height, width)
            safety_margin: 安全系数 (0-1)，预留部分显存

        Returns:
            安全的批处理大小 (至少为1)
        """
        if not self._cuda_available:
            return base_batch_size

        try:
            free_mb = self.get_free_memory_mb()
            usable_mb = free_mb * safety_margin

            frame_memory_mb = self.estimate_frame_memory(frame_size)

            if frame_memory_mb <= 0:
                return base_batch_size

            safe_batch = int(usable_mb / frame_memory_mb)
            result = max(1, min(base_batch_size, safe_batch))

            if result < base_batch_size:
                logger.info(
                    f"Batch size adjusted: {base_batch_size} → {result} "
                    f"(free: {free_mb:.0f}MB, per frame: {frame_memory_mb:.1f}MB)"
                )

            return result

        except Exception as e:
            logger.warning(f"Failed to calculate safe batch size: {e}")
            return base_batch_size

    def check_and_warn(self) -> Optional[str]:
        """
        检查显存状态并返回警告信息

        Returns:
            警告信息字符串，如果正常则返回 None
        """
        info = self.get_memory_info()
        if info is None:
            return None

        if info.utilization_percent >= self.CRITICAL_THRESHOLD * 100:
            return (
                f"⚠️ 严重警告：GPU 显存使用率达到 {info.utilization_percent:.1f}%！"
                f"剩余 {info.free_mb:.0f}MB，可能导致 OOM 崩溃。"
            )
        elif info.utilization_percent >= self.WARNING_THRESHOLD * 100:
            return (
                f"⚠️ 警告：GPU 显存使用率较高 ({info.utilization_percent:.1f}%)，"
                f"剩余 {info.free_mb:.0f}MB。建议降低批处理大小或视频分辨率。"
            )

        return None

    def cleanup(self) -> None:
        """清理 GPU 缓存"""
        if not self._cuda_available:
            return

        try:
            import torch

            torch.cuda.empty_cache()
            logger.debug("GPU cache cleared")

        except Exception as e:
            logger.warning(f"Failed to clear GPU cache: {e}")

    def log_status(self) -> None:
        """记录当前 GPU 状态到日志"""
        info = self.get_memory_info()
        if info:
            logger.info(
                f"GPU Memory Status: "
                f"Used {info.used_mb:.0f}MB / {info.total_mb:.0f}MB "
                f"({info.utilization_percent:.1f}%), Free: {info.free_mb:.0f}MB"
            )
        else:
            logger.info("GPU Memory Status: GPU not available")


# 全局单例实例
_gpu_monitor: Optional[GPUMemoryMonitor] = None


def get_gpu_monitor() -> GPUMemoryMonitor:
    """获取全局 GPU 监控器实例"""
    global _gpu_monitor
    if _gpu_monitor is None:
        _gpu_monitor = GPUMemoryMonitor()
    return _gpu_monitor


# ============================================================================
# 便捷函数
# ============================================================================


def check_gpu_memory(min_free_mb: float = 500) -> bool:
    """检查 GPU 是否有足够显存"""
    return get_gpu_monitor().check_memory_available(min_free_mb)


def ensure_gpu_memory(min_free_mb: float = 500) -> bool:
    """确保有足够显存，必要时清理缓存"""
    return get_gpu_monitor().ensure_memory(min_free_mb)


def get_safe_batch_size(base_size: int, frame_size: Tuple[int, int]) -> int:
    """计算安全的批处理大小"""
    return get_gpu_monitor().calculate_safe_batch_size(base_size, frame_size)


def cleanup_gpu() -> None:
    """清理 GPU 缓存"""
    get_gpu_monitor().cleanup()
