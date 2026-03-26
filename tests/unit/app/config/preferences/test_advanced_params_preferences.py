#!/usr/bin/env python3
"""
统一高级参数偏好迁移测试。
"""

from __future__ import annotations

from app.config.preferences import UserPreferencesManager


def test_manager_migrates_legacy_advanced_and_batch_preferences(tmp_path) -> None:
    manager = UserPreferencesManager(config_dir=str(tmp_path / "prefs"))
    manager.preferences["advanced"] = {
        "max_threads": 6,
        "enable_gpu": False,
        "cache_size_mb": 768,
    }
    manager.preferences["batch"] = {
        "max_concurrent_files": 2,
        "auto_retry_failed": False,
        "max_retry_count": 1,
    }

    snapshot = manager.get_advanced_params_snapshot()

    assert snapshot.worker_count == 6
    assert snapshot.enable_gpu is False
    assert snapshot.cache_size_mb == 768
    assert snapshot.batch_max_concurrent_files == 2
    assert snapshot.batch_auto_retry_failed is False
    assert snapshot.batch_max_retry_count == 1
