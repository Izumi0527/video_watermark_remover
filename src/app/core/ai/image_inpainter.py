#!/usr/bin/env python3
"""
图像修复模块

提供基于OpenCV的图像修复功能：
1. OpenCV内置修复算法(TELEA, Navier-Stokes)
2. 自定义插值修复方法
3. 多方法组合修复策略
4. 区域大小自适应选择

"""

from __future__ import annotations

import logging
from typing import Optional, Union

import cv2
import numpy as np
from numpy.typing import NDArray

from ..exceptions import InpaintingError

# ==================== 修复参数常量 ====================

# 二值化阈值参数
MASK_BINARY_THRESHOLD = 127
MASK_BINARY_MAX = 255

# OpenCV inpaint 修复半径
INPAINT_RADIUS = 3

# 区域大小自适应阈值
SMALL_AREA_THRESHOLD = 0.05  # 小区域：占图像 < 5%
MEDIUM_AREA_THRESHOLD = 0.15  # 中等区域：占图像 < 15%

# 自定义修复参数
CUSTOM_INPAINT_MIN_PADDING = 5  # 最小填充像素
CUSTOM_INPAINT_PADDING_DIVISOR = 4  # 填充大小计算除数

# 高斯模糊参数
CUSTOM_BLUR_KERNEL_SIZE = (21, 21)
CUSTOM_BLUR_SIGMA = 0

# 形态学操作参数
CUSTOM_MORPH_KERNEL_SIZE = (15, 15)
CUSTOM_MORPH_KERNEL_SHAPE = cv2.MORPH_ELLIPSE
CUSTOM_DILATE_ITERATIONS = 1

# 过渡混合参数
TRANSITION_BLUR_KERNEL_SIZE = (15, 15)
TRANSITION_BLUR_SIGMA = 0

# 质量等级映射
QUALITY_RADIUS_FACTORS = {
    1: 0.75,
    2: 0.9,
    3: 1.0,
    4: 1.15,
    5: 1.3,
}

AUTO_THRESHOLD_PRESETS = {
    1: (0.08, 0.20),
    2: (0.06, 0.17),
    3: (SMALL_AREA_THRESHOLD, MEDIUM_AREA_THRESHOLD),
    4: (0.04, 0.12),
    5: (0.03, 0.10),
}


