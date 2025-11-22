#!/usr/bin/env python3
"""
高级处理参数控制界面 - 主Widget

提供以下功能：
1. 水印检测敏感度调节
2. 修复方法选择
3. 输出质量控制
4. 线程数设置
5. GPU加速开关
6. 缓存设置

作者: Claude Code Assistant
创建时间: 2025-01-31
版本: v1.0 (重构版)
"""

from typing import Any, Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QScrollArea, QTabWidget, QVBoxLayout, QWidget

# 导入Tab页面实现
from .advanced_parameters_tabs import (
    DetectionParametersTab,
    InpaintingParametersTab,
    OutputParametersTab,
    PerformanceParametersTab,
)


class AdvancedParametersWidget(QWidget):
    """
    高级处理参数控制组件

    提供详细的处理参数控制界面
    """

    # 信号定义
    parameters_changed = pyqtSignal(dict)  # 参数变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parameters = {}
        self.preferences = None

        self._init_ui()
        self._connect_signals()
        self._load_default_parameters()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # 创建标签页控件
        self.tab_widget = QTabWidget()

        # 创建各个参数页面
        detection_tab = DetectionParametersTab.create_tab(self)
        inpainting_tab = InpaintingParametersTab.create_tab(self)
        performance_tab = PerformanceParametersTab.create_tab(self)
        output_tab = OutputParametersTab.create_tab(self)

        # 添加到标签页
        self.tab_widget.addTab(detection_tab, "检测参数")
        self.tab_widget.addTab(inpainting_tab, "修复参数")
        self.tab_widget.addTab(performance_tab, "性能参数")
        self.tab_widget.addTab(output_tab, "输出参数")

        scroll_area.setWidget(self.tab_widget)
        layout.addWidget(scroll_area)

    def _connect_signals(self):
        """连接信号"""
        # 检测参数信号
        self.sensitivity_slider.valueChanged.connect(self._update_sensitivity_label)
        self.sensitivity_slider.valueChanged.connect(self._on_parameter_changed)
        self.detection_method_combo.currentTextChanged.connect(self._on_parameter_changed)
        self.min_area_spin.valueChanged.connect(self._on_parameter_changed)

        # 预处理选项信号
        self.enable_blur_check.toggled.connect(self._on_parameter_changed)
        self.enable_sharp_check.toggled.connect(self._on_parameter_changed)
        self.enable_denoise_check.toggled.connect(self._on_parameter_changed)

        # 修复参数信号
        self.inpainting_method_combo.currentTextChanged.connect(self._on_parameter_changed)
        self.inpaint_radius_spin.valueChanged.connect(self._on_parameter_changed)
        self.quality_slider.valueChanged.connect(self._update_quality_label)
        self.quality_slider.valueChanged.connect(self._on_parameter_changed)

        # 后处理选项信号
        self.enable_smooth_check.toggled.connect(self._on_parameter_changed)
        self.enable_blend_check.toggled.connect(self._on_parameter_changed)
        self.enable_enhance_check.toggled.connect(self._on_parameter_changed)

        # 性能参数信号
        self.thread_count_spin.valueChanged.connect(self._on_parameter_changed)
        self.enable_gpu_check.toggled.connect(self._on_parameter_changed)
        self.gpu_memory_spin.valueChanged.connect(self._on_parameter_changed)
        self.cache_size_spin.valueChanged.connect(self._on_parameter_changed)
        self.enable_cache_check.toggled.connect(self._on_parameter_changed)

        # 输出参数信号
        self.output_format_combo.currentTextChanged.connect(self._on_parameter_changed)
        self.compression_slider.valueChanged.connect(self._update_compression_label)
        self.compression_slider.valueChanged.connect(self._on_parameter_changed)
        self.add_suffix_check.toggled.connect(self._on_parameter_changed)
        self.add_timestamp_check.toggled.connect(self._on_parameter_changed)

    def _update_sensitivity_label(self, value):
        """更新敏感度标签"""
        self.sensitivity_label.setText(f"{value/100:.2f}")

    def _update_quality_label(self, value):
        """更新质量标签"""
        quality_names = ["最低", "低", "中等", "高", "最高"]
        self.quality_label.setText(quality_names[value - 1])

    def _update_compression_label(self, value):
        """更新压缩质量标签"""
        self.compression_label.setText(f"{value}%")

    def _on_parameter_changed(self):
        """参数变化处理"""
        self.parameters = self.get_parameters()
        self.parameters_changed.emit(self.parameters)

    def _load_default_parameters(self):
        """加载默认参数"""
        self.reset_to_defaults()

    def get_parameters(self) -> Dict[str, Any]:
        """获取当前参数"""
        return {
            # 检测参数
            "detection_sensitivity": self.sensitivity_slider.value() / 100.0,
            "detection_method": self.detection_method_combo.currentText(),
            "min_detection_area": self.min_area_spin.value(),
            "enable_blur_preprocess": self.enable_blur_check.isChecked(),
            "enable_sharp_preprocess": self.enable_sharp_check.isChecked(),
            "enable_denoise_preprocess": self.enable_denoise_check.isChecked(),
            # 修复参数
            "inpainting_method": self.inpainting_method_combo.currentText(),
            "inpainting_radius": self.inpaint_radius_spin.value(),
            "inpainting_quality": self.quality_slider.value(),
            "enable_smooth_postprocess": self.enable_smooth_check.isChecked(),
            "enable_blend_postprocess": self.enable_blend_check.isChecked(),
            "enable_enhance_postprocess": self.enable_enhance_check.isChecked(),
            # 性能参数
            "thread_count": self.thread_count_spin.value(),
            "enable_gpu": self.enable_gpu_check.isChecked(),
            "gpu_memory_limit": self.gpu_memory_spin.value(),
            "cache_size": self.cache_size_spin.value(),
            "enable_cache": self.enable_cache_check.isChecked(),
            # 输出参数
            "output_format": self.output_format_combo.currentText(),
            "compression_quality": self.compression_slider.value(),
            "add_suffix": self.add_suffix_check.isChecked(),
            "add_timestamp": self.add_timestamp_check.isChecked(),
        }

    def set_parameters(self, parameters: Dict[str, Any]):
        """设置参数"""
        # 暂时断开信号连接，避免循环触发
        self._disconnect_signals()

        try:
            # 设置检测参数
            if "detection_sensitivity" in parameters:
                self.sensitivity_slider.setValue(int(parameters["detection_sensitivity"] * 100))

            if "detection_method" in parameters:
                index = self.detection_method_combo.findText(parameters["detection_method"])
                if index >= 0:
                    self.detection_method_combo.setCurrentIndex(index)

            if "min_detection_area" in parameters:
                self.min_area_spin.setValue(parameters["min_detection_area"])

            # 设置预处理选项
            if "enable_blur_preprocess" in parameters:
                self.enable_blur_check.setChecked(parameters["enable_blur_preprocess"])
            if "enable_sharp_preprocess" in parameters:
                self.enable_sharp_check.setChecked(parameters["enable_sharp_preprocess"])
            if "enable_denoise_preprocess" in parameters:
                self.enable_denoise_check.setChecked(parameters["enable_denoise_preprocess"])

            # 设置修复参数
            if "inpainting_method" in parameters:
                index = self.inpainting_method_combo.findText(parameters["inpainting_method"])
                if index >= 0:
                    self.inpainting_method_combo.setCurrentIndex(index)

            if "inpainting_radius" in parameters:
                self.inpaint_radius_spin.setValue(parameters["inpainting_radius"])

            if "inpainting_quality" in parameters:
                self.quality_slider.setValue(parameters["inpainting_quality"])

            # 设置性能参数
            if "thread_count" in parameters:
                self.thread_count_spin.setValue(parameters["thread_count"])

            if "enable_gpu" in parameters:
                self.enable_gpu_check.setChecked(parameters["enable_gpu"])

            if "compression_quality" in parameters:
                self.compression_slider.setValue(parameters["compression_quality"])

        finally:
            # 重新连接信号
            self._connect_signals()

        # 更新标签
        self._update_sensitivity_label(self.sensitivity_slider.value())
        self._update_quality_label(self.quality_slider.value())
        self._update_compression_label(self.compression_slider.value())

    def _disconnect_signals(self):
        """断开所有信号连接"""
        # 这里可以添加断开信号的逻辑，如果需要的话
        pass

    def reset_to_defaults(self):
        """重置为默认值"""
        default_params = {
            "detection_sensitivity": 0.5,
            "detection_method": "YOLO v11s 深度学习 (推荐)",
            "min_detection_area": 100,
            "enable_blur_preprocess": True,
            "enable_sharp_preprocess": False,
            "enable_denoise_preprocess": True,
            "inpainting_method": "GPU 深度学习 U-Net (推荐)",
            "inpainting_radius": 3,
            "inpainting_quality": 3,
            "enable_smooth_postprocess": True,
            "enable_blend_postprocess": True,
            "enable_enhance_postprocess": False,
            "thread_count": 4,
            "enable_gpu": True,
            "gpu_memory_limit": 2048,
            "cache_size": 512,
            "enable_cache": True,
            "output_format": "保持原格式",
            "compression_quality": 85,
            "add_suffix": True,
            "add_timestamp": False,
        }

        self.set_parameters(default_params)
        self.parameters = default_params

        if self.preferences:
            try:
                self.preferences.save_preferences()
                print("[OK] 参数已重置为默认值")
            except Exception as e:
                print(f"[WARNING] 保存默认参数失败: {e}")

    def apply_parameters(self):
        """应用当前参数"""
        current_params = self.get_parameters()
        self.parameters = current_params
        self.parameters_changed.emit(current_params)

        if self.preferences:
            try:
                # 保存参数到偏好设置
                for key, value in current_params.items():
                    self.preferences.set_preference("advanced_params", key, value)
                self.preferences.save_preferences()
                print("[OK] 高级参数已应用")
            except Exception as e:
                print(f"[WARNING] 保存高级参数失败: {e}")

    def set_preferences_manager(self, preferences):
        """设置偏好设置管理器"""
        self.preferences = preferences

        # 从偏好设置中加载参数
        if preferences:
            try:
                saved_params = {}
                for key in self.get_parameters().keys():
                    value = preferences.get_preference("advanced_params", key)
                    if value is not None:
                        saved_params[key] = value

                if saved_params:
                    self.set_parameters(saved_params)
                    print("[OK] 已从偏好设置加载高级参数")

            except Exception as e:
                print(f"[WARNING] 加载高级参数失败: {e}")


# 示例用法
if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = AdvancedParametersWidget()
    widget.show()

    def on_params_changed(params):
        print(f"[INFO] 参数已更新: {len(params)} 个参数")

    widget.parameters_changed.connect(on_params_changed)

    sys.exit(app.exec())
