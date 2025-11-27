#!/usr/bin/env python3
"""
高级处理参数控制界面 - Tab页面实现

包含各个参数控制Tab的具体实现：
1. 水印检测参数Tab
2. 图像修复参数Tab
3. 性能参数Tab
4. 输出参数Tab

"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
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


class PerformanceParametersTab:
    """性能参数Tab页面"""

    @staticmethod
    def create_tab(parent_widget):
        """创建性能参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 线程设置组
        thread_group = QGroupBox("线程设置")
        thread_layout = QFormLayout(thread_group)

        parent_widget.thread_count_spin = QSpinBox()
        parent_widget.thread_count_spin.setMinimum(1)
        parent_widget.thread_count_spin.setMaximum(16)
        parent_widget.thread_count_spin.setValue(4)
        parent_widget.thread_count_spin.setSpecialValueText("自动")
        thread_layout.addRow("处理线程数:", parent_widget.thread_count_spin)

        layout.addWidget(thread_group)

        # GPU加速组
        gpu_group = QGroupBox("GPU加速")
        gpu_layout = QVBoxLayout(gpu_group)

        parent_widget.enable_gpu_check = QCheckBox("启用GPU加速 (需要CUDA支持)")
        gpu_layout.addWidget(parent_widget.enable_gpu_check)

        parent_widget.gpu_memory_spin = QSpinBox()
        parent_widget.gpu_memory_spin.setMinimum(512)
        parent_widget.gpu_memory_spin.setMaximum(16384)
        parent_widget.gpu_memory_spin.setValue(2048)
        parent_widget.gpu_memory_spin.setSuffix(" MB")
        gpu_layout.addWidget(QLabel("GPU内存限制:"))
        gpu_layout.addWidget(parent_widget.gpu_memory_spin)

        layout.addWidget(gpu_group)

        # 缓存设置组
        cache_group = QGroupBox("缓存设置")
        cache_layout = QFormLayout(cache_group)

        parent_widget.cache_size_spin = QSpinBox()
        parent_widget.cache_size_spin.setMinimum(64)
        parent_widget.cache_size_spin.setMaximum(4096)
        parent_widget.cache_size_spin.setValue(512)
        parent_widget.cache_size_spin.setSuffix(" MB")
        cache_layout.addRow("缓存大小:", parent_widget.cache_size_spin)

        parent_widget.enable_cache_check = QCheckBox("启用结果缓存")
        parent_widget.enable_cache_check.setChecked(True)
        cache_layout.addRow("", parent_widget.enable_cache_check)

        layout.addWidget(cache_group)
        layout.addStretch()

        return tab


class OutputParametersTab:
    """输出参数Tab页面"""

    @staticmethod
    def create_tab(parent_widget):
        """创建输出参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 输出格式组
        format_group = QGroupBox("输出格式")
        format_layout = QFormLayout(format_group)

        parent_widget.output_format_combo = QComboBox()
        parent_widget.output_format_combo.addItems(["保持原格式", "JPG", "PNG", "BMP", "TIFF"])
        format_layout.addRow("输出格式:", parent_widget.output_format_combo)

        layout.addWidget(format_group)

        # 压缩设置组
        compression_group = QGroupBox("压缩设置")
        compression_layout = QFormLayout(compression_group)

        parent_widget.compression_slider = QSlider(Qt.Orientation.Horizontal)
        parent_widget.compression_slider.setMinimum(1)
        parent_widget.compression_slider.setMaximum(100)
        parent_widget.compression_slider.setValue(85)
        parent_widget.compression_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        parent_widget.compression_slider.setTickInterval(10)

        parent_widget.compression_label = QLabel("85%")
        compression_layout.addRow("压缩质量:", parent_widget.compression_slider)
        compression_layout.addRow("当前质量:", parent_widget.compression_label)

        layout.addWidget(compression_group)

        # 文件名设置组
        filename_group = QGroupBox("文件名设置")
        filename_layout = QVBoxLayout(filename_group)

        parent_widget.add_suffix_check = QCheckBox("添加处理后缀")
        parent_widget.add_suffix_check.setChecked(True)
        filename_layout.addWidget(parent_widget.add_suffix_check)

        parent_widget.add_timestamp_check = QCheckBox("添加时间戳")
        filename_layout.addWidget(parent_widget.add_timestamp_check)

        layout.addWidget(filename_group)
        layout.addStretch()

        return tab
