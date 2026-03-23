"""
ImageInpainter 单元测试 (Phase 2 简化版)

测试图像修复器的核心功能，匹配Phase 2实际API：
- 模型加载
- 基本图像修复功能
- 不同掩码类型的处理
- 错误处理

测试用例数量: 14个
覆盖率目标: 核心功能100%
"""

from unittest.mock import Mock

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from app.core.ai.image_inpainter import ImageInpainter


class TestImageInpainter:
    """ImageInpainter Phase 2 测试类"""

    # ===== 初始化测试 =====

    def test_init_without_config(self):
        """测试无配置初始化"""
        # Act
        inpainter = ImageInpainter()

        # Assert
        assert inpainter is not None
        assert inpainter.config is None
        assert inpainter.inpainting_model is None

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
        assert inpainter.inpainting_model == "opencv_inpaint"

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

    # ===== 图像修复测试 (Phase 2不接受method参数) =====

    def test_inpaint_frame_basic(self, mock_image, mock_mask):
        """测试基本修复功能"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, mock_mask)

        # Assert
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape == mock_image.shape

    def test_inpaint_frame_with_none_image(self, mock_mask):
        """测试处理None图像"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act & Assert - 应该抛出InpaintingError
        from app.core.exceptions import InpaintingError

        with pytest.raises(InpaintingError):
            inpainter.inpaint_frame(None, mock_mask)

    def test_inpaint_frame_with_none_mask(self, mock_image):
        """测试处理None掩码"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, None)

        # Assert
        # Phase 2 会返回原图
        assert result is not None
        assert np.array_equal(result, mock_image)

    def test_inpaint_frame_with_empty_mask(self, mock_image):
        """测试使用空掩码（全零）"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()
        empty_mask = np.zeros((480, 640), dtype=np.uint8)

        # Act
        result = inpainter.inpaint_frame(mock_image, empty_mask)

        # Assert
        # 空掩码应该返回原图
        assert result is not None
        assert np.array_equal(result, mock_image)

    def test_inpaint_frame_with_small_mask(self, mock_image):
        """测试小掩码修复（自动选择自定义方法）"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 创建小掩码（<5%）
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:110, 100:110] = 255  # 10x10像素

        # Act
        result = inpainter.inpaint_frame(mock_image, mask)

        # Assert
        assert result is not None
        assert result.shape == mock_image.shape

    def test_inpaint_frame_with_medium_mask(self, mock_image):
        """测试中等掩码修复（自动选择TELEA）"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 创建中等掩码（5-15%）
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:200, 100:200] = 255  # 100x100像素

        # Act
        result = inpainter.inpaint_frame(mock_image, mask)

        # Assert
        assert result is not None
        assert result.shape == mock_image.shape

    def test_inpaint_frame_with_large_mask(self, mock_image):
        """测试大掩码修复（自动选择Navier-Stokes）"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 创建大掩码（>15%）
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[50:400, 50:600] = 255  # 大区域

        # Act
        result = inpainter.inpaint_frame(mock_image, mask)

        # Assert
        assert result is not None
        assert result.shape == mock_image.shape

    def test_inpaint_frame_accepts_navier_stokes_alias(
        self,
        monkeypatch,
        mock_image,
        mock_mask,
    ):
        """显式传入 navier_stokes 时应走 OpenCV NS 分支。"""
        inpainter = ImageInpainter()
        inpainter.load_model()
        captured = {}

        def fake_inpaint(frame, mask, radius, flags):
            captured["radius"] = radius
            captured["flags"] = flags
            return frame.copy()

        monkeypatch.setattr(cv2, "inpaint", fake_inpaint)

        result = inpainter.inpaint_frame(
            mock_image,
            mock_mask,
            method="navier_stokes",
            radius=4,
            quality_level=3,
        )

        assert result is not None
        assert captured["flags"] == cv2.INPAINT_NS
        assert captured["radius"] == 4

    def test_inpaint_frame_quality_level_affects_effective_radius(
        self,
        monkeypatch,
        mock_image,
        mock_mask,
    ):
        """高质量等级应让 OpenCV 修复半径更积极一些。"""
        inpainter = ImageInpainter()
        inpainter.load_model()
        radii = []

        def fake_inpaint(frame, mask, radius, flags):
            radii.append(radius)
            return frame.copy()

        monkeypatch.setattr(cv2, "inpaint", fake_inpaint)

        inpainter.inpaint_frame(
            mock_image,
            mock_mask,
            method="telea",
            radius=4,
            quality_level=1,
        )
        inpainter.inpaint_frame(
            mock_image,
            mock_mask,
            method="telea",
            radius=4,
            quality_level=5,
        )

        assert radii[0] < radii[1]

    def test_inpaint_frame_with_scattered_mask(self, mock_image):
        """测试分散掩码修复"""
        # Arrange
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 创建分散的掩码
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[50:60, 50:60] = 255
        mask[200:210, 300:310] = 255
        mask[400:410, 500:510] = 255

        # Act
        result = inpainter.inpaint_frame(mock_image, mask)

        # Assert
        assert result is not None
        assert result.shape == mock_image.shape

    def test_inpaint_frame_with_color_image(self):
        """测试处理彩色图像"""
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
        result = inpainter.inpaint_frame(image, mask)

        # Assert
        assert result is not None
        assert result.shape[2] == 3  # 保持3通道

    def test_inpaint_frame_without_loading_model(self, mock_image, mock_mask):
        """测试未加载模型时修复"""
        # Arrange
        inpainter = ImageInpainter()
        # 不调用 load_model()

        # Act
        result = inpainter.inpaint_frame(mock_image, mock_mask)

        # Assert
        # Phase 2会检查模型是否加载，返回原图
        assert result is not None
        assert np.array_equal(result, mock_image)


# Fixtures


@pytest.fixture
def mock_config():
    """创建模拟配置对象"""
    config = Mock()
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
