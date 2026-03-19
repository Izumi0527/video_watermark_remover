import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..widgets.advanced.advanced_parameters_widget import AdvancedParametersWidget
from .detailed_progress_widget import DetailedProgressWidget


class ControlPanel(QWidget):
    """
    控制面板组件
    处理水印去除、批处理和高级参数控制

    采用信号驱动模式，组件间通过信号解耦
    """

    # 信号定义
    start_processing_requested = pyqtSignal()
    stop_processing_requested = pyqtSignal()

    # Phase 6: 进度更新信号（组件解耦）
    progress_update_requested = pyqtSignal(dict)
    progress_reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._init_ui()
        self._connect_internal_signals()

    def _init_ui(self):
        """初始化用户界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setObjectName("control_scroll_area")

        # 滚动区域的内容容器
        content_widget = QWidget()
        content_widget.setObjectName("control_content")
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # 创建处理控制组
        self._create_processing_control_group(self.content_layout)

        # 创建进度显示组
        self._create_progress_group(self.content_layout)

        # 创建高级功能标签页
        self._create_advanced_tabs_group(self.content_layout)

        # 移除弹簧，让"高级功能"自然扩展，避免底部过多空白
        # self.content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def _connect_internal_signals(self):
        """
        连接内部信号（Phase 6: 组件解耦）

        通过信号连接子组件，而非直接调用，提高可测试性和松耦合
        """
        # 进度更新信号 → DetailedProgressWidget
        self.progress_update_requested.connect(self.detailed_progress.update_progress)
        # 进度重置信号 → DetailedProgressWidget
        self.progress_reset_requested.connect(self.detailed_progress.reset)

    def _create_processing_control_group(self, main_layout):
        """创建处理控制组"""
        control_group = QGroupBox("处理控制")
        control_group.setObjectName("processing_control_group")

        control_layout = QHBoxLayout(control_group)
        control_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        control_layout.setSpacing(8)

        # 开始处理按钮
        self.btn_start_processing = QPushButton("✨ 开始去除水印")
        self.btn_start_processing.setObjectName("btn_success")
        self.btn_start_processing.setMinimumHeight(50)
        self.btn_start_processing.clicked.connect(self._on_start_processing)
        control_layout.addWidget(self.btn_start_processing)

        # 停止处理按钮
        self.btn_stop_processing = QPushButton("⏹️ 停止处理")
        self.btn_stop_processing.setObjectName("btn_danger")
        self.btn_stop_processing.setMinimumHeight(50)
        self.btn_stop_processing.clicked.connect(self._on_stop_processing)
        self.btn_stop_processing.setEnabled(False)
        control_layout.addWidget(self.btn_stop_processing)

        main_layout.addWidget(control_group)

    def _create_progress_group(self, main_layout):
        """创建进度显示组 (Phase 4 Stage 1.4 - 增强版)"""
        progress_group = QGroupBox("处理进度")
        progress_group.setObjectName("progress_group")

        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        progress_layout.setSpacing(0)

        # 添加详细进度组件 (Phase 4 Stage 1.4)
        self.detailed_progress = DetailedProgressWidget()
        progress_layout.addWidget(self.detailed_progress)

        # 保留原有的简单进度条 (用于兼容性)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("simple_progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        # 隐藏简单进度条,使用详细进度组件代替
        self.progress_bar.hide()

        main_layout.addWidget(progress_group)

    def _create_advanced_tabs_group(self, main_layout):
        """创建参数设置组"""
        params_group = QGroupBox("参数设置")  # 标题改为"参数设置"
        params_group.setObjectName("parameters_group")

        params_layout = QVBoxLayout(params_group)
        params_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        params_layout.setSpacing(0)

        # 直接添加高级参数组件（不再嵌套QTabWidget）
        self.advanced_params_widget = AdvancedParametersWidget()
        params_layout.addWidget(self.advanced_params_widget)

        main_layout.addWidget(params_group, 1)  # stretch=1，让参数设置占据所有剩余空间

    def _on_start_processing(self):
        """处理开始处理按钮点击"""
        self.logger.debug("Start processing requested")
        self.btn_start_processing.setEnabled(False)
        self.btn_stop_processing.setEnabled(True)
        self.start_processing_requested.emit()

    def _on_stop_processing(self):
        """处理停止处理按钮点击"""
        self.logger.debug("Stop processing requested")
        self.btn_start_processing.setEnabled(True)
        self.btn_stop_processing.setEnabled(False)
        self.stop_processing_requested.emit()

    def set_start_button_enabled(self, enabled):
        """设置开始按钮是否可用"""
        self.btn_start_processing.setEnabled(enabled)

    def set_processing_state(self, is_processing):
        """设置处理状态"""
        self.btn_start_processing.setEnabled(not is_processing)
        self.btn_stop_processing.setEnabled(is_processing)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def reset_progress(self):
        """重置进度条"""
        self.progress_bar.setValue(0)
        # Phase 6: 通过信号解耦
        self.progress_reset_requested.emit()

    def update_detailed_progress(self, progress_data: dict):
        """
        更新详细进度信息 (Phase 4 Stage 1.4, Phase 6 信号解耦)

        Args:
            progress_data: 详细进度数据字典
        """
        # Phase 6: 通过信号发射，而非直接调用子组件方法
        self.progress_update_requested.emit(progress_data)

    def get_advanced_parameters(self):
        """
        获取高级参数配置

        Returns:
            dict: 包含所有高级参数的字典
        """
        if hasattr(self, "advanced_params_widget"):
            return self.advanced_params_widget.get_parameters()
        return {}

    def set_advanced_parameters(self, parameters: dict):
        """
        设置高级参数配置

        Args:
            parameters: 参数字典
        """
        if hasattr(self, "advanced_params_widget"):
            self.advanced_params_widget.set_parameters(parameters)
