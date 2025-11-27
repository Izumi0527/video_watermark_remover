"""
pytest 配置和共享 fixtures

提供测试所需的通用 fixtures 和配置。
"""

import os
import shutil
import tempfile
from configparser import ConfigParser
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """
    创建临时目录用于测试

    Yields:
        Path: 临时目录路径
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # 清理
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_config_file(temp_dir):
    """
    创建临时配置文件

    Args:
        temp_dir: 临时目录 fixture

    Returns:
        Path: 临时配置文件路径
    """
    config_path = temp_dir / "test_config.ini"
    return config_path


@pytest.fixture
def sample_config():
    """
    创建示例配置对象

    Returns:
        ConfigParser: 示例配置对象
    """
    config = ConfigParser()
    config["Paths"] = {
        "ffmpeg_path": "ffmpeg",
        "default_model_dir": "./models",
        "last_input_dir": "",
        "last_output_dir": "",
    }
    config["Processing"] = {
        "default_output_suffix": "_processed",
        "auto_start_processing": "no",
        "gpu_acceleration": "auto",
    }
    config["Logging"] = {
        "log_level": "INFO",
        "log_file_path": "./logs/app.log",
    }
    return config


@pytest.fixture
def mock_image():
    """
    创建模拟图像数据（使用 numpy）

    Returns:
        numpy.ndarray: 640x480 的黑色 BGR 图像
    """
    import numpy as np

    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_mask():
    """
    创建模拟掩码数据

    Returns:
        numpy.ndarray: 640x480 的全零掩码
    """
    import numpy as np

    return np.zeros((480, 640), dtype=np.uint8)
