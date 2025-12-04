#!/usr/bin/env python3
"""
水印检测参数Tab页面
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class DetectionParametersTab:
    """水印检测参数Tab页面"""

    @staticmethod
    def create_tab(parent_widget):
        """创建检测参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 检测敏感度组
        sensitivity_group = QGroupBox("检测敏感度")
        sensitivity_layout = QFormLayout(sensitivity_group)

        parent_widget.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        parent_widget.sensitivity_slider.setMinimum(10)
        parent_widget.sensitivity_slider.setMaximum(100)
        parent_widget.sensitivity_slider.setValue(50)
        parent_widget.sensitivity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        parent_widget.sensitivity_slider.setTickInterval(10)

        parent_widget.sensitivity_label = QLabel("0.50")
        sensitivity_layout.addRow("敏感度:", parent_widget.sensitivity_slider)
        sensitivity_layout.addRow("当前值:", parent_widget.sensitivity_label)

        layout.addWidget(sensitivity_group)

        # 检测方法组
        method_group = QGroupBox("检测方法")
        method_layout = QFormLayout(method_group)

        parent_widget.detection_method_combo = QComboBox()
        parent_widget.detection_method_combo.addItems(
            [
                "YOLO v11s 深度学习 (推荐)",
                "YOLO v11s GPU 加速",
                "YOLO v11s CPU 模式",
            ]
        )
        method_layout.addRow("检测方法:", parent_widget.detection_method_combo)

        parent_widget.min_area_spin = QSpinBox()
        parent_widget.min_area_spin.setMinimum(1)
        parent_widget.min_area_spin.setMaximum(10000)
        parent_widget.min_area_spin.setValue(100)
        parent_widget.min_area_spin.setSuffix(" 像素")
        method_layout.addRow("最小检测区域:", parent_widget.min_area_spin)

        layout.addWidget(method_group)

        # 预处理选项
        preprocess_group = QGroupBox("预处理选项")
        preprocess_layout = QVBoxLayout(preprocess_group)

        parent_widget.enable_blur_check = QCheckBox("启用高斯模糊预处理")
        parent_widget.enable_blur_check.setChecked(True)
        preprocess_layout.addWidget(parent_widget.enable_blur_check)

        parent_widget.enable_sharp_check = QCheckBox("启用锐化预处理")
        preprocess_layout.addWidget(parent_widget.enable_sharp_check)

        parent_widget.enable_denoise_check = QCheckBox("启用降噪预处理")
        parent_widget.enable_denoise_check.setChecked(True)
        preprocess_layout.addWidget(parent_widget.enable_denoise_check)

        layout.addWidget(preprocess_group)
        layout.addStretch()

        return tab