class ImageInpainter:
    """
    图像修复器

    使用多种OpenCV方法进行图像修复，根据修复区域大小自动选择最佳方法
    """

    def __init__(self, config=None):
        self.config = config
        self.inpainting_model = None
        self.logger = logging.getLogger(__name__)
        self.last_method_used: Optional[str] = None
        self.last_effective_radius = INPAINT_RADIUS
        self.last_quality_level = 3

    def load_model(self) -> bool:
        """
        加载修复模型（使用OpenCV方法）

        Returns:
            bool: 加载是否成功
        """
        self.logger.info("Loading lightweight image inpainting model...")

        # Phase 2: 使用OpenCV方法，无需外部模型文件
        self.inpainting_model = "opencv_inpaint"

        self.logger.info("Image inpainting model loaded successfully:")
        self.logger.info("  - Method: OpenCV interpolation-based repair")

        return True

    def inpaint_frame(  # noqa: C901
        self,
        frame: Optional[NDArray[np.uint8]],
        mask: Optional[NDArray[np.uint8]],
        method: Optional[str] = None,
        radius: int = INPAINT_RADIUS,
        quality_level: int = 3,
    ) -> Optional[NDArray[np.uint8]]:
        """
        基于提供的掩码对帧应用修复，支持 TELEA / NS / 自定义 / 自动选择。

        Args:
            frame: 输入图像，numpy数组(BGR格式)
            mask: 二值掩码，255=需要修复的区域，0=保持原始
            method: telea | ns | custom | auto；None 表示 Phase2 兼容模式
            radius: OpenCV inpaint 半径
            quality_level: 修复质量等级 (1-5)

        Returns:
            修复后的帧；输入缺失或方法无效时返回 None。
        """
        legacy_mode = method is None  # Phase2 兼容：无 method 参数

        if legacy_mode:
            if frame is None:
                raise InpaintingError("输入图像为空")
            if mask is None:
                self.logger.warning("Mask is None, return original frame (legacy mode)")
                return frame
        else:
            if frame is None or mask is None:
                self.logger.warning("Frame or mask is None, skip inpainting")
                return None

        if self.inpainting_model != "opencv_inpaint":
            self.logger.warning("Inpainting model not loaded")
            return frame if legacy_mode else None

        if mask is not None and not np.any(mask):
            self.logger.debug("No mask provided or empty mask, returning original frame")
            return frame

        try:
            self.logger.debug("Starting image inpainting using OpenCV methods")
            quality_level = self._normalize_quality_level(quality_level)
            effective_radius = self._resolve_effective_radius(radius, quality_level)
            self.last_quality_level = quality_level
            self.last_effective_radius = effective_radius

            # 确保掩码是单通道
            if len(mask.shape) == 3:
                mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

            # 二值化掩码
            _, bin_mask = cv2.threshold(
                mask, MASK_BINARY_THRESHOLD, MASK_BINARY_MAX, cv2.THRESH_BINARY
            )

            method = self._normalize_method(method or "auto")

            # 各算法结果
            def _telea() -> NDArray[np.uint8]:
                self.last_method_used = "telea"
                return np.asarray(cv2.inpaint(frame, bin_mask, effective_radius, cv2.INPAINT_TELEA))

            def _ns() -> NDArray[np.uint8]:
                self.last_method_used = "navier_stokes"
                return np.asarray(cv2.inpaint(frame, bin_mask, effective_radius, cv2.INPAINT_NS))

            def _custom() -> NDArray[np.uint8]:
                self.last_method_used = "custom_interpolation"
                return self._custom_inpaint(frame, bin_mask, quality_level=quality_level)

            if method == "telea":
                return _telea()
            if method == "ns":
                return _ns()
            if method == "custom":
                return _custom()
            if method not in {"auto", "telea", "ns", "custom"}:
                self.logger.warning(f"Invalid inpaint method: {method}")
                return None

            # 自动选择：按掩码面积比挑选算法
            contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            total_inpaint_area = sum(cv2.contourArea(c) for c in contours)
            image_area = frame.shape[0] * frame.shape[1]
            area_ratio = total_inpaint_area / image_area if image_area else 0
            small_threshold, medium_threshold = AUTO_THRESHOLD_PRESETS[quality_level]

            if area_ratio < small_threshold:
                return _custom()
            if area_ratio < medium_threshold:
                return _telea()
            return _ns()

        except Exception as e:
            self.logger.error(f"Error in image inpainting: {e}")
            raise InpaintingError("图像修复失败", details=str(e), original_exception=e)

    def _custom_inpaint(
        self, frame: NDArray[np.uint8], mask: NDArray[np.uint8], quality_level: int = 3
    ) -> NDArray[np.uint8]:
        """
        使用插值和纹理合成的自定义修复方法
        适用于小的水印区域

        Args:
            frame: 输入帧
            mask: 修复掩码

        Returns:
            修复后的图像
        """
        result = frame.copy()
        profile = self._build_custom_quality_profile(quality_level)

        # 寻找需要修复区域的轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # 获取边界矩形
            x, y, w, h = cv2.boundingRect(contour)

            # 添加填充以获取上下文
            base_padding = max(
                CUSTOM_INPAINT_MIN_PADDING, min(w, h) // CUSTOM_INPAINT_PADDING_DIVISOR
            )
            padding = max(
                CUSTOM_INPAINT_MIN_PADDING, int(round(base_padding * profile["padding_scale"]))
            )
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(frame.shape[1], x + w + padding)
            y2 = min(frame.shape[0], y + h + padding)

            # 提取区域
            region = frame[y1:y2, x1:x2]
            region_mask = mask[y1:y2, x1:x2]

            # 对周围区域应用高斯模糊以实现平滑过渡
            blur_kernel = self._ensure_odd_kernel(int(profile["blur_kernel"]))
            blurred_region = cv2.GaussianBlur(region, blur_kernel, CUSTOM_BLUR_SIGMA)

            # 使用形态学操作创建平滑过渡
            morph_kernel = cv2.getStructuringElement(
                CUSTOM_MORPH_KERNEL_SHAPE,
                self._ensure_odd_kernel(int(profile["morph_kernel"])),
            )
            dilated_mask = cv2.dilate(
                region_mask, morph_kernel, iterations=int(profile["dilate_iterations"])
            )

            # 创建过渡权重
            transition_mask = dilated_mask.astype(np.float32) / 255.0
            transition_mask = cv2.GaussianBlur(
                transition_mask,
                self._ensure_odd_kernel(int(profile["transition_kernel"])),
                TRANSITION_BLUR_SIGMA,
            )

            # 混合原始、模糊和修复区域
            for c in range(3):  # 对每个颜色通道
                channel: np.ndarray = region[:, :, c].astype(np.float32)
                blurred_channel: np.ndarray = blurred_region[:, :, c].astype(np.float32)

                # 应用平滑混合
                result_channel = (1 - transition_mask) * channel + transition_mask * blurred_channel
                result[y1:y2, x1:x2, c] = result_channel.astype(np.uint8)

        return result

    def _normalize_method(self, method: str) -> str:
        """统一修复方法别名，便于 UI 与 core 层对齐。"""
        normalized = (method or "auto").lower()
        alias_mapping = {
            "navier_stokes": "ns",
            "custom_interpolation": "custom",
        }
        return alias_mapping.get(normalized, normalized)

    def _normalize_quality_level(self, quality_level: int) -> int:
        """将质量等级限制在 1-5 之间。"""
        try:
            normalized = int(quality_level)
        except (TypeError, ValueError):
            normalized = 3
        return min(5, max(1, normalized))

    def _resolve_effective_radius(self, radius: int, quality_level: int) -> int:
        """基于质量等级计算实际 OpenCV 修复半径。"""
        base_radius = max(1, int(radius))
        factor = QUALITY_RADIUS_FACTORS[self._normalize_quality_level(quality_level)]
        return max(1, int(round(base_radius * factor)))

    def _ensure_odd_kernel(
        self,
        kernel_size: Union[int, tuple[int, int]],
    ) -> tuple[int, int]:
        """确保核大小为奇数。"""
        if isinstance(kernel_size, tuple):
            width, height = kernel_size
        else:
            width = height = kernel_size
        if width % 2 == 0:
            width += 1
        if height % 2 == 0:
            height += 1
        return width, height

    def _build_custom_quality_profile(self, quality_level: int) -> dict[str, Union[float, int]]:
        """为自定义插值修复构建随质量变化的强度配置。"""
        level = self._normalize_quality_level(quality_level)
        return {
            1: {
                "padding_scale": 0.8,
                "blur_kernel": 11,
                "morph_kernel": 9,
                "dilate_iterations": 1,
                "transition_kernel": 9,
            },
            2: {
                "padding_scale": 0.9,
                "blur_kernel": 15,
                "morph_kernel": 11,
                "dilate_iterations": 1,
                "transition_kernel": 11,
            },
            3: {
                "padding_scale": 1.0,
                "blur_kernel": 21,
                "morph_kernel": 15,
                "dilate_iterations": 1,
                "transition_kernel": 15,
            },
            4: {
                "padding_scale": 1.1,
                "blur_kernel": 25,
                "morph_kernel": 17,
                "dilate_iterations": 2,
                "transition_kernel": 19,
            },
            5: {
                "padding_scale": 1.25,
                "blur_kernel": 31,
                "morph_kernel": 21,
                "dilate_iterations": 2,
                "transition_kernel": 23,
            },
        }[level]
