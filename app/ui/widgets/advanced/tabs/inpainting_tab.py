#!/usr/bin/env python3
"""
图像修复参数Tab页面
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


class InpaintingParametersTab:
    """图像修复参数Tab页面"""

    @staticmethod
    def create_tab(parent_widget):
        """创建修复参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 修复方法组
        method_group = QGroupBox("修复方法")
        method_layout = QFormLayout(method_group)

        parent_widget.inpainting_method_combo = QComboBox()
        parent_widget.inpainting_method_combo.addItems(
            [
                "GPU 深度学习 U-Net (推荐)",
                "TELEA 快速修复 (OpenCV)",
                "Navier-Stokes 高质量 (OpenCV)",
                "自定义插值方法",
            ]
        )
        method_layout.addRow("修复算法:", parent_widget.inpainting_method_combo)

        parent_widget.inpaint_radius_spin = QSpinBox()
        parent_widget.inpaint_radius_spin.setMinimum(1)
        parent_widget.inpaint_radius_spin.setMaximum(10)
        parent_widget.inpaint_radius_spin.setValue(3)
        method_layout.addRow("修复半径:", parent_widget.inpaint_radius_spin)

        layout.addWidget(method_group)

        # 修复质量组
        quality_group = QGroupBox("修复质量")
        quality_layout = QFormLayout(quality_group)

        parent_widget.quality_slider = QSlider(Qt.Orientation.Horizontal)
        parent_widget.quality_slider.setMinimum(1)
        parent_widget.quality_slider.setMaximum(5)
        parent_widget.quality_slider.setValue(3)
        parent_widget.quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        parent_widget.quality_slider.setTickInterval(1)

        parent_widget.quality_label = QLabel("中等")
        quality_layout.addRow("质量等级:", parent_widget.quality_slider)
        quality_layout.addRow("当前等级:", parent_widget.quality_label)

        layout.addWidget(quality_group)

        # 后处理选项
        postprocess_group = QGroupBox("后处理选项")
        postprocess_layout = QVBoxLayout(postprocess_group)

        parent_widget.enable_smooth_check = QCheckBox("启用边缘平滑")
        parent_widget.enable_smooth_check.setChecked(True)
        postprocess_layout.addWidget(parent_widget.enable_smooth_check)

        parent_widget.enable_blend_check = QCheckBox("启用颜色混合")
        parent_widget.enable_blend_check.setChecked(True)
        postprocess_layout.addWidget(parent_widget.enable_blend_check)

        parent_widget.enable_enhance_check = QCheckBox("启用图像增强")
        postprocess_layout.addWidget(parent_widget.enable_enhance_check)

        layout.addWidget(postprocess_group)
        layout.addStretch()

        return tab
