import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..widgets.advanced.advanced_parameters_widget import AdvancedParametersWidget
from .detailed_progress_widget import DetailedProgressWidget


class ControlPanel(QWidget):
    """
    控制面板组件
    处理水印去除、批处理和高级参数控制
    """

    # 信号定义
    start_processing_requested = pyqtSignal()
    stop_processing_requested = pyqtSignal()
    batch_processing_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._init_ui()

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

    def _create_processing_control_group(self, main_layout):
        """创建处理控制组"""
        control_group = QGroupBox("处理控制")
        control_group.setObjectName("processing_control_group")

        control_layout = QHBoxLayout(control_group)
        control_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        control_layout.setSpacing(8)

        # 开始处理按钮
        self.btn_start_processing = QPushButton("✨ 开始去除水印")
        self.btn_start_processing.setMinimumHeight(50)
        self.btn_start_processing.clicked.connect(self._on_start_processing)
        self.btn_start_processing.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )
        control_layout.addWidget(self.btn_start_processing)

        # 停止处理按钮
        self.btn_stop_processing = QPushButton("⏹️ 停止处理")
        self.btn_stop_processing.setMinimumHeight(50)
        self.btn_stop_processing.clicked.connect(self._on_stop_processing)
        self.btn_stop_processing.setEnabled(False)
        self.btn_stop_processing.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )
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
        """创建高级功能标签页组"""
        tabs_group = QGroupBox("高级功能")
        tabs_group.setObjectName("advanced_tabs_group")

        # tabs_group.setMinimumHeight(450) # Removed fixed height to allow layout to adapt
        tabs_layout = QVBoxLayout(tabs_group)
        tabs_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        tabs_layout.setSpacing(0)

        # 创建标签页容器
        self.advanced_tabs = QTabWidget()

        # 批处理标签页
        self._create_batch_processing_tab()

        # 参数控制标签页
        self._create_parameters_tab()

        tabs_layout.addWidget(self.advanced_tabs)
        main_layout.addWidget(tabs_group, 1)  # stretch=1，让高级功能占据所有剩余空间

    def _create_batch_processing_tab(self):
        """创建批处理标签页"""
        batch_tab = QWidget()
        batch_layout = QVBoxLayout(batch_tab)

        # 批处理按钮
        self.btn_batch_processing = QPushButton("📁 批量处理")
        self.btn_batch_processing.setMinimumHeight(40)
        self.btn_batch_processing.clicked.connect(self._on_batch_processing)
        self.btn_batch_processing.setToolTip("选择多个文件进行批量处理")
        batch_layout.addWidget(self.btn_batch_processing)

        # 占位符说明
        batch_info = QWidget()
        batch_info.setMinimumHeight(100)
        batch_layout.addWidget(batch_info)

        # batch_layout.addStretch()  # 移除：避免底部过多空白

        self.advanced_tabs.addTab(batch_tab, "📦 批处理")

    def _create_parameters_tab(self):
        """创建参数控制标签页"""
        params_tab = QWidget()
        params_layout = QVBoxLayout(params_tab)

        # 集成高级参数组件
        self.advanced_params_widget = AdvancedParametersWidget()
        params_layout.addWidget(self.advanced_params_widget)

        self.advanced_tabs.addTab(params_tab, "⚙️ 参数设置")

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

    def _on_batch_processing(self):
        """处理批处理按钮点击"""
        self.logger.debug("Batch processing requested")
        self.batch_processing_requested.emit()

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
        self.detailed_progress.reset()

    def update_detailed_progress(self, progress_data: dict):
        """
        更新详细进度信息 (Phase 4 Stage 1.4)

        Args:
            progress_data: 详细进度数据字典
        """
        self.detailed_progress.update_progress(progress_data)

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
