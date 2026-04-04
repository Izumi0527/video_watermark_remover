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
        parent_widget.configure_panel_combo_box(
            parent_widget.inpainting_method_combo,
            minimum_contents_length=18,
            tooltip="优先使用 LaMa 获取更自然的修复结果；OpenCV 方法适合小范围快速修补。",
        )
        # 说明：不同 PyQt6/Qt 版本对 SizeAdjustPolicy 的枚举值支持不完全一致；
        # 这里做兼容处理，避免启动时因属性不存在而崩溃。
        size_policy = getattr(
            QComboBox.SizeAdjustPolicy, "AdjustToMinimumContentsLength", None
        ) or getattr(QComboBox.SizeAdjustPolicy, "AdjustToMinimumContentsLengthWithIcon", None)
        if size_policy is not None and hasattr(
            parent_widget.inpainting_method_combo, "setMinimumContentsLength"
        ):
            parent_widget.inpainting_method_combo.setSizeAdjustPolicy(size_policy)
        method_layout.addRow("修复算法:", parent_widget.inpainting_method_combo)

        parent_widget.inpaint_radius_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.inpaint_radius_spin,
            tooltip="主要影响 OpenCV 修复算法的传播范围。",
        )
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

        parent_widget.enable_mixed_inpainting_check = QCheckBox("启用混合修复（小水印走 OpenCV 提速）")
        parent_widget.enable_mixed_inpainting_check.setToolTip(
            "小水印优先走 OpenCV（更快），大水印仍使用深度修复；可通过“小水印阈值”控制切换。"
        )
        parent_widget.enable_mixed_inpainting_check.setChecked(False)
        mixed_layout.addRow("", parent_widget.enable_mixed_inpainting_check)

        parent_widget.mixed_inpainting_area_percent_spin = QDoubleSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.mixed_inpainting_area_percent_spin,
            tooltip="控制多大面积以下的水印优先走 OpenCV 快速修复。",
        )
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
        parent_widget.configure_panel_combo_box(
            parent_widget.mixed_inpainting_opencv_method_combo,
            minimum_contents_length=16,
            tooltip="小水印默认可走更快的 OpenCV 修复路径；不同方法在速度和边缘自然度上各有偏向。",
        )
        mixed_layout.addRow("OpenCV 方法:", parent_widget.mixed_inpainting_opencv_method_combo)

        mixed_hint_label = QLabel("说明：阈值为掩码占比；质量越高越保守。")
        mixed_hint_label.setWordWrap(True)
        mixed_hint_label.setToolTip("阈值表示掩码面积占画面比例；质量等级越高，系统会更保守地使用 OpenCV。")
        mixed_layout.addRow("", mixed_hint_label)
        layout.addWidget(mixed_group)
        layout.addStretch()

        return tab
