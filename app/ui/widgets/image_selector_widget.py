#!/usr/bin/env python3
"""
图像选择器组件 - 重构版

提供完整的图像选择功能，使用模块化架构：
- selectable_image_label: 核心图像标签组件
- selection_handlers: 事件处理器
- coordinate_converter: 坐标转换工具

"""

import sys
from typing import TYPE_CHECKING, Any, List, Tuple

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from .selectable_image_label import SelectableImageLabel


class ImageSelectorWidget(QWidget):
    """
    图像选择器组件

    包含图像显示区域和控制按钮
    """

    # 选择区域变化信号
    selection_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 图像显示区域
        self.image_label = SelectableImageLabel()
        self.image_label.selection_changed.connect(self._on_selection_changed)

        # 使用滚动区域以支持大图像
        scroll_area = QScrollArea()
        scroll_area.setObjectName("image_scroll_area")
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        # 控制按钮区域
        control_layout = QHBoxLayout()

        self.clear_button = QPushButton("清空选择")
        self.clear_button.setObjectName("btn_clear")
        self.clear_button.clicked.connect(self.clearSelections)
        control_layout.addWidget(self.clear_button)

        self.info_label = QLabel("拖拽鼠标选择水印区域")
        self.info_label.setObjectName("info_label")
        control_layout.addWidget(self.info_label)

        control_layout.addStretch()

        layout.addLayout(control_layout)

    def setImage(self, image_path: str) -> bool:
        """设置图像"""
        result = self.image_label.setImage(image_path)
        if result:
            self.info_label.setText("拖拽鼠标选择水印区域")
        return result

    def setImageFromArray(self, image_array: "np.ndarray") -> bool:
        """从数组设置图像"""
        result = self.image_label.setImageFromArray(image_array)
        if result:
            self.info_label.setText("拖拽鼠标选择水印区域")
        return result

    def clearSelections(self):
        """清空选择"""
        self.image_label.clearSelections()

    def getSelections(self) -> List[Tuple[int, int, int, int]]:
        """获取选择区域"""
        return self.image_label.getSelections()

    def _on_selection_changed(self, selections: List):
        """选择区域变化处理"""
        count = len(selections)
        if count == 0:
            self.info_label.setText("拖拽鼠标选择水印区域")
        elif count == 1:
            self.info_label.setText(f"已选择 {count} 个水印区域")
        else:
            self.info_label.setText(f"已选择 {count} 个水印区域")

        # 转发信号
        self.selection_changed.emit(selections)


if __name__ == "__main__":
    """测试代码"""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建测试窗口
    widget = ImageSelectorWidget()
    widget.setWindowTitle("图像选择器测试 - 重构版")
    widget.resize(800, 600)
    widget.show()

    # 连接信号用于测试
    def on_selection_changed(selections):
        print(f"选择区域变化: {selections}")

    widget.selection_changed.connect(on_selection_changed)

    print("✅ 图像选择器重构版启动成功")
    print("模块化架构包含:")
    print("  - SelectableImageLabel: 核心图像显示组件")
    print("  - SelectionEventHandler: 鼠标事件处理")
    print("  - CoordinateConverter: 坐标转换工具")

    sys.exit(app.exec())
