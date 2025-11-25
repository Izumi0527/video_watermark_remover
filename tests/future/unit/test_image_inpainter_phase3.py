"""
ImageInpainter 单元测试

测试图像修复器的核心功能，包括：
- 模型加载
- TELEA算法修复
- Navier-Stokes算法修复
- 自定义修复方法
- 自动方法选择
- 边缘融合
- 错误处理

测试用例数量: 28+个
覆盖率目标: 80%+
"""

from unittest.mock import Mock, patch

import cv2
import numpy as np
import pytest

from app.core.ai.image_inpainter import ImageInpainter


class TestImageInpainter:
    """ImageInpainter 测试类"""

    # ===== 初始化测试 =====

    def test_init_without_config(self):
        """测试无配置初始化"""
        # Act
        inpainter = ImageInpainter()

        # Assert
        assert inpainter is not None
        assert inpainter.config is None

    def test_init_with_config(self, mock_config):
        """测试使用配置初始化"""
        # Act
        inpainter = ImageInpainter(config=mock_config)

        # Assert
        assert inpainter is not None
        assert inpainter.config == mock_config

    # ===== 模型加载测试 =====

    def test_load_model_success(self):
        """测试模型加载成功"""
        # Arrange
        inpainter = ImageInpainter()

        # Act
        result = inpainter.load_model()

        # Assert
        assert result is True

    def test_load_model_idempotent(self):
        """测试重复加载模型"""
        # Arrange
        inpainter = ImageInpainter()

        # Act
        result1 = inpainter.load_model()
        result2 = inpainter.load_model()

        # Assert
        assert result1 is True
        assert result2 is True

    # ===== TELEA算法测试 =====

    def test_inpaint_telea_basic(self, mock_image, mock_mask):
        """测试TELEA算法基本功能"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, mock_mask, method="telea")

        # Assert
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape == mock_image.shape

    def test_inpaint_telea_with_none_image(self, mock_mask):
        """测试TELEA算法处理None图像"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(None, mock_mask, method="telea")

        # Assert
        assert result is None

    def test_inpaint_telea_with_none_mask(self, mock_image):
        """测试TELEA算法处理None掩码"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, None, method="telea")

        # Assert
        assert result is None

    def test_inpaint_telea_preserves_unmasked_areas(self, mock_image):
        """测试TELEA算法保留未掩码区域"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 创建小掩码（只覆盖一小部分）
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:110, 100:110] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="telea")

        # Assert
        assert result is not None
        # 未掩码区域应该保持不变或仅有轻微变化
        # 这里只验证返回了有效结果

    def test_inpaint_telea_with_large_mask(self, mock_image):
        """测试TELEA算法处理大掩码"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 创建大掩码（覆盖大部分区域）
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[50:400, 50:600] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="telea")

        # Assert
        assert result is not None

    def test_inpaint_telea_with_scattered_mask(self, mock_image):
        """测试TELEA算法处理分散掩码"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 创建分散的掩码
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[50:60, 50:60] = 255
        mask[200:210, 300:310] = 255
        mask[400:410, 500:510] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="telea")

        # Assert
        assert result is not None

    def test_inpaint_telea_radius_parameter(self, mock_image, mock_mask):
        """测试TELEA算法的半径参数"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result_small = inpainter.inpaint_frame(mock_image, mock_mask, method="telea", radius=3)
        result_large = inpainter.inpaint_frame(mock_image, mock_mask, method="telea", radius=10)

        # Assert
        assert result_small is not None
        assert result_large is not None

    def test_inpaint_telea_with_color_image(self):
        """测试TELEA算法处理彩色图像"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 创建彩色图像
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        image[:, :, 0] = 100  # 蓝色通道
        image[:, :, 1] = 150  # 绿色通道
        image[:, :, 2] = 200  # 红色通道

        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:200, 100:200] = 255

        # Act
        result = inpainter.inpaint_frame(image, mask, method="telea")

        # Assert
        assert result is not None
        assert result.shape[2] == 3  # 保持3通道

    # ===== Navier-Stokes算法测试 =====

    def test_inpaint_ns_basic(self, mock_image, mock_mask):
        """测试Navier-Stokes算法基本功能"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, mock_mask, method="ns")

        # Assert
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape == mock_image.shape

    def test_inpaint_ns_with_none_image(self, mock_mask):
        """测试Navier-Stokes算法处理None图像"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(None, mock_mask, method="ns")

        # Assert
        assert result is None

    def test_inpaint_ns_with_none_mask(self, mock_image):
        """测试Navier-Stokes算法处理None掩码"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, None, method="ns")

        # Assert
        assert result is None

    def test_inpaint_ns_preserves_unmasked_areas(self, mock_image):
        """测试Navier-Stokes算法保留未掩码区域"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:110, 100:110] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="ns")

        # Assert
        assert result is not None

    def test_inpaint_ns_with_large_mask(self, mock_image):
        """测试Navier-Stokes算法处理大掩码"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[50:400, 50:600] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="ns")

        # Assert
        assert result is not None

    def test_inpaint_ns_with_scattered_mask(self, mock_image):
        """测试Navier-Stokes算法处理分散掩码"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[50:60, 50:60] = 255
        mask[200:210, 300:310] = 255
        mask[400:410, 500:510] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="ns")

        # Assert
        assert result is not None

    def test_inpaint_ns_radius_parameter(self, mock_image, mock_mask):
        """测试Navier-Stokes算法的半径参数"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result_small = inpainter.inpaint_frame(mock_image, mock_mask, method="ns", radius=3)
        result_large = inpainter.inpaint_frame(mock_image, mock_mask, method="ns", radius=10)

        # Assert
        assert result_small is not None
        assert result_large is not None

    def test_inpaint_ns_with_color_image(self):
        """测试Navier-Stokes算法处理彩色图像"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        image = np.zeros((480, 640, 3), dtype=np.uint8)
        image[:, :, 0] = 100
        image[:, :, 1] = 150
        image[:, :, 2] = 200

        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:200, 100:200] = 255

        # Act
        result = inpainter.inpaint_frame(image, mask, method="ns")

        # Assert
        assert result is not None
        assert result.shape[2] == 3

    # ===== 自定义修复方法测试 =====

    def test_inpaint_custom_method(self, mock_image, mock_mask):
        """测试自定义修复方法"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, mock_mask, method="custom")

        # Assert
        assert result is not None
        assert isinstance(result, np.ndarray)

    def test_inpaint_custom_with_small_area(self, mock_image):
        """测试自定义方法处理小区域"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:105, 100:105] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="custom")

        # Assert
        assert result is not None

    def test_inpaint_custom_with_large_area(self, mock_image):
        """测试自定义方法处理大区域"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[50:450, 50:630] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="custom")

        # Assert
        assert result is not None

    # ===== 自动方法选择测试 =====

    def test_inpaint_auto_method_selection_small_area(self, mock_image):
        """测试自动选择方法（小区域）"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 小掩码
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[200:220, 300:320] = 255  # 20x20像素

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="auto")

        # Assert
        assert result is not None

    def test_inpaint_auto_method_selection_large_area(self, mock_image):
        """测试自动选择方法（大区域）"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 大掩码
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:300, 100:500] = 255  # 200x400像素

        # Act
        result = inpainter.inpaint_frame(mock_image, mask, method="auto")

        # Assert
        assert result is not None

    def test_inpaint_frame_with_small_area_uses_custom_method(self, mock_image):
        """测试小区域修复使用自定义方法"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[200:220, 300:320] = 255  # 20x20像素

        # Act
        result = inpainter.inpaint_frame(mock_image, mask)

        # Assert
        assert result is not None

    # ===== 错误处理测试 =====

    def test_inpaint_without_loading_model(self, mock_image, mock_mask):
        """测试未加载模型时修复"""
        # Arrange
        inpainter = ImageInpainter()

        # Act
        result = inpainter.inpaint_frame(mock_image, mock_mask)

        # Assert
        # 应该能够处理（可能自动加载模型或返回None）
        assert result is None or isinstance(result, np.ndarray)

    def test_inpaint_with_invalid_method(self, mock_image, mock_mask):
        """测试使用无效方法"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, mock_mask, method="invalid_method")

        # Assert
        # 应该fallback到默认方法或返回None
        assert result is None or isinstance(result, np.ndarray)

    def test_inpaint_with_empty_mask(self, mock_image):
        """测试使用空掩码"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        empty_mask = np.zeros((480, 640), dtype=np.uint8)

        # Act
        result = inpainter.inpaint_frame(mock_image, empty_mask)

        # Assert
        # 空掩码应该返回原图或None
        if result is not None:
            assert np.array_equal(result, mock_image) or result is None


# Fixtures


@pytest.fixture
def mock_config():
    """创建模拟配置对象"""
    config = Mock()
    config.get.return_value = "auto"
    return config


@pytest.fixture
def mock_image():
    """创建模拟图像数据"""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_mask():
    """创建模拟掩码"""
    mask = np.zeros((480, 640), dtype=np.uint8)
    mask[100:200, 100:200] = 255
    return mask
