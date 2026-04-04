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

import logging
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ....config.advanced_params import AdvancedParamsSnapshot

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
        self.logger = logging.getLogger(__name__)
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
        self.enable_mask_shrink_check: Optional["QCheckBox"] = None
        self.mask_shrink_pixels_spin: Optional["QSpinBox"] = None
        self.enable_mask_tracking_check: Optional["QCheckBox"] = None
        self.mask_tracking_interval_spin: Optional["QSpinBox"] = None
        self.mask_tracking_max_missing_detections_spin: Optional["QSpinBox"] = None
        self.mask_tracking_motion_iou_threshold_spin: Optional["QDoubleSpinBox"] = None
        self.mask_tracking_scene_shift_confirmation_frames_spin: Optional["QSpinBox"] = None
        self.inpainting_method_combo: Optional["QComboBox"] = None
        self.inpaint_radius_spin: Optional["QSpinBox"] = None
        self.quality_slider: Optional["QSlider"] = None
        self.quality_label: Optional["QLabel"] = None
        self.enable_smooth_check: Optional["QCheckBox"] = None
        self.enable_blend_check: Optional["QCheckBox"] = None
        self.enable_enhance_check: Optional["QCheckBox"] = None
        self.enable_mixed_inpainting_check: Optional["QCheckBox"] = None
        self.mixed_inpainting_area_percent_spin: Optional["QDoubleSpinBox"] = None
        self.mixed_inpainting_opencv_method_combo: Optional["QComboBox"] = None
        self.processing_mode_combo: Optional["QComboBox"] = None
        self.worker_count_spin: Optional["QSpinBox"] = None
        self.thread_count_spin: Optional["QSpinBox"] = None
        self.enable_gpu_check: Optional["QCheckBox"] = None
        self.gpu_memory_spin: Optional["QSpinBox"] = None
        self.cache_size_spin: Optional["QSpinBox"] = None
        self.enable_cache_check: Optional["QCheckBox"] = None
        self.batch_max_concurrent_files_spin: Optional["QSpinBox"] = None
        self.batch_auto_retry_failed_check: Optional["QCheckBox"] = None
        self.batch_max_retry_count_spin: Optional["QSpinBox"] = None
        self.output_format_combo: Optional["QComboBox"] = None
        self.compression_slider: Optional["QSlider"] = None
        self.compression_label: Optional["QLabel"] = None
        self.add_suffix_check: Optional["QCheckBox"] = None
        self.add_timestamp_check: Optional["QCheckBox"] = None
        self.preserve_audio_check: Optional["QCheckBox"] = None

        self._init_ui()
        self._connect_signals()
        self._load_default_parameters()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 统一间距，与其他面板保持一致

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

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

    def configure_panel_combo_box(
        self,
        combo_box: QComboBox,
        *,
        object_name: str = "panel_combobox",
        minimum_height: int = 34,
        minimum_contents_length: Optional[int] = None,
        tooltip: Optional[str] = None,
    ) -> None:
        """统一配置参数面板中的下拉框外观与交互细节。"""
        combo_box.setObjectName(object_name)
        combo_box.setMinimumHeight(minimum_height)
        combo_box.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if combo_box.view() is not None:
            combo_box.view().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if tooltip:
            combo_box.setToolTip(tooltip)
        if minimum_contents_length is not None and hasattr(combo_box, "setMinimumContentsLength"):
            combo_box.setMinimumContentsLength(minimum_contents_length)

    def configure_panel_spin_box(
        self,
        spin_box: QAbstractSpinBox,
        *,
        object_name: str = "panel_spinbox",
        minimum_height: int = 34,
        tooltip: Optional[str] = None,
    ) -> None:
        """统一配置参数面板中的数值输入控件。"""
        spin_box.setObjectName(object_name)
        spin_box.setMinimumHeight(minimum_height)
        if tooltip:
            spin_box.setToolTip(tooltip)

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
        if self.enable_mask_shrink_check:
            self.enable_mask_shrink_check.toggled.connect(self._on_parameter_changed)
        if self.mask_shrink_pixels_spin:
            self.mask_shrink_pixels_spin.valueChanged.connect(self._on_parameter_changed)
        if self.enable_mask_tracking_check:
            self.enable_mask_tracking_check.toggled.connect(self._on_parameter_changed)
        if self.mask_tracking_interval_spin:
            self.mask_tracking_interval_spin.valueChanged.connect(self._on_parameter_changed)
        if self.mask_tracking_max_missing_detections_spin:
            self.mask_tracking_max_missing_detections_spin.valueChanged.connect(
                self._on_parameter_changed
            )
        if self.mask_tracking_motion_iou_threshold_spin:
            self.mask_tracking_motion_iou_threshold_spin.valueChanged.connect(
                self._on_parameter_changed
            )
        if self.mask_tracking_scene_shift_confirmation_frames_spin:
            self.mask_tracking_scene_shift_confirmation_frames_spin.valueChanged.connect(
                self._on_parameter_changed
            )

        # 修复参数信号
        if self.inpainting_method_combo:
            self.inpainting_method_combo.currentTextChanged.connect(self._on_parameter_changed)
        if self.inpaint_radius_spin:
            self.inpaint_radius_spin.valueChanged.connect(self._on_parameter_changed)
        if self.quality_slider:
            self.quality_slider.valueChanged.connect(self._update_quality_label)
            self.quality_slider.valueChanged.connect(self._on_parameter_changed)
        if self.enable_mixed_inpainting_check:
            self.enable_mixed_inpainting_check.toggled.connect(self._on_parameter_changed)
        if self.mixed_inpainting_area_percent_spin:
            self.mixed_inpainting_area_percent_spin.valueChanged.connect(self._on_parameter_changed)
        if self.mixed_inpainting_opencv_method_combo:
            self.mixed_inpainting_opencv_method_combo.currentTextChanged.connect(
                self._on_parameter_changed
            )

        # 后处理选项信号
        if self.enable_smooth_check:
            self.enable_smooth_check.toggled.connect(self._on_parameter_changed)
        if self.enable_blend_check:
            self.enable_blend_check.toggled.connect(self._on_parameter_changed)
        if self.enable_enhance_check:
            self.enable_enhance_check.toggled.connect(self._on_parameter_changed)

        # 性能参数信号
        if self.processing_mode_combo:
            self.processing_mode_combo.currentTextChanged.connect(self._on_parameter_changed)
        if self.worker_count_spin:
            self.worker_count_spin.valueChanged.connect(self._on_parameter_changed)
        if self.thread_count_spin and self.thread_count_spin is not self.worker_count_spin:
            self.thread_count_spin.valueChanged.connect(self._on_parameter_changed)
        if self.enable_gpu_check:
            self.enable_gpu_check.toggled.connect(self._on_parameter_changed)
        if self.gpu_memory_spin:
            self.gpu_memory_spin.valueChanged.connect(self._on_parameter_changed)
        if self.cache_size_spin:
            self.cache_size_spin.valueChanged.connect(self._on_parameter_changed)
        if self.enable_cache_check:
            self.enable_cache_check.toggled.connect(self._on_parameter_changed)
        if self.batch_max_concurrent_files_spin:
            self.batch_max_concurrent_files_spin.valueChanged.connect(self._on_parameter_changed)
        if self.batch_auto_retry_failed_check:
            self.batch_auto_retry_failed_check.toggled.connect(self._on_parameter_changed)
        if self.batch_max_retry_count_spin:
            self.batch_max_retry_count_spin.valueChanged.connect(self._on_parameter_changed)

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
        if self.preserve_audio_check:
            self.preserve_audio_check.toggled.connect(self._on_parameter_changed)

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
        advanced_snapshot = AdvancedParamsSnapshot.from_dict(
            {
                "processing_mode": (
                    self.processing_mode_combo.currentData() if self.processing_mode_combo else None
                ),
                "worker_count": self.worker_count_spin.value() if self.worker_count_spin else 0,
                "enable_gpu": self.enable_gpu_check.isChecked() if self.enable_gpu_check else False,
                "gpu_memory_limit_mb": self.gpu_memory_spin.value() if self.gpu_memory_spin else 0,
                "enable_cache": (
                    self.enable_cache_check.isChecked() if self.enable_cache_check else False
                ),
                "cache_size_mb": self.cache_size_spin.value() if self.cache_size_spin else 0,
                "batch_max_concurrent_files": (
                    self.batch_max_concurrent_files_spin.value()
                    if self.batch_max_concurrent_files_spin
                    else 1
                ),
                "batch_auto_retry_failed": (
                    self.batch_auto_retry_failed_check.isChecked()
                    if self.batch_auto_retry_failed_check
                    else True
                ),
                "batch_max_retry_count": (
                    self.batch_max_retry_count_spin.value()
                    if self.batch_max_retry_count_spin
                    else 0
                ),
                "output_format": (
                    self.output_format_combo.currentText() if self.output_format_combo else "保持原格式"
                ),
                "compression_quality": (
                    self.compression_slider.value() if self.compression_slider else 85
                ),
                "add_suffix": self.add_suffix_check.isChecked() if self.add_suffix_check else True,
                "add_timestamp": (
                    self.add_timestamp_check.isChecked() if self.add_timestamp_check else False
                ),
                "preserve_audio": (
                    self.preserve_audio_check.isChecked() if self.preserve_audio_check else True
                ),
                "mask_tracking_max_missing_detections": (
                    self.mask_tracking_max_missing_detections_spin.value()
                    if self.mask_tracking_max_missing_detections_spin
                    else 1
                ),
                "mask_tracking_motion_iou_threshold": (
                    self.mask_tracking_motion_iou_threshold_spin.value()
                    if self.mask_tracking_motion_iou_threshold_spin
                    else 0.2
                ),
                "mask_tracking_scene_shift_confirmation_frames": (
                    self.mask_tracking_scene_shift_confirmation_frames_spin.value()
                    if self.mask_tracking_scene_shift_confirmation_frames_spin
                    else 1
                ),
            }
        )

        return {
            # 检测参数
            "detection_sensitivity": (
                (self.sensitivity_slider.value() / 100.0) if self.sensitivity_slider else 0.5
            ),
            "detection_method": (
                self.detection_method_combo.currentText() if self.detection_method_combo else ""
            ),
            "min_detection_area": self.min_area_spin.value() if self.min_area_spin else 0,
            "enable_blur_preprocess": (
                self.enable_blur_check.isChecked() if self.enable_blur_check else False
            ),
            "enable_sharp_preprocess": (
                self.enable_sharp_check.isChecked() if self.enable_sharp_check else False
            ),
            "enable_denoise_preprocess": (
                self.enable_denoise_check.isChecked() if self.enable_denoise_check else False
            ),
            "enable_mask_shrink": (
                self.enable_mask_shrink_check.isChecked()
                if self.enable_mask_shrink_check
                else False
            ),
            "mask_shrink_pixels": (
                self.mask_shrink_pixels_spin.value() if self.mask_shrink_pixels_spin else 0
            ),
            "enable_mask_tracking": (
                self.enable_mask_tracking_check.isChecked()
                if self.enable_mask_tracking_check
                else False
            ),
            "mask_tracking_interval": (
                self.mask_tracking_interval_spin.value() if self.mask_tracking_interval_spin else 3
            ),
            "mask_tracking_max_missing_detections": (
                self.mask_tracking_max_missing_detections_spin.value()
                if self.mask_tracking_max_missing_detections_spin
                else 1
            ),
            "mask_tracking_motion_iou_threshold": (
                self.mask_tracking_motion_iou_threshold_spin.value()
                if self.mask_tracking_motion_iou_threshold_spin
                else 0.2
            ),
            "mask_tracking_scene_shift_confirmation_frames": (
                self.mask_tracking_scene_shift_confirmation_frames_spin.value()
                if self.mask_tracking_scene_shift_confirmation_frames_spin
                else 1
            ),
            # 修复参数
            "inpainting_method": (
                self.inpainting_method_combo.currentText() if self.inpainting_method_combo else ""
            ),
            "inpainting_radius": (
                self.inpaint_radius_spin.value() if self.inpaint_radius_spin else 0
            ),
            "inpainting_quality": self.quality_slider.value() if self.quality_slider else 0,
            "enable_smooth_postprocess": (
                self.enable_smooth_check.isChecked() if self.enable_smooth_check else False
            ),
            "enable_blend_postprocess": (
                self.enable_blend_check.isChecked() if self.enable_blend_check else False
            ),
            "enable_enhance_postprocess": (
                self.enable_enhance_check.isChecked() if self.enable_enhance_check else False
            ),
            "enable_mixed_inpainting": (
                self.enable_mixed_inpainting_check.isChecked()
                if self.enable_mixed_inpainting_check
                else False
            ),
            "mixed_inpainting_area_percent": (
                self.mixed_inpainting_area_percent_spin.value()
                if self.mixed_inpainting_area_percent_spin
                else 0.30
            ),
            "mixed_inpainting_opencv_method": (
                self.mixed_inpainting_opencv_method_combo.currentData()
                if self.mixed_inpainting_opencv_method_combo
                else "telea"
            ),
            # 统一高级参数（性能 + 输出）
            **advanced_snapshot.to_ui_dict(),
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
            if "enable_mask_shrink" in parameters and self.enable_mask_shrink_check:
                self.enable_mask_shrink_check.setChecked(parameters["enable_mask_shrink"])
            if "mask_shrink_pixels" in parameters and self.mask_shrink_pixels_spin:
                self.mask_shrink_pixels_spin.setValue(int(parameters["mask_shrink_pixels"]))
            if "enable_mask_tracking" in parameters and self.enable_mask_tracking_check:
                self.enable_mask_tracking_check.setChecked(parameters["enable_mask_tracking"])
            if "mask_tracking_interval" in parameters and self.mask_tracking_interval_spin:
                self.mask_tracking_interval_spin.setValue(int(parameters["mask_tracking_interval"]))
            if (
                "mask_tracking_max_missing_detections" in parameters
                and self.mask_tracking_max_missing_detections_spin
            ):
                self.mask_tracking_max_missing_detections_spin.setValue(
                    int(parameters["mask_tracking_max_missing_detections"])
                )
            if (
                "mask_tracking_motion_iou_threshold" in parameters
                and self.mask_tracking_motion_iou_threshold_spin
            ):
                self.mask_tracking_motion_iou_threshold_spin.setValue(
                    float(parameters["mask_tracking_motion_iou_threshold"])
                )
            if (
                "mask_tracking_scene_shift_confirmation_frames" in parameters
                and self.mask_tracking_scene_shift_confirmation_frames_spin
            ):
                self.mask_tracking_scene_shift_confirmation_frames_spin.setValue(
                    int(parameters["mask_tracking_scene_shift_confirmation_frames"])
                )

            # 设置修复参数
            if "inpainting_method" in parameters and self.inpainting_method_combo:
                index = self.inpainting_method_combo.findText(parameters["inpainting_method"])
                if index >= 0:
                    self.inpainting_method_combo.setCurrentIndex(index)

            if "inpainting_radius" in parameters and self.inpaint_radius_spin:
                self.inpaint_radius_spin.setValue(parameters["inpainting_radius"])

            if "inpainting_quality" in parameters and self.quality_slider:
                self.quality_slider.setValue(parameters["inpainting_quality"])
            if "enable_mixed_inpainting" in parameters and self.enable_mixed_inpainting_check:
                self.enable_mixed_inpainting_check.setChecked(parameters["enable_mixed_inpainting"])
            if (
                "mixed_inpainting_area_percent" in parameters
                and self.mixed_inpainting_area_percent_spin
            ):
                self.mixed_inpainting_area_percent_spin.setValue(
                    float(parameters["mixed_inpainting_area_percent"])
                )
            if (
                "mixed_inpainting_opencv_method" in parameters
                and self.mixed_inpainting_opencv_method_combo
            ):
                index = self.mixed_inpainting_opencv_method_combo.findData(
                    parameters["mixed_inpainting_opencv_method"]
                )
                if index >= 0:
                    self.mixed_inpainting_opencv_method_combo.setCurrentIndex(index)

            # 设置后处理选项
            if "enable_smooth_postprocess" in parameters and self.enable_smooth_check:
                self.enable_smooth_check.setChecked(parameters["enable_smooth_postprocess"])
            if "enable_blend_postprocess" in parameters and self.enable_blend_check:
                self.enable_blend_check.setChecked(parameters["enable_blend_postprocess"])
            if "enable_enhance_postprocess" in parameters and self.enable_enhance_check:
                self.enable_enhance_check.setChecked(parameters["enable_enhance_postprocess"])

            # 设置性能参数
            performance_snapshot = AdvancedParamsSnapshot.from_dict(parameters)
            if self.processing_mode_combo:
                index = self.processing_mode_combo.findData(performance_snapshot.processing_mode)
                if index < 0:
                    # 兼容旧配置中的 auto：UI 已收敛为显式单值模式，这里安全回落到单进程。
                    index = self.processing_mode_combo.findData("single_process")
                if index >= 0:
                    self.processing_mode_combo.setCurrentIndex(index)
            if self.worker_count_spin:
                self.worker_count_spin.setValue(performance_snapshot.worker_count)
            if self.enable_gpu_check:
                self.enable_gpu_check.setChecked(performance_snapshot.enable_gpu)
            if self.gpu_memory_spin:
                self.gpu_memory_spin.setValue(performance_snapshot.gpu_memory_limit_mb)
            if self.cache_size_spin:
                self.cache_size_spin.setValue(performance_snapshot.cache_size_mb)
            if self.enable_cache_check:
                self.enable_cache_check.setChecked(performance_snapshot.enable_cache)
            if self.batch_max_concurrent_files_spin:
                self.batch_max_concurrent_files_spin.setValue(
                    performance_snapshot.batch_max_concurrent_files
                )
            if self.batch_auto_retry_failed_check:
                self.batch_auto_retry_failed_check.setChecked(
                    performance_snapshot.batch_auto_retry_failed
                )
            if self.batch_max_retry_count_spin:
                self.batch_max_retry_count_spin.setValue(performance_snapshot.batch_max_retry_count)

            if self.compression_slider:
                self.compression_slider.setValue(performance_snapshot.compression_quality)

            # 设置输出参数
            if self.output_format_combo:
                index = self.output_format_combo.findText(
                    performance_snapshot.to_ui_dict()["output_format"]
                )
                if index >= 0:
                    self.output_format_combo.setCurrentIndex(index)

            if self.add_suffix_check:
                self.add_suffix_check.setChecked(performance_snapshot.add_suffix)

            if self.add_timestamp_check:
                self.add_timestamp_check.setChecked(performance_snapshot.add_timestamp)

            if self.preserve_audio_check:
                self.preserve_audio_check.setChecked(performance_snapshot.preserve_audio)

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
            if self.enable_mask_shrink_check:
                self.enable_mask_shrink_check.toggled.disconnect(self._on_parameter_changed)
            if self.mask_shrink_pixels_spin:
                self.mask_shrink_pixels_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.enable_mask_tracking_check:
                self.enable_mask_tracking_check.toggled.disconnect(self._on_parameter_changed)
            if self.mask_tracking_interval_spin:
                self.mask_tracking_interval_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.mask_tracking_max_missing_detections_spin:
                self.mask_tracking_max_missing_detections_spin.valueChanged.disconnect(
                    self._on_parameter_changed
                )
            if self.mask_tracking_motion_iou_threshold_spin:
                self.mask_tracking_motion_iou_threshold_spin.valueChanged.disconnect(
                    self._on_parameter_changed
                )
            if self.mask_tracking_scene_shift_confirmation_frames_spin:
                self.mask_tracking_scene_shift_confirmation_frames_spin.valueChanged.disconnect(
                    self._on_parameter_changed
                )

            if self.inpainting_method_combo:
                self.inpainting_method_combo.currentTextChanged.disconnect(
                    self._on_parameter_changed
                )
            if self.inpaint_radius_spin:
                self.inpaint_radius_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.quality_slider:
                self.quality_slider.valueChanged.disconnect(self._update_quality_label)
                self.quality_slider.valueChanged.disconnect(self._on_parameter_changed)
            if self.enable_mixed_inpainting_check:
                self.enable_mixed_inpainting_check.toggled.disconnect(self._on_parameter_changed)
            if self.mixed_inpainting_area_percent_spin:
                self.mixed_inpainting_area_percent_spin.valueChanged.disconnect(
                    self._on_parameter_changed
                )
            if self.mixed_inpainting_opencv_method_combo:
                self.mixed_inpainting_opencv_method_combo.currentTextChanged.disconnect(
                    self._on_parameter_changed
                )

            if self.enable_smooth_check:
                self.enable_smooth_check.toggled.disconnect(self._on_parameter_changed)
            if self.enable_blend_check:
                self.enable_blend_check.toggled.disconnect(self._on_parameter_changed)
            if self.enable_enhance_check:
                self.enable_enhance_check.toggled.disconnect(self._on_parameter_changed)

            if self.processing_mode_combo:
                self.processing_mode_combo.currentTextChanged.disconnect(self._on_parameter_changed)
            if self.worker_count_spin:
                self.worker_count_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.thread_count_spin and self.thread_count_spin is not self.worker_count_spin:
                self.thread_count_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.enable_gpu_check:
                self.enable_gpu_check.toggled.disconnect(self._on_parameter_changed)
            if self.gpu_memory_spin:
                self.gpu_memory_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.cache_size_spin:
                self.cache_size_spin.valueChanged.disconnect(self._on_parameter_changed)
            if self.enable_cache_check:
                self.enable_cache_check.toggled.disconnect(self._on_parameter_changed)
            if self.batch_max_concurrent_files_spin:
                self.batch_max_concurrent_files_spin.valueChanged.disconnect(
                    self._on_parameter_changed
                )
            if self.batch_auto_retry_failed_check:
                self.batch_auto_retry_failed_check.toggled.disconnect(self._on_parameter_changed)
            if self.batch_max_retry_count_spin:
                self.batch_max_retry_count_spin.valueChanged.disconnect(self._on_parameter_changed)

            if self.output_format_combo:
                self.output_format_combo.currentTextChanged.disconnect(self._on_parameter_changed)
            if self.compression_slider:
                self.compression_slider.valueChanged.disconnect(self._update_compression_label)
                self.compression_slider.valueChanged.disconnect(self._on_parameter_changed)
            if self.add_suffix_check:
                self.add_suffix_check.toggled.disconnect(self._on_parameter_changed)
            if self.add_timestamp_check:
                self.add_timestamp_check.toggled.disconnect(self._on_parameter_changed)
            if self.preserve_audio_check:
                self.preserve_audio_check.toggled.disconnect(self._on_parameter_changed)
        except Exception as e:
            # 若部分信号未连接，不影响整体断开流程
            self.logger.debug(f"Signal disconnect warning: {e}")

    def reset_to_defaults(self):
        """重置为默认值"""
        advanced_defaults = AdvancedParamsSnapshot.defaults().to_ui_dict()
        default_params = {
            "detection_sensitivity": 0.5,
            "detection_method": "YOLO v11x 深度学习auto (推荐)",
            "min_detection_area": 100,
            "enable_blur_preprocess": True,
            "enable_sharp_preprocess": False,
            "enable_denoise_preprocess": True,
            "enable_mask_shrink": False,
            "mask_shrink_pixels": 1,
            "enable_mask_tracking": False,
            "mask_tracking_interval": 3,
            "mask_tracking_max_missing_detections": 1,
            "mask_tracking_motion_iou_threshold": 0.2,
            "mask_tracking_scene_shift_confirmation_frames": 1,
            "inpainting_method": "LaMa 深度学习修复（推荐）",
            "inpainting_radius": 3,
            "inpainting_quality": 3,
            "enable_smooth_postprocess": True,
            "enable_blend_postprocess": False,
            "enable_enhance_postprocess": False,
            "enable_mixed_inpainting": False,
            "mixed_inpainting_area_percent": 0.30,
            "mixed_inpainting_opencv_method": "telea",
            **advanced_defaults,
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
                snapshot = AdvancedParamsSnapshot.from_dict(current_params)
                persisted_params = {**current_params, **snapshot.to_dict()}
                # 保存参数到偏好设置
                for key, value in persisted_params.items():
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

                if hasattr(preferences, "get_advanced_params_snapshot"):
                    saved_params.update(preferences.get_advanced_params_snapshot().to_ui_dict())

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
