#!/usr/bin/env python3
"""
背压控制器模块

提供精确的生产者-消费者背压控制：
1. 基于 Condition 变量的精确等待/唤醒
2. 高低水位线控制
3. 避免轮询浪费CPU

"""

import threading
from typing import Optional


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


__all__ = ["BackpressureController", "AdaptiveBackpressure"]
