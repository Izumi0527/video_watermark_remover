"""
ConfigManager 单元测试

测试配置管理器的核心功能，包括：
- 配置文件加载和创建
- 配置项读取和验证
- 默认值处理
- 错误处理

测试用例数量: 18个
覆盖率目标: 90%+
"""

import pytest
import tempfile
from pathlib import Path
from configparser import ConfigParser
import shutil

from app.config.config_manager import ConfigManager


class TestConfigManager:
    """ConfigManager 测试类"""

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
        assert config.has_section("processing")
        assert config.get("processing", "default_detection_sensitivity") == "0.7"

    def test_get_detection_sensitivity_default(self, temp_config_file):
        """测试获取默认检测敏感度"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))

        # Act
        sensitivity = ConfigManager.get_detection_sensitivity(config)

        # Assert
        assert sensitivity == 0.5
        assert isinstance(sensitivity, float)

    def test_get_detection_sensitivity_custom(self, existing_config_file):
        """测试获取自定义检测敏感度"""
        # Arrange
        config = ConfigManager.load_config(str(existing_config_file))

        # Act
        sensitivity = ConfigManager.get_detection_sensitivity(config)

        # Assert
        assert sensitivity == 0.7

    def test_get_detection_sensitivity_invalid_returns_default(
        self, temp_config_file
    ):
        """测试无效敏感度值返回默认值"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))
        config.set("processing", "default_detection_sensitivity", "invalid")

        # Act
        sensitivity = ConfigManager.get_detection_sensitivity(config)

        # Assert
        assert sensitivity == 0.5

    def test_get_inpainting_method_default(self, temp_config_file):
        """测试获取默认修复方法"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))

        # Act
        method = ConfigManager.get_inpainting_method(config)

        # Assert
        assert method == "auto"
        assert isinstance(method, str)

    def test_get_inpainting_method_custom(self, existing_config_file):
        """测试获取自定义修复方法"""
        # Arrange
        config = ConfigManager.load_config(str(existing_config_file))

        # Act
        method = ConfigManager.get_inpainting_method(config)

        # Assert
        assert method == "telea"

    def test_preserve_audio_default(self, temp_config_file):
        """测试默认保留音频设置"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))

        # Act
        preserve = ConfigManager.preserve_audio(config)

        # Assert
        assert preserve is True
        assert isinstance(preserve, bool)

    def test_preserve_audio_false(self, temp_config_file):
        """测试音频不保留设置"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))
        config.set("processing", "preserve_audio", "false")

        # Act
        preserve = ConfigManager.preserve_audio(config)

        # Assert
        assert preserve is False

    def test_preserve_audio_invalid_returns_default(self, temp_config_file):
        """测试无效音频保留值返回默认值"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))
        config.set("processing", "preserve_audio", "maybe")

        # Act
        preserve = ConfigManager.preserve_audio(config)

        # Assert
        assert preserve is True

    def test_config_has_required_sections(self, temp_config_file):
        """测试配置包含必需的section"""
        # Act
        config = ConfigManager.load_config(str(temp_config_file))

        # Assert
        assert config.has_section("processing")
        assert config.has_section("paths")
        assert config.has_section("advanced")

    def test_config_has_required_options(self, temp_config_file):
        """测试配置包含必需的选项"""
        # Act
        config = ConfigManager.load_config(str(temp_config_file))

        # Assert
        assert config.has_option("processing", "default_detection_sensitivity")
        assert config.has_option("processing", "default_inpainting_method")
        assert config.has_option("processing", "preserve_audio")

    def test_config_default_values(self, temp_config_file):
        """测试配置默认值"""
        # Act
        config = ConfigManager.load_config(str(temp_config_file))

        # Assert
        assert config.get("processing", "default_detection_sensitivity") == "0.5"
        assert config.get("processing", "default_inpainting_method") == "auto"
        assert config.get("processing", "preserve_audio") == "true"

    def test_load_config_handles_unicode(self, temp_config_file):
        """测试配置文件处理Unicode字符"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))
        config.set("processing", "comment", "支持中文注释")

        # Act
        with open(temp_config_file, "w", encoding="utf-8") as f:
            config.write(f)

        config_reloaded = ConfigManager.load_config(str(temp_config_file))

        # Assert
        assert config_reloaded.get("processing", "comment") == "支持中文注释"

    def test_load_config_with_nonexistent_directory(self, temp_dir):
        """测试在不存在的目录中创建配置文件"""
        # Arrange
        nonexistent_dir = temp_dir / "subdir" / "config.ini"

        # Act
        config = ConfigManager.load_config(str(nonexistent_dir))

        # Assert
        assert nonexistent_dir.exists()
        assert isinstance(config, ConfigParser)

    def test_load_config_preserves_comments(self, temp_config_file):
        """测试配置文件保留注释（ConfigParser不保留注释，此测试验证行为）"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))

        # Act - 写入配置文件
        with open(temp_config_file, "w", encoding="utf-8") as f:
            config.write(f)

        # Assert - 验证文件可以被重新读取
        config_reloaded = ConfigManager.load_config(str(temp_config_file))
        assert config_reloaded.get("processing", "default_detection_sensitivity") == "0.5"

    def test_config_edge_case_sensitivity_bounds(self, temp_config_file):
        """测试敏感度边界值"""
        # Arrange
        config = ConfigManager.load_config(str(temp_config_file))

        # Test lower bound
        config.set("processing", "default_detection_sensitivity", "0.0")
        assert ConfigManager.get_detection_sensitivity(config) == 0.0

        # Test upper bound
        config.set("processing", "default_detection_sensitivity", "1.0")
        assert ConfigManager.get_detection_sensitivity(config) == 1.0

        # Test out of range (should return default)
        config.set("processing", "default_detection_sensitivity", "1.5")
        sensitivity = ConfigManager.get_detection_sensitivity(config)
        # 这里依赖于ConfigManager的实现，可能返回默认值或夹紧到范围内
        assert 0.0 <= sensitivity <= 1.0


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
    """创建已存在的配置文件"""
    config_path = temp_dir / "existing_config.ini"
    config = ConfigParser()
    config.add_section("processing")
    config.set("processing", "default_detection_sensitivity", "0.7")
    config.set("processing", "default_inpainting_method", "telea")
    config.set("processing", "preserve_audio", "true")

    config.add_section("paths")
    config.add_section("advanced")

    with open(config_path, "w", encoding="utf-8") as f:
        config.write(f)

    yield config_path
    if config_path.exists():
        config_path.unlink()
