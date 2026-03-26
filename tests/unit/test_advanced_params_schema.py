#!/usr/bin/env python3
"""
统一高级参数模型测试。
"""

from __future__ import annotations


def test_advanced_params_defaults_are_single_source_of_truth() -> None:
    from app.config.advanced_params import AdvancedParamsSnapshot

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
