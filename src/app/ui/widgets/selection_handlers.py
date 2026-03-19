#!/usr/bin/env python3
"""
图像选择事件处理器模块

提供鼠标事件处理功能：
1. 鼠标按下事件处理
2. 鼠标移动事件处理
3. 鼠标释放事件处理
4. 选择区域管理

"""

from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QMouseEvent, QPixmap

if TYPE_CHECKING:
    from .coordinate_converter import CoordinateConverter


class SelectionEventHandler:
    """图像选择事件处理器"""

    def __init__(self):
        """初始化事件处理器"""
        # 选择状态
        self.is_selecting = False
        self.selection_start = QPoint()
        self.current_selection = QRect()
        self.selection_areas: List[Tuple[int, int, int, int]] = []

        # 回调函数
        self.on_selection_changed: Optional[Callable] = None
        self.on_cursor_change: Optional[Callable] = None
        self.on_update_display: Optional[Callable] = None

        # 坐标转换器引用（由外部设置）
        self._coordinate_converter: Optional["CoordinateConverter"] = None

    def set_coordinate_converter(self, converter: "CoordinateConverter") -> None:
        """
        设置坐标转换器引用

        Args:
            converter: CoordinateConverter 实例
        """
        self._coordinate_converter = converter

    def set_callbacks(
        self,
        selection_changed: Optional[Callable] = None,
        cursor_change: Optional[Callable] = None,
        update_display: Optional[Callable] = None,
    ):
        """
        设置回调函数

        Args:
            selection_changed: 选择区域变化回调
            cursor_change: 光标变化回调
            update_display: 显示更新回调
        """
        self.on_selection_changed = selection_changed
        self.on_cursor_change = cursor_change
        self.on_update_display = update_display

    def handle_mouse_press(
        self, event: QMouseEvent, scaled_pixmap: QPixmap, image_offset: QPoint
    ) -> bool:
        """
        处理鼠标按下事件

        Args:
            event: 鼠标事件
            scaled_pixmap: 缩放后的图像
            image_offset: 图像偏移

        Returns:
            是否处理了事件
        """
        if not event or event.button() != Qt.MouseButton.LeftButton or not scaled_pixmap:
            return False

        # 检查点击是否在图像区域内
        click_pos = event.pos() - image_offset
        image_rect = scaled_pixmap.rect()

        if image_rect.contains(click_pos):
            self.is_selecting = True
            self.selection_start = click_pos
            self.current_selection = QRect(click_pos, click_pos)

            if self.on_cursor_change:
                self.on_cursor_change(Qt.CursorShape.CrossCursor)

            return True

        return False

    def handle_mouse_move(
        self, event: QMouseEvent, scaled_pixmap: QPixmap, image_offset: QPoint
    ) -> bool:
        """
        处理鼠标移动事件

        Args:
            event: 鼠标事件
            scaled_pixmap: 缩放后的图像
            image_offset: 图像偏移

        Returns:
            是否处理了事件
        """
        if not self.is_selecting or not event or not scaled_pixmap:
            return False

        # 更新当前选择区域
        current_pos = event.pos() - image_offset
        self.current_selection = QRect(self.selection_start, current_pos).normalized()

        # 限制选择区域在图像范围内
        image_rect = scaled_pixmap.rect()
        self.current_selection = self.current_selection.intersected(image_rect)

        if self.on_update_display:
            self.on_update_display()

        return True

    def handle_mouse_release(self, event: QMouseEvent, scale_factor: float) -> bool:
        """
        处理鼠标释放事件

        Args:
            event: 鼠标事件
            scale_factor: 缩放因子（仅在未设置 coordinate_converter 时使用）

        Returns:
            是否处理了事件
        """
        if not event or event.button() != Qt.MouseButton.LeftButton or not self.is_selecting:
            return False

        self.is_selecting = False

        if self.on_cursor_change:
            self.on_cursor_change(Qt.CursorShape.ArrowCursor)

        # 如果选择区域足够大，添加到选择列表
        if self.current_selection.width() > 5 and self.current_selection.height() > 5:
            # 转换到原图坐标系
            if self._coordinate_converter is not None:
                # 使用已设置的坐标转换器（推荐）
                original_rect = self._coordinate_converter.scaled_to_original_rect(
                    self.current_selection
                )
            else:
                # 兼容旧代码：创建临时转换器
                from .coordinate_converter import CoordinateConverter

                converter = CoordinateConverter(scale_factor)
                original_rect = converter.scaled_to_original_rect(self.current_selection)

            self.selection_areas.append(original_rect)

            # 发送选择变化信号
            if self.on_selection_changed:
                self.on_selection_changed(self.selection_areas.copy())

        # 清空当前选择
        self.current_selection = QRect()

        if self.on_update_display:
            self.on_update_display()

        return True

    def clear_selections(self) -> None:
        """清空所有选择区域"""
        self.selection_areas.clear()
        self.current_selection = QRect()
        self.is_selecting = False

        if self.on_selection_changed:
            self.on_selection_changed([])

        if self.on_update_display:
            self.on_update_display()

    def get_selections(self) -> List[Tuple[int, int, int, int]]:
        """获取所有选择区域（原图坐标系）"""
        return self.selection_areas.copy()

    def get_current_selection(self) -> QRect:
        """获取当前正在选择的区域"""
        return self.current_selection

    def is_currently_selecting(self) -> bool:
        """是否正在选择中"""
        return self.is_selecting
