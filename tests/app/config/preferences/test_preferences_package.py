import json
from pathlib import Path

import pytest

from app.config import preferences


def test_defaults_deepcopy():
    base = preferences.PreferencesDefaults.DEFAULT_PREFERENCES
    copy = preferences.PreferencesDefaults.get_default_preferences()
    copy["ui"]["theme"] = "dark"
    assert base["ui"]["theme"] == "light"
    assert copy["ui"]["theme"] == "dark"


def test_validator_rules():
    v = preferences.PreferencesValidator()
    assert v.validate_preference_value("ui", "theme", "dark")
    assert not v.validate_preference_value("ui", "theme", "purple")
    assert v.validate_preference_value("processing", "detection_sensitivity", 0.5)
    assert not v.validate_preference_value("processing", "detection_sensitivity", 1.5)
    assert v.validate_preference_value("advanced", "cache_size_mb", 128)
    assert not v.validate_preference_value("advanced", "cache_size_mb", -1)
    assert v.validate_window_geometry([0, 0, 100, 100])
    assert not v.validate_window_geometry([0, 0, -1, 100])
    assert v.normalize_splitter_sizes([50, 10]) == [100, 100]


def test_storage_roundtrip(tmp_path):
    config_dir = tmp_path / "prefs_storage"
    storage = preferences.PreferencesStorage(config_dir=str(config_dir))
    prefs = preferences.PreferencesDefaults.get_default_preferences()
    prefs["ui"]["theme"] = "light"
    assert storage.save_preferences(prefs)
    assert storage.get_preferences_file_path().exists()
    loaded = storage.load_preferences()
    assert loaded["ui"]["theme"] == "light"

    export_path = tmp_path / "export.json"
    assert storage.export_preferences(loaded, str(export_path))
    imported = storage.import_preferences(str(export_path))
    assert imported is not None
    assert imported["ui"]["theme"] == "light"


def test_manager_set_get(tmp_path):
    config_dir = tmp_path / "prefs_manager"
    manager = preferences.UserPreferencesManager(config_dir=str(config_dir))

    assert manager.set_preference("processing", "output_quality", "low")
    assert manager.get_preference("processing", "output_quality") == "low"
    assert manager.set_preference("ui", "theme", "light")
    assert manager.get_preference("ui", "theme") == "light"

    assert not manager.set_preference("processing", "output_quality", "invalid")

    manager.update_window_geometry(0, 0, 800, 600, maximized=True)
    assert manager.get_preference("ui", "window_geometry") == [0, 0, 800, 600]
    assert manager.get_preference("ui", "window_maximized") is True

    manager.update_window_geometry(0, 0, -1, 600)  # 无效，不应覆盖
    assert manager.get_preference("ui", "window_geometry") == [0, 0, 800, 600]

    manager.update_splitter_sizes([50])  # 会被标准化
    assert manager.get_preference("ui", "splitter_sizes") == [100, 400]

    recent_file = config_dir / "file.txt"
    recent_file.parent.mkdir(parents=True, exist_ok=True)
    recent_file.write_text("data", encoding="utf-8")
    manager.add_recent_file(str(recent_file))
    assert str(recent_file) in manager.get_recent_files()

    manager.clear_recent_files()
    assert manager.get_recent_files() == []

    assert manager.reset_to_defaults()
    assert manager.get_preference("ui", "theme") == "light"


def test_global_manager_singleton(tmp_path, monkeypatch):
    import importlib

    mod = preferences.manager
    monkeypatch.setattr(mod, "_preferences_manager", None)

    cfg1 = tmp_path / "g1"
    cfg2 = tmp_path / "g2"

    m1 = mod.get_preferences_manager(str(cfg1))
    m1.set_preference("ui", "theme", "light")
    assert m1.get_preference("ui", "theme") == "light"

    m2 = mod.get_preferences_manager(str(cfg2))
    # 由于单例，同一实例应返回，并保持修改
    assert m1 is m2
    assert m2.get_preference("ui", "theme") == "light"

    # 重置单例再创建新实例
    monkeypatch.setattr(mod, "_preferences_manager", None)
    m3 = mod.get_preferences_manager(str(cfg2))
    assert m3 is not m1
    assert m3.get_preference("ui", "theme") == "light"


@pytest.mark.parametrize(
    "input_json,expected_theme",
    [
        ({"ui": {"theme": "light"}}, "light"),
        ({}, "light"),
    ],
)
def test_storage_merge_with_default(tmp_path, input_json, expected_theme):
    cfg = tmp_path / "merge"
    cfg.mkdir(parents=True, exist_ok=True)
    prefs_file = cfg / "user_preferences.json"
    prefs_file.write_text(json.dumps(input_json), encoding="utf-8")

    storage = preferences.PreferencesStorage(config_dir=str(cfg))
    loaded = storage.load_preferences()
    assert loaded["ui"]["theme"] == expected_theme
