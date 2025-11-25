"""
ConfigManager 单元测试 (Phase 2 简化版)

测试配置管理器的核心功能，匹配Phase 2实际API：
- 配置文件加载和创建
- 配置对象操作
- 基本的配置读写功能

测试用例数量: 10个
覆盖率目标: 核心功能100%
"""

import shutil
import tempfile
from configparser import ConfigParser
from pathlib import Path

import pytest

from app.config.config_manager import ConfigManager


class TestConfigManager:
    """ConfigManager Phase 2 测试类"""

    def test_load_config_creates_file_if_not_exists(self, temp_config_file):
        """测试当配置文件不存在时会创建默认配置"""
        # Arrange
        assert not temp_config_file.exists()

        # Act
        config = ConfigManager.load_config(str(temp_config_file))

        # Assert
        assert temp_config_file.exists()
        assert isinstance(config, ConfigParser)

    def test_load_config_returns_configparser(self, temp_config_file):
        """测试load_config返回ConfigParser对象"""
        # Act
        config = ConfigManager.load_config(str(temp_config_file))

        # Assert
        assert isinstance(config, ConfigParser)
        assert config is not None

    def test_load_config_with_existing_file(self, existing_config_file):
        """测试加载已存在的配置文件"""
        # Act
        config = ConfigManager.load_config(str(existing_config_file))

        # Assert
        assert isinstance(config, ConfigParser)
        assert config.has_section("Paths")
        assert config.get("Paths", "ffmpeg_path") == "ffmpeg_custom"

    def test_config_has_default_sections(self, temp_config_file):
        """测试配置包含默认的sections (Phase 2实际sections)"""
        # Act
        config = ConfigManager.load_config(str(temp_config_file))

        # Assert - Phase 2 实际的section名称
        assert config.has_section("Paths")
        assert config.has_section("Processing")
        assert config.has_section("Logging")
        assert config.has_section("Models")

    def test_config_default_values(self, temp_config_file):
        """测试配置默认值 (Phase 2实际默认值)"""
        # Act
        config = ConfigManager.load_config(str(temp_config_file))

        # Assert
        assert config.get("Paths", "ffmpeg_path") == "ffmpeg"
        assert config.get("Processing", "auto_start_processing") == "no"
        assert config.get("Logging", "log_level") == "INFO"

    def test_save_config_success(self, temp_config_file):
        """测试保存配置成功"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))
        config.set("Paths", "ffmpeg_path", "custom_ffmpeg")

        # Act
        result = ConfigManager.save_config(config, str(temp_config_file))

        # Assert
        assert result is True
        reloaded_config = ConfigManager.load_config(str(temp_config_file))
        assert reloaded_config.get("Paths", "ffmpeg_path") == "custom_ffmpeg"

    def test_update_config_value_success(self, temp_config_file):
        """测试更新配置值成功"""
        # Arrange
        ConfigManager.load_config(str(temp_config_file))

        # Act
        result = ConfigManager.update_config_value(
            "Logging", "log_level", "DEBUG", str(temp_config_file)
        )

        # Assert
        assert result is True
        config = ConfigManager.load_config(str(temp_config_file))
        assert config.get("Logging", "log_level") == "DEBUG"

    def test_load_config_handles_unicode(self, temp_config_file):
        """测试配置文件处理Unicode字符"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))
        config.set("Paths", "last_input_dir", "测试目录/中文路径")

        # Act
        ConfigManager.save_config(config, str(temp_config_file))
        config_reloaded = ConfigManager.load_config(str(temp_config_file))

        # Assert
        assert config_reloaded.get("Paths", "last_input_dir") == "测试目录/中文路径"

    def test_load_config_with_nonexistent_directory(self, temp_dir):
        """测试在不存在的目录中创建配置文件"""
        # Arrange
        nonexistent_dir = temp_dir / "subdir" / "config.ini"

        # Act
        config = ConfigManager.load_config(str(nonexistent_dir))

        # Assert
        assert nonexistent_dir.exists()
        assert isinstance(config, ConfigParser)

    def test_get_config_path(self):
        """测试获取配置文件路径"""
        # Act
        path = ConfigManager.get_config_path()

        # Assert
        assert isinstance(path, str)
        assert len(path) > 0
        assert "VideoWatermarkRemover" in path or "video" in path.lower()


# Fixtures


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_config_file(temp_dir):
    """创建临时配置文件路径（不存在的文件）"""
    config_path = temp_dir / "config.ini"
    yield config_path
    if config_path.exists():
        config_path.unlink()


@pytest.fixture
def existing_config_file(temp_dir):
    """创建已存在的配置文件 (使用Phase 2实际的section名称)"""
    config_path = temp_dir / "existing_config.ini"
    config = ConfigParser()

    # Phase 2 实际的sections
    config.add_section("Paths")
    config.set("Paths", "ffmpeg_path", "ffmpeg_custom")
    config.set("Paths", "default_model_dir", "./models")

    config.add_section("Processing")
    config.set("Processing", "auto_start_processing", "yes")

    config.add_section("Logging")
    config.set("Logging", "log_level", "DEBUG")

    config.add_section("Models")

    with open(config_path, "w", encoding="utf-8") as f:
        config.write(f)

    yield config_path
    if config_path.exists():
        config_path.unlink()
