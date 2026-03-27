#!/usr/bin/env python3
"""
统一高级参数偏好迁移测试。
"""

from __future__ import annotations

from pathlib import Path

from app.config.advanced_params import AdvancedParamsSnapshot
from app.config.preferences import UserPreferencesManager


def _make_config_dir(name: str) -> Path:
    return Path("virtual_test_prefs") / name


def test_manager_migrates_legacy_advanced_and_batch_preferences() -> None:
    config_dir = _make_config_dir("advanced_batch")
    manager = UserPreferencesManager(config_dir=str(config_dir / "prefs"))
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


def test_existing_advanced_params_defaults_are_not_overridden_by_legacy_fields() -> None:
    config_dir = _make_config_dir("defaults_priority")
    manager = UserPreferencesManager(config_dir=str(config_dir / "prefs"))
    manager.preferences["advanced_params"] = AdvancedParamsSnapshot.defaults().to_dict()
    manager.preferences["advanced"] = {
        "max_threads": 8,
        "enable_gpu": True,
        "cache_size_mb": 2048,
    }
    manager.preferences["batch"] = {
        "max_concurrent_files": 4,
        "auto_retry_failed": False,
        "max_retry_count": 7,
    }
    assert manager.save_preferences() is True

    manager = UserPreferencesManager(config_dir=str(config_dir / "prefs"))

    snapshot = manager.get_advanced_params_snapshot()

    assert snapshot == AdvancedParamsSnapshot.defaults()


def test_manager_ignores_legacy_processing_output_preferences() -> None:
    config_dir = _make_config_dir("processing_output")
    manager = UserPreferencesManager(config_dir=str(config_dir / "prefs"))
    manager.preferences["processing"] = {
        "preserve_audio": False,
        "output_quality": "low",
    }

    snapshot = manager.get_advanced_params_snapshot()

    assert snapshot.preserve_audio is True
    assert snapshot.compression_quality == 85
