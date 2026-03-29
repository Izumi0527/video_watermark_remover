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
                "YOLO v11x 深度学习auto (推荐)",
                "YOLO v11x GPU 加速",
                "YOLO v11x CPU 模式",
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

        # 掩码优化（速度/误伤控制）
        mask_group = QGroupBox("掩码优化")
        mask_layout = QFormLayout(mask_group)

        parent_widget.enable_mask_shrink_check = QCheckBox("启用掩码收缩（减少误伤并降低修复负载）")
        parent_widget.enable_mask_shrink_check.setChecked(False)
        mask_layout.addRow("", parent_widget.enable_mask_shrink_check)

        parent_widget.mask_shrink_pixels_spin = QSpinBox()
        parent_widget.mask_shrink_pixels_spin.setMinimum(0)
        parent_widget.mask_shrink_pixels_spin.setMaximum(10)
        parent_widget.mask_shrink_pixels_spin.setValue(1)
        parent_widget.mask_shrink_pixels_spin.setSpecialValueText("不收缩")
        parent_widget.mask_shrink_pixels_spin.setSuffix(" px")
        mask_layout.addRow("收缩强度:", parent_widget.mask_shrink_pixels_spin)

        parent_widget.enable_mask_tracking_check = QCheckBox("启用静态水印跟踪（复用掩码以减少检测频率）")
        parent_widget.enable_mask_tracking_check.setChecked(False)
        mask_layout.addRow("", parent_widget.enable_mask_tracking_check)

        parent_widget.mask_tracking_interval_spin = QSpinBox()
        parent_widget.mask_tracking_interval_spin.setMinimum(1)
        parent_widget.mask_tracking_interval_spin.setMaximum(30)
        parent_widget.mask_tracking_interval_spin.setValue(3)
        parent_widget.mask_tracking_interval_spin.setSuffix(" 帧")
        mask_layout.addRow("重新检测间隔:", parent_widget.mask_tracking_interval_spin)

        mask_layout.addRow(
            "",
            QLabel("说明：适合静态/轻微移动水印；动态水印建议关闭或调小间隔。"),
        )

        layout.addWidget(mask_group)
        layout.addStretch()

        return tab
