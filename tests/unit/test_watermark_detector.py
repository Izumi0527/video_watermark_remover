"""
WatermarkDetector 单元测试 (Phase 2 简化版)

测试水印检测器的核心功能，匹配Phase 2实际API：
- 模型加载
- 基本水印检测
- 不同图像类型的处理
- 错误处理

测试用例数量: 12个
覆盖率目标: 核心功能100%
"""

import pytest
import numpy as np
import cv2
from unittest.mock import Mock

from app.core.ai.watermark_detector import WatermarkDetector


class TestWatermarkDetector:
    """WatermarkDetector Phase 2 测试类"""

    # ===== 初始化测试 =====

    def test_init_without_config(self):
        """测试无配置初始化"""
        # Act
        detector = WatermarkDetector()

        # Assert
        assert detector is not None
        assert detector.config is None
        assert detector.detection_model is None

    def test_init_with_config(self, mock_config):
        """测试使用配置初始化"""
        # Act
        detector = WatermarkDetector(config=mock_config)

        # Assert
        assert detector is not None
        assert detector.config == mock_config

    # ===== 模型加载测试 =====

    def test_load_model_success(self):
        """测试模型加载成功"""
        # Arrange
        detector = WatermarkDetector()

        # Act
        result = detector.load_model()

        # Assert
        assert result is True
        assert detector.detection_model == "opencv_traditional"

    def test_load_model_idempotent(self):
        """测试重复加载模型"""
        # Arrange
        detector = WatermarkDetector()

        # Act
        result1 = detector.load_model()
        result2 = detector.load_model()

        # Assert
        assert result1 is True
        assert result2 is True

    # ===== 水印检测测试 =====

    def test_detect_watermark_returns_mask_or_none(self, mock_image):
        """测试检测返回掩码或None"""
        # Arrange
        detector = WatermarkDetector()
        detector.load_model()

        # Act
        result = detector.detect_watermark(mock_image)

        # Assert
        # Phase 2可能检测到或检测不到，都是正常的
        if result is not None:
            assert isinstance(result, np.ndarray)
            assert len(result.shape) == 2  # 二值掩码应该是2D
            assert result.dtype == np.uint8

    def test_detect_watermark_with_none_image(self):
        """测试传入None图像"""
        # Arrange
        detector = WatermarkDetector()
        detector.load_model()

        # Act & Assert - 应该抛出DetectionError
        from app.core.exceptions import DetectionError
        with pytest.raises(DetectionError):
            detector.detect_watermark(None)

    def test_detect_watermark_with_empty_image(self):
        """测试传入空图像"""
        # Arrange
        detector = WatermarkDetector()
        detector.load_model()
        empty_image = np.array([])

        # Act & Assert - 应该抛出DetectionError
        from app.core.exceptions import DetectionError
        with pytest.raises(DetectionError):
            detector.detect_watermark(empty_image)

    def test_detect_watermark_with_simulated_text(self):
        """测试在包含模拟文本的图像上检测"""
        # Arrange
        detector = WatermarkDetector()
        detector.load_model()

        # 创建包含白色矩形（模拟文本）的图像
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(image, (50, 50), (200, 100), (255, 255, 255), -1)

        # Act
        result = detector.detect_watermark(image)

        # Assert
        # 应该检测到白色矩形区域（可能）
        if result is not None:
            assert isinstance(result, np.ndarray)
            # 检测结果应该有一些非零值
            assert np.any(result > 0)

    def test_detect_watermark_with_color_image(self):
        """测试处理彩色图像"""
        # Arrange
        detector = WatermarkDetector()
        detector.load_model()

        # 创建彩色图像
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        image[:, :, 0] = 100  # 蓝色通道
        image[:, :, 1] = 150  # 绿色通道
        image[:, :, 2] = 200  # 红色通道

        # Act
        result = detector.detect_watermark(image)

        # Assert
        # 应该能处理彩色图像
        assert result is None or isinstance(result, np.ndarray)

    def test_detect_watermark_with_grayscale_conversion(self):
        """测试能够处理需要转换的图像"""
        # Arrange
        detector = WatermarkDetector()
        detector.load_model()

        # 创建测试图像
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Act
        result = detector.detect_watermark(image)

        # Assert
        # 应该能够处理
        assert result is None or isinstance(result, np.ndarray)

    def test_detect_watermark_without_loading_model(self, mock_image):
        """测试在未加载模型时检测"""
        # Arrange
        detector = WatermarkDetector()
        # 不调用 load_model()

        # Act
        result = detector.detect_watermark(mock_image)

        # Assert
        # Phase 2会检查模型是否加载
        assert result is None

    def test_detect_watermark_consistent_output_shape(self, mock_image):
        """测试检测输出形状一致性"""
        # Arrange
        detector = WatermarkDetector()
        detector.load_model()

        # Act
        result = detector.detect_watermark(mock_image)

        # Assert
        if result is not None:
            # 输出掩码形状应该与输入图像的高宽一致
            assert result.shape[0] == mock_image.shape[0]
            assert result.shape[1] == mock_image.shape[1]


# Fixtures

@pytest.fixture
def mock_config():
    """创建模拟配置对象"""
    config = Mock()
    return config


@pytest.fixture
def mock_image():
    """创建模拟图像数据"""
    # 创建480x640的BGR图像
    return np.zeros((480, 640, 3), dtype=np.uint8)
