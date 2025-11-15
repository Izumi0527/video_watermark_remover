#!/usr/bin/env python3
"""
可选择图像标签模块

提供支持区域选择的图像标签组件：
1. 图像显示和缩放
2. 选择区域可视化
3. 绘制和渲染管理

从 image_selector_widget.py 重构拆分
作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.1 (延迟导入优化)
"""

from typing import List, Optional, Tuple

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QLabel

from .coordinate_converter import CoordinateConverter
from .selection_handlers import SelectionEventHandler


class SelectableImageLabel(QLabel):
    """
    支持区域选择的图像标签组件

    功能：
    - 显示图像
    - 鼠标拖拽选择矩形区域
    - 支持多个选择区域
    - 区域高亮显示
    """

    # 选择区域变化信号：发送所有选择区域的列表
    selection_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._init_handlers()

    def _init_ui(self):
        """初始化UI设置"""
        # 基本设置
        self.setMinimumSize(400, 300)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            """
            QLabel {
                border: 2px solid #ccc;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
        """
        )

        # 图像和缩放相关
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.scale_factor = 1.0
        self.image_offset = QPoint(0, 0)  # 图像在控件中的偏移

        # 显示设置
        self.selection_color = QColor(255, 0, 0, 100)  # 半透明红色
        self.selection_border_color = QColor(255, 0, 0, 255)  # 红色边框

        # 设置默认提示文本
        self.set_default_text()

    def _init_handlers(self):
        """初始化事件处理器"""
        self.event_handler = SelectionEventHandler()
        self.coordinate_converter = CoordinateConverter()

        # 设置回调函数
        self.event_handler.set_callbacks(
            selection_changed=self._emit_selection_changed,
            cursor_change=self.setCursor,
            update_display=self.update,
        )

    def set_default_text(self):
        """设置默认提示文本"""
        self.setText("图像预览区域\n\n请选择图片文件进行预览\n然后拖拽鼠标选择水印区域")
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

    def setImage(self, image_path: str) -> bool:
        """
        设置要显示的图像

        Args:
            image_path: 图像文件路径

        Returns:
            加载是否成功
        """
        try:
            # 加载图像
            self.original_pixmap = QPixmap(image_path)
            if self.original_pixmap.isNull():
                self.setText("❌ 无法加载图像")
                return False

            # 清空之前的选择
            self.clearSelections()

            # 计算缩放和显示
            self._update_scaled_pixmap()
            self.setText("")  # 清空文本，显示图像

            return True

        except Exception as e:
            self.setText(f"❌ 图像加载失败\n{str(e)}")
            return False

    def setImageFromArray(self, image_array: "np.ndarray") -> bool:
        """
        从numpy数组设置图像

        Args:
            image_array: OpenCV格式的图像数组 (BGR)

        Returns:
            转换是否成功
        """
        try:
            # 延迟导入：只在实际使用时才导入OpenCV和NumPy
            import cv2
            import numpy as np

            # 转换BGR到RGB
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)

            # 转换为QPixmap
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w

            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.original_pixmap = QPixmap.fromImage(qt_image)

            # 清空之前的选择
            self.clearSelections()

            # 计算缩放和显示
            self._update_scaled_pixmap()
            self.setText("")  # 清空文本，显示图像

            return True

        except Exception as e:
            self.setText(f"❌ 图像数组转换失败\n{str(e)}")
            return False

    def _update_scaled_pixmap(self):
        """更新缩放后的图像"""
        if not self.original_pixmap:
            return

        # 计算适合控件大小的缩放
        widget_size = self.size()
        pixmap_size = self.original_pixmap.size()

        # 计算缩放比例和偏移
        self.scale_factor = CoordinateConverter.calculate_scale_factor(
            widget_size, pixmap_size, 0.1
        )

        # 更新坐标转换器
        self.coordinate_converter.set_scale_factor(self.scale_factor)

        # 缩放图像
        scaled_size = pixmap_size * self.scale_factor
        self.scaled_pixmap = self.original_pixmap.scaled(
            scaled_size.toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 计算图像在控件中的偏移（居中显示）
        self.image_offset = CoordinateConverter.calculate_image_offset(
            widget_size, scaled_size.toSize()
        )

        self.setPixmap(self.scaled_pixmap)
        self.update()  # 触发重绘

    def mousePressEvent(self, event: Optional[QMouseEvent]):
        """鼠标按下事件"""
        if event:
            self.event_handler.handle_mouse_press(event, self.scaled_pixmap, self.image_offset)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Optional[QMouseEvent]):
        """鼠标移动事件"""
        if event:
            self.event_handler.handle_mouse_move(event, self.scaled_pixmap, self.image_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Optional[QMouseEvent]):
        """鼠标释放事件"""
        if event:
            self.event_handler.handle_mouse_release(event, self.scale_factor)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: Optional[QPaintEvent]):
        """绘制事件 - 绘制图像和选择区域"""
        super().paintEvent(event)

        if not self.scaled_pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制已保存的选择区域
        self._draw_saved_selections(painter)

        # 绘制当前正在选择的区域
        self._draw_current_selection(painter)

    def _draw_saved_selections(self, painter: QPainter):
        """绘制已保存的选择区域"""
        brush = QBrush(self.selection_color)
        pen = QPen(self.selection_border_color, 2)
        painter.setBrush(brush)
        painter.setPen(pen)

        for original_rect in self.event_handler.get_selections():
            # 转换到缩放坐标系
            scaled_rect = self.coordinate_converter.original_to_scaled_rect(original_rect)
            display_rect = self.coordinate_converter.image_to_display_rect(
                scaled_rect, self.image_offset
            )
            painter.drawRect(display_rect)

    def _draw_current_selection(self, painter: QPainter):
        """绘制当前正在选择的区域"""
        if not self.event_handler.is_currently_selecting():
            return

        current_selection = self.event_handler.get_current_selection()
        if current_selection.isEmpty():
            return

        pen = QPen(self.selection_border_color, 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        display_rect = self.coordinate_converter.image_to_display_rect(
            current_selection, self.image_offset
        )
        painter.drawRect(display_rect)

    def clearSelections(self):
        """清空所有选择区域"""
        self.event_handler.clear_selections()

    def getSelections(self) -> List[Tuple[int, int, int, int]]:
        """获取所有选择区域（原图坐标系）"""
        return self.event_handler.get_selections()

    def resizeEvent(self, event):
        """窗口大小变化时重新计算缩放"""
        super().resizeEvent(event)
        if self.original_pixmap:
            self._update_scaled_pixmap()

    def _emit_selection_changed(self, selections: List):
        """发送选择区域变化信号"""
        self.selection_changed.emit(selections)
