#!/usr/bin/env python3
"""
坐标转换工具模块

提供图像坐标系之间的转换功能：
1. 缩放坐标系与原图坐标系转换
2. 显示坐标系与图像坐标系转换
3. 矩形区域坐标转换

"""

from typing import Tuple

from PyQt6.QtCore import QPoint, QRect, QSize
from PyQt6.QtGui import QPixmap


class CoordinateConverter:
    """坐标转换工具类"""

    def __init__(self, scale_factor: float = 1.0):
        """
        初始化坐标转换器

        Args:
            scale_factor: 缩放因子
        """
        self.scale_factor = scale_factor

    def set_scale_factor(self, scale_factor: float) -> None:
        """
        设置缩放因子

        Args:
            scale_factor: 新的缩放因子
        """
        self.scale_factor = scale_factor

    def scaled_to_original_rect(self, scaled_rect: QRect) -> Tuple[int, int, int, int]:
        """
        将缩放坐标系的矩形转换为原图坐标系

        Args:
            scaled_rect: 缩放坐标系中的矩形

        Returns:
            原图坐标系中的矩形 (x, y, width, height)
        """
        if self.scale_factor == 0:
            return (0, 0, 0, 0)

        x = int(scaled_rect.x() / self.scale_factor)
        y = int(scaled_rect.y() / self.scale_factor)
        w = int(scaled_rect.width() / self.scale_factor)
        h = int(scaled_rect.height() / self.scale_factor)

        return (x, y, w, h)

    def original_to_scaled_rect(self, original_rect: Tuple[int, int, int, int]) -> QRect:
        """
        将原图坐标系的矩形转换为缩放坐标系

        Args:
            original_rect: 原图坐标系中的矩形 (x, y, width, height)

        Returns:
            缩放坐标系中的QRect
        """
        x, y, w, h = original_rect
        scaled_x = int(x * self.scale_factor)
        scaled_y = int(y * self.scale_factor)
        scaled_w = int(w * self.scale_factor)
        scaled_h = int(h * self.scale_factor)

        return QRect(scaled_x, scaled_y, scaled_w, scaled_h)

    @staticmethod
    def calculate_scale_factor(
        widget_size: QSize, pixmap_size: QSize, margin_ratio: float = 0.1
    ) -> float:
        """
        计算适合控件大小的缩放因子

        Args:
            widget_size: 控件大小
            pixmap_size: 图像大小
            margin_ratio: 边距比例（默认10%）

        Returns:
            缩放因子
        """
        if pixmap_size.width() == 0 or pixmap_size.height() == 0:
            return 1.0

        # 计算缩放比例（保持宽高比）
        scale_x = widget_size.width() / pixmap_size.width()
        scale_y = widget_size.height() / pixmap_size.height()
        scale_factor = min(scale_x, scale_y) * (1.0 - margin_ratio)  # 留出边距

        return max(scale_factor, 0.1)  # 最小缩放因子为0.1

    @staticmethod
    def calculate_image_offset(widget_size: QSize, scaled_size: QSize) -> QPoint:
        """
        计算图像在控件中的偏移（居中显示）

        Args:
            widget_size: 控件大小
            scaled_size: 缩放后图像大小

        Returns:
            图像偏移位置
        """
        offset_x = (widget_size.width() - scaled_size.width()) // 2
        offset_y = (widget_size.height() - scaled_size.height()) // 2

        return QPoint(max(0, offset_x), max(0, offset_y))

    def display_to_image_rect(self, display_rect: QRect, image_offset: QPoint) -> QRect:
        """
        将显示坐标系的矩形转换为图像坐标系

        Args:
            display_rect: 显示坐标系中的矩形
            image_offset: 图像偏移

        Returns:
            图像坐标系中的QRect
        """
        return QRect(
            display_rect.x() - image_offset.x(),
            display_rect.y() - image_offset.y(),
            display_rect.width(),
            display_rect.height(),
        )

    def image_to_display_rect(self, image_rect: QRect, image_offset: QPoint) -> QRect:
        """
        将图像坐标系的矩形转换为显示坐标系

        Args:
            image_rect: 图像坐标系中的矩形
            image_offset: 图像偏移

        Returns:
            显示坐标系中的QRect
        """
        return QRect(
            image_rect.x() + image_offset.x(),
            image_rect.y() + image_offset.y(),
            image_rect.width(),
            image_rect.height(),
        )
