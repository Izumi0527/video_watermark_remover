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

"""

from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

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

        # 预先声明控件属性，便于类型检查与防止属性缺失
        self.sensitivity_slider: Optional["QSlider"] = None
        self.sensitivity_label: Optional["QLabel"] = None
        self.detection_method_combo: Optional["QComboBox"] = None
        self.min_area_spin: Optional["QSpinBox"] = None
        self.enable_blur_check: Optional["QCheckBox"] = None
        self.enable_sharp_check: Optional["QCheckBox"] = None
        self.enable_denoise_check: Optional["QCheckBox"] = None
        self.inpainting_method_combo: Optional["QComboBox"] = None
        self.inpaint_radius_spin: Optional["QSpinBox"] = None
        self.quality_slider: Optional["QSlider"] = None
        self.quality_label: Optional["QLabel"] = None
        self.enable_smooth_check: Optional["QCheckBox"] = None
        self.enable_blend_check: Optional["QCheckBox"] = None
        self.enable_enhance_check: Optional["QCheckBox"] = None
        self.thread_count_spin: Optional["QSpinBox"] = None
        self.enable_gpu_check: Optional["QCheckBox"] = None
        self.gpu_memory_spin: Optional["QSpinBox"] = None
        self.cache_size_spin: Optional["QSpinBox"] = None
        self.enable_cache_check: Optional["QCheckBox"] = None
        self.output_format_combo: Optional["QComboBox"] = None
        self.compression_slider: Optional["QSlider"] = None
        self.compression_label: Optional["QLabel"] = None
        self.add_suffix_check: Optional["QCheckBox"] = None
        self.add_timestamp_check: Optional["QCheckBox"] = None

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

    def _connect_signals(self):  # noqa: C901
        """连接信号"""
        # 先断开已存在的连接，避免重复绑定导致信号噪音
        self._disconnect_signals()

        # 检测参数信号
        if self.sensitivity_slider:
            self.sensitivity_slider.valueChanged.connect(self._update_sensitivity_label)
            self.sensitivity_slider.valueChanged.connect(self._on_parameter_changed)
        if self.detection_method_combo:
            self.detection_method_combo.currentTextChanged.connect(self._on_parameter_changed)
        if self.min_area_spin:
            self.min_area_spin.valueChanged.connect(self._on_parameter_changed)

        # 预处理选项信号
        if self.enable_blur_check:
            self.enable_blur_check.toggled.connect(self._on_parameter_changed)
        if self.enable_sharp_check:
            self.enable_sharp_check.toggled.connect(self._on_parameter_changed)
        if self.enable_denoise_check:
            self.enable_denoise_check.toggled.connect(self._on_parameter_changed)

        # 修复参数信号
        if self.inpainting_method_combo:
            self.inpainting_method_combo.currentTextChanged.connect(self._on_parameter_changed)
        if self.inpaint_radius_spin:
            self.inpaint_radius_spin.valueChanged.connect(self._on_parameter_changed)
        if self.quality_slider:
            self.quality_slider.valueChanged.connect(self._update_quality_label)
            self.quality_slider.valueChanged.connect(self._on_parameter_changed)

        # 后处理选项信号
        if self.enable_smooth_check:
            self.enable_smooth_check.toggled.connect(self._on_parameter_changed)
        if self.enable_blend_check:
            self.enable_blend_check.toggled.connect(self._on_parameter_changed)
        if self.enable_enhance_check:
            self.enable_enhance_check.toggled.connect(self._on_parameter_changed)

        # 性能参数信号
        if self.thread_count_spin:
            self.thread_count_spin.valueChanged.connect(self._on_parameter_changed)
        if self.enable_gpu_check:
            self.enable_gpu_check.toggled.connect(self._on_parameter_changed)
        if self.gpu_memory_spin:
            self.gpu_memory_spin.valueChanged.connect(self._on_parameter_changed)
        if self.cache_size_spin:
            self.cache_size_spin.valueChanged.connect(self._on_parameter_changed)
        if self.enable_cache_check:
            self.enable_cache_check.toggled.connect(self._on_parameter_changed)

        # 输出参数信号
        if self.output_format_combo:
            self.output_format_combo.currentTextChanged.connect(self._on_parameter_changed)
        if self.compression_slider:
            self.compression_slider.valueChanged.connect(self._update_compression_label)
            self.compression_slider.valueChanged.connect(self._on_parameter_changed)
        if self.add_suffix_check:
            self.add_suffix_check.toggled.connect(self._on_parameter_changed)
        if self.add_timestamp_check:
            self.add_timestamp_check.toggled.connect(self._on_parameter_changed)

    def _update_sensitivity_label(self, value):
        """更新敏感度标签"""
        if self.sensitivity_label:
            self.sensitivity_label.setText(f"{value / 100:.2f}")

    def _update_quality_label(self, value):
        """更新质量标签"""
        quality_names = ["最低", "低", "中等", "高", "最高"]
        if self.quality_label:
            self.quality_label.setText(quality_names[value - 1])

    def _update_compression_label(self, value):
        """更新压缩质量标签"""
        if self.compression_label:
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
            "detection_sensitivity": (self.sensitivity_slider.value() / 100.0)
            if self.sensitivity_slider
            else 0.5,
            "detection_method": self.detection_method_combo.currentText()
            if self.detection_method_combo
            else "",
            "min_detection_area": self.min_area_spin.value() if self.min_area_spin else 0,
            "enable_blur_preprocess": self.enable_blur_check.isChecked()
            if self.enable_blur_check
            else False,
            "enable_sharp_preprocess": self.enable_sharp_check.isChecked()
            if self.enable_sharp_check
            else False,
            "enable_denoise_preprocess": self.enable_denoise_check.isChecked()
            if self.enable_denoise_check
            else False,
            # 修复参数
            "inpainting_method": self.inpainting_method_combo.currentText()
            if self.inpainting_method_combo
            else "",
            "inpainting_radius": self.inpaint_radius_spin.value()
            if self.inpaint_radius_spin
            else 0,
            "inpainting_quality": self.quality_slider.value() if self.quality_slider else 0,
            "enable_smooth_postprocess": self.enable_smooth_check.isChecked()
            if self.enable_smooth_check
            else False,
            "enable_blend_postprocess": self.enable_blend_check.isChecked()
            if self.enable_blend_check
            else False,
            "enable_enhance_postprocess": self.enable_enhance_check.isChecked()
            if self.enable_enhance_check
            else False,
            # 性能参数
            "thread_count": self.thread_count_spin.value() if self.thread_count_spin else 0,
            "enable_gpu": self.enable_gpu_check.isChecked() if self.enable_gpu_check else False,
            "gpu_memory_limit": self.gpu_memory_spin.value() if self.gpu_memory_spin else 0,
            "cache_size": self.cache_size_spin.value() if self.cache_size_spin else 0,
            "enable_cache": self.enable_cache_check.isChecked()
            if self.enable_cache_check
            else False,
            # 输出参数
            "output_format": self.output_format_combo.currentText()
            if self.output_format_combo
            else "",
            "compression_quality": self.compression_slider.value()
            if self.compression_slider
            else 0,
            "add_suffix": self.add_suffix_check.isChecked() if self.add_suffix_check else False,
            "add_timestamp": self.add_timestamp_check.isChecked()
            if self.add_timestamp_check
            else False,
        }

    def set_parameters(self, parameters: Dict[str, Any]):  # noqa: C901
        """设置参数"""
        # 暂时断开信号连接，避免循环触发
        self._disconnect_signals()

        try:
            # 设置检测参数
            if "detection_sensitivity" in parameters and self.sensitivity_slider:
                self.sensitivity_slider.setValue(int(parameters["detection_sensitivity"] * 100))

            if "detection_method" in parameters and self.detection_method_combo:
                index = self.detection_method_combo.findText(parameters["detection_method"])
                if index >= 0:
                    self.detection_method_combo.setCurrentIndex(index)

            if "min_detection_area" in parameters and self.min_area_spin:
                self.min_area_spin.setValue(parameters["min_detection_area"])

            # 设置预处理选项
            if "enable_blur_preprocess" in parameters and self.enable_blur_check:
                self.enable_blur_check.setChecked(parameters["enable_blur_preprocess"])
            if "enable_sharp_preprocess" in parameters and self.enable_sharp_check:
                self.enable_sharp_check.setChecked(parameters["enable_sharp_preprocess"])
            if "enable_denoise_preprocess" in parameters and self.enable_denoise_check:
                self.enable_denoise_check.setChecked(parameters["enable_denoise_preprocess"])

            # 设置修复参数
            if "inpainting_method" in parameters and self.inpainting_method_combo:
                index = self.inpainting_method_combo.findText(parameters["inpainting_method"])
                if index >= 0:
                    self.inpainting_method_combo.setCurrentIndex(index)

            if "inpainting_radius" in parameters and self.inpaint_radius_spin:
                self.inpaint_radius_spin.setValue(parameters["inpainting_radius"])

            if "inpainting_quality" in parameters and self.quality_slider:
                self.quality_slider.setValue(parameters["inpainting_quality"])

            # 设置后处理选项
            if "enable_smooth_postprocess" in parameters and self.enable_smooth_check:
                self.enable_smooth_check.setChecked(parameters["enable_smooth_postprocess"])
            if "enable_blend_postprocess" in parameters and self.enable_blend_check:
                self.enable_blend_check.setChecked(parameters["enable_blend_postprocess"])
            if "enable_enhance_postprocess" in parameters and self.enable_enhance_check:
                self.enable_enhance_check.setChecked(parameters["enable_enhance_postprocess"])

            # 设置性能参数
            if "thread_count" in parameters and self.thread_count_spin:
                self.thread_count_spin.setValue(parameters["thread_count"])

            if "enable_gpu" in parameters and self.enable_gpu_check:
                self.enable_gpu_check.setChecked(parameters["enable_gpu"])

            if "gpu_memory_limit" in parameters and self.gpu_memory_spin:
                self.gpu_memory_spin.setValue(parameters["gpu_memory_limit"])

            if "cache_size" in parameters and self.cache_size_spin:
                self.cache_size_spin.setValue(parameters["cache_size"])

            if "enable_cache" in parameters and self.enable_cache_check:
                self.enable_cache_check.setChecked(parameters["enable_cache"])

            if "compression_quality" in parameters and self.compression_slider:
                self.compression_slider.setValue(parameters["compression_quality"])

            # 设置输出参数
            if "output_format" in parameters and self.output_format_combo:
                index = self.output_format_combo.findText(parameters["output_format"])
                if index >= 0:
                    self.output_format_combo.setCurrentIndex(index)

            if "add_suffix" in parameters and self.add_suffix_check:
                self.add_suffix_check.setChecked(parameters["add_suffix"])

            if "add_timestamp" in parameters and self.add_timestamp_check:
                self.add_timestamp_check.setChecked(parameters["add_timestamp"])

        finally:
            # 重新连接信号
            self._connect_signals()

        # 更新标签
        if self.sensitivity_slider:
            self._update_sensitivity_label(self.sensitivity_slider.value())
        if self.quality_slider:
            self._update_quality_label(self.quality_slider.value())
        if self.compression_slider:
            self._update_compression_label(self.compression_slider.value())

    def _disconnect_signals(self):  # noqa: C901
        """断开所有信号连接"""
        try:
            if self.sensitivity_slider:
                self.sensitivity_slider.valueChanged.disconnect(self._update_sensitivity_label)
                self.sensitivity_slider.valueChanged.disconnect(self._on_parameter_changed)
            if self.detection_method_combo:
                self.detection_method_combo.currentTextChanged.disconnect(
                    self._on_parameter_changed
                )
            if self.min_area_spin:
                self.min_area_spin.valueChanged.disconnect(self._on_parameter_changed)

            if self.enable_blur_check:
                self.enable_blur_check.toggled.disconnect(self._on_parameter_changed)
            if self.enable_sharp_check:
                self.enable_sharp_check.toggled.disconnect(self._on_parameter_changed)
            if self.enable_denoise_check:
                self.enable_denoise_check.toggled.disconnect(self._on_parameter_changed)

            if self.inpainting_method_combo:
                self.inpainting_method_combo.currentTextChanged.disconnect(
                    self._on_parameter_changed
                )
            if self.inpaint_radius_spin:
                self.inpaint_radius_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.quality_slider:
                self.quality_slider.valueChanged.disconnect(self._update_quality_label)
                self.quality_slider.valueChanged.disconnect(self._on_parameter_changed)

            if self.enable_smooth_check:
                self.enable_smooth_check.toggled.disconnect(self._on_parameter_changed)
            if self.enable_blend_check:
                self.enable_blend_check.toggled.disconnect(self._on_parameter_changed)
            if self.enable_enhance_check:
                self.enable_enhance_check.toggled.disconnect(self._on_parameter_changed)

            if self.thread_count_spin:
                self.thread_count_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.enable_gpu_check:
                self.enable_gpu_check.toggled.disconnect(self._on_parameter_changed)
            if self.gpu_memory_spin:
                self.gpu_memory_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.cache_size_spin:
                self.cache_size_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.enable_cache_check:
                self.enable_cache_check.toggled.disconnect(self._on_parameter_changed)

            if self.output_format_combo:
                self.output_format_combo.currentTextChanged.disconnect(self._on_parameter_changed)
            if self.compression_slider:
                self.compression_slider.valueChanged.disconnect(self._update_compression_label)
                self.compression_slider.valueChanged.disconnect(self._on_parameter_changed)
            if self.add_suffix_check:
                self.add_suffix_check.toggled.disconnect(self._on_parameter_changed)
            if self.add_timestamp_check:
                self.add_timestamp_check.toggled.disconnect(self._on_parameter_changed)
        except Exception:
            # 若部分信号未连接，不影响整体断开流程
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
