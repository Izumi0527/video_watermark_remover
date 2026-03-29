#!/usr/bin/env python3
"""
图像修复参数Tab页面
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
                "LaMa 深度学习修复（推荐）",
                "兼容 U-Net 深度修复（旧模型）",
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

        # 混合修复（P1：小水印走 OpenCV，速度优先；大水印仍走 LaMa）
        mixed_group = QGroupBox("混合修复（提速）")
        mixed_layout = QFormLayout(mixed_group)

        parent_widget.enable_mixed_inpainting_check = QCheckBox(
            "启用混合修复：小水印优先走 OpenCV（更快），大水印仍使用深度修复"
        )
        parent_widget.enable_mixed_inpainting_check.setChecked(False)
        mixed_layout.addRow("", parent_widget.enable_mixed_inpainting_check)

        parent_widget.mixed_inpainting_area_percent_spin = QDoubleSpinBox()
        parent_widget.mixed_inpainting_area_percent_spin.setMinimum(0.01)
        parent_widget.mixed_inpainting_area_percent_spin.setMaximum(5.0)
        parent_widget.mixed_inpainting_area_percent_spin.setDecimals(2)
        parent_widget.mixed_inpainting_area_percent_spin.setSingleStep(0.05)
        parent_widget.mixed_inpainting_area_percent_spin.setValue(0.30)
        parent_widget.mixed_inpainting_area_percent_spin.setSuffix(" %")
        mixed_layout.addRow("小水印阈值:", parent_widget.mixed_inpainting_area_percent_spin)

        parent_widget.mixed_inpainting_opencv_method_combo = QComboBox()
        parent_widget.mixed_inpainting_opencv_method_combo.addItem("TELEA 快速修复", "telea")
        parent_widget.mixed_inpainting_opencv_method_combo.addItem(
            "Navier-Stokes 高质量", "navier_stokes"
        )
        mixed_layout.addRow("OpenCV 方法:", parent_widget.mixed_inpainting_opencv_method_combo)

        mixed_layout.addRow(
            "",
            QLabel("说明：阈值表示掩码面积占画面比例；质量等级越高，系统会自动更保守地使用 OpenCV。"),
        )

        layout.addWidget(mixed_group)
        layout.addStretch()

        return tab
