"""
健壮性单元测试：覆盖配置管理、通用工具和日志初始化。

关注点：
- 配置文件损坏时的自愈能力
- update_config_value 自动创建缺失 section
- 日志目录不可写时的异常处理
- 通用工具方法的边界条件
"""

import os
from configparser import ConfigParser
from pathlib import Path

import pytest

from app.config.config_manager import ConfigManager
from app.utils import utils
from app.utils.logger_setup import setup_logging


def test_load_config_recovers_from_corrupted_file(tmp_path):
    """配置文件损坏时应回落到默认配置并补齐必需 section/option。"""
    bad_file = tmp_path / "broken.ini"
    bad_file.write_text("not a valid ini\n[Paths\nffmpeg_path", encoding="utf-8")

    config = ConfigManager.load_config(str(bad_file))

    assert isinstance(config, ConfigParser)
    assert config.has_section("Paths")
    assert config.has_option("Paths", "ffmpeg_path")
    assert config.get("Processing", "gpu_acceleration") in {"auto", "yes", "no"}


def test_update_config_value_creates_missing_section(tmp_path):
    """当 section 不存在时，update_config_value 应自动创建并持久化。"""
    config_path = tmp_path / "config.ini"
    ConfigManager.load_config(str(config_path))

    assert (
        ConfigManager.update_config_value("NewSection", "new_key", "123", str(config_path)) is True
    )

    reloaded = ConfigManager.load_config(str(config_path))
    assert reloaded.get("NewSection", "new_key") == "123"


def test_setup_logging_creates_log_file(tmp_path, monkeypatch):
    """日志初始化应创建 logs 目录并生成日志文件。"""
    monkeypatch.chdir(tmp_path)

    assert setup_logging() is True

    log_dir = tmp_path / "logs"
    assert log_dir.exists() and log_dir.is_dir()
    created_files = list(log_dir.glob("watermark_remover_*.log"))
    assert created_files, "日志文件未生成"


def test_setup_logging_handles_makedirs_error(monkeypatch):
    """当日志目录创建失败时，setup_logging 应返回 False 而非抛异常。"""
    monkeypatch.setattr(os.path, "exists", lambda path: False)

    def _raise_oserror(*_, **__):
        raise OSError("cannot create")

    monkeypatch.setattr(os, "makedirs", _raise_oserror)

    assert setup_logging() is False


def test_ensure_directory_exists_success(tmp_path):
    """正常路径应成功创建目录。"""
    target = tmp_path / "a" / "b"
    assert utils.ensure_directory_exists(target) is True
    assert target.is_dir()


def test_ensure_directory_exists_handles_oserror(monkeypatch):
    """目录创建异常时应返回 False。"""
    monkeypatch.setattr(os.path, "exists", lambda path: False)

    def _raise_oserror(*_, **__):
        raise OSError("blocked")

    monkeypatch.setattr(os, "makedirs", _raise_oserror)

    assert utils.ensure_directory_exists("any/path") is False


def test_format_duration_negative():
    """负值应归零格式化。"""
    assert utils.format_duration(-5) == "00:00:00"


def test_get_file_basename_empty_string():
    """空输入应返回空字符串，避免 None/空路径异常。"""
    assert utils.get_file_basename("") == ""
