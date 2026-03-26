#!/usr/bin/env python3
"""
流水线缓存预算测试。
"""

from __future__ import annotations


def test_pipeline_queue_sizes_follow_cache_budget() -> None:
    from app.core.video.utils.backpressure import calculate_runtime_queue_budget

    small = calculate_runtime_queue_budget(
        enable_cache=False,
        cache_size_mb=128,
        frame_shape=(1080, 1920),
    )
    large = calculate_runtime_queue_budget(
        enable_cache=True,
        cache_size_mb=1024,
        frame_shape=(1080, 1920),
    )

    assert large.frame_queue_size > small.frame_queue_size
    assert large.result_queue_size > small.result_queue_size
    assert large.writer_buffer_size > small.writer_buffer_size
