import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


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
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 创建处理控制组
        self._create_processing_control_group(layout)

        # 创建进度显示组
        self._create_progress_group(layout)

        # 创建高级功能标签页
        self._create_advanced_tabs_group(layout)

    def _create_processing_control_group(self, main_layout):
        """创建处理控制组"""
        control_group = QGroupBox("处理控制")
        control_layout = QHBoxLayout(control_group)

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
        """创建进度显示组"""
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """
        )
        progress_layout.addWidget(self.progress_bar)

        main_layout.addWidget(progress_group)

    def _create_advanced_tabs_group(self, main_layout):
        """创建高级功能标签页组"""
        tabs_group = QGroupBox("高级功能")
        tabs_layout = QVBoxLayout(tabs_group)

        # 创建标签页容器
        self.advanced_tabs = QTabWidget()

        # 批处理标签页
        self._create_batch_processing_tab()

        # 参数控制标签页
        self._create_parameters_tab()

        tabs_layout.addWidget(self.advanced_tabs)
        main_layout.addWidget(tabs_group)

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

        batch_layout.addStretch()

        self.advanced_tabs.addTab(batch_tab, "📦 批处理")

    def _create_parameters_tab(self):
        """创建参数控制标签页"""
        params_tab = QWidget()
        params_layout = QVBoxLayout(params_tab)

        # 占位符 - 这里将来会集成AdvancedParametersWidget
        params_info = QWidget()
        params_info.setMinimumHeight(200)
        params_layout.addWidget(params_info)

        params_layout.addStretch()

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
