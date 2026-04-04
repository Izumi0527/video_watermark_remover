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
        parent_widget.configure_panel_combo_box(
            parent_widget.detection_method_combo,
            minimum_contents_length=18,
            tooltip="选择检测后端。推荐使用 auto，在 GPU 不可用时会更稳妥地回退。",
        )
        # 说明：不同 PyQt6/Qt 版本对 SizeAdjustPolicy 的枚举值支持不完全一致；
        # 这里做兼容处理，避免启动时因属性不存在而崩溃。
        size_policy = getattr(
            QComboBox.SizeAdjustPolicy, "AdjustToMinimumContentsLength", None
        ) or getattr(QComboBox.SizeAdjustPolicy, "AdjustToMinimumContentsLengthWithIcon", None)
        if size_policy is not None and hasattr(
            parent_widget.detection_method_combo, "setMinimumContentsLength"
        ):
            parent_widget.detection_method_combo.setSizeAdjustPolicy(size_policy)
        method_layout.addRow("检测方法:", parent_widget.detection_method_combo)

        parent_widget.min_area_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.min_area_spin,
            tooltip="过滤过小的检测框，降低噪点误检进入修复流程的概率。",
        )
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

        parent_widget.enable_mask_shrink_check = QCheckBox("启用掩码收缩（减少误伤）")
        parent_widget.enable_mask_shrink_check.setToolTip("收缩掩码边界，减少误伤并降低修复负载；边界偏小的水印不建议开启。")
        parent_widget.enable_mask_shrink_check.setChecked(False)
        mask_layout.addRow("", parent_widget.enable_mask_shrink_check)

        parent_widget.mask_shrink_pixels_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.mask_shrink_pixels_spin,
            tooltip="收缩掩码边界像素，数值越大越保守。",
        )
        parent_widget.mask_shrink_pixels_spin.setMinimum(0)
        parent_widget.mask_shrink_pixels_spin.setMaximum(10)
        parent_widget.mask_shrink_pixels_spin.setValue(1)
        parent_widget.mask_shrink_pixels_spin.setSpecialValueText("不收缩")
        parent_widget.mask_shrink_pixels_spin.setSuffix(" px")
        mask_layout.addRow("收缩强度:", parent_widget.mask_shrink_pixels_spin)

        parent_widget.enable_mask_tracking_check = QCheckBox("启用静态水印跟踪（降低检测频率）")
        parent_widget.enable_mask_tracking_check.setToolTip("静态/轻微移动水印可复用掩码减少检测；动态水印建议关闭或减小间隔。")
        parent_widget.enable_mask_tracking_check.setChecked(False)
        mask_layout.addRow("", parent_widget.enable_mask_tracking_check)

        parent_widget.mask_tracking_interval_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.mask_tracking_interval_spin,
            tooltip="控制静态水印场景下的重新检测频率。",
        )
        parent_widget.mask_tracking_interval_spin.setMinimum(1)
        parent_widget.mask_tracking_interval_spin.setMaximum(30)
        parent_widget.mask_tracking_interval_spin.setValue(3)
        parent_widget.mask_tracking_interval_spin.setSuffix(" 帧")
        mask_layout.addRow("重新检测间隔:", parent_widget.mask_tracking_interval_spin)

        tracking_hint_label = QLabel("说明：适合静态水印；动态水印建议关闭/减小间隔。")
        tracking_hint_label.setWordWrap(True)
        tracking_hint_label.setToolTip("静态/轻微移动水印可复用掩码减少检测；动态水印建议关闭或减小间隔。")
        mask_layout.addRow("", tracking_hint_label)
        layout.addWidget(mask_group)
        layout.addStretch()

        return tab
