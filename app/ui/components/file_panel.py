import logging
import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..widgets.batch.batch_processor_thread import ProcessingStatus


class FilePanel(QWidget):
    """
    文件操作面板组件
    处理文件选择、导出和主题切换等操作
    """

    # 信号定义
    file_import_requested = pyqtSignal()
    file_export_requested = pyqtSignal()
    theme_toggle_requested = pyqtSignal()
    auto_mode_changed = pyqtSignal(bool)
    manual_mode_changed = pyqtSignal(bool)
    queue_clear_requested = pyqtSignal()
    file_remove_requested = pyqtSignal(int)
    open_output_dir_requested = pyqtSignal(int)
    export_manifest_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._init_ui()

    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 统一顶部边距为0，确保与左侧预览区域对齐
        layout.setSpacing(8)  # 改为8dp，遵循栅格系统

        # 文件操作组
        self._create_file_operations_group(layout)

        # 处理模式组
        self._create_processing_mode_group(layout)

        # 文件队列组
        self._create_file_queue_group(layout)

    def _create_file_operations_group(self, main_layout):
        """创建文件操作组"""
        file_group = QGroupBox("文件操作")
        file_group.setObjectName("file_operations_group")

        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        file_layout.setSpacing(8)

        # 选择文件按钮
        self.btn_import = QPushButton("📂 选择文件")
        self.btn_import.setObjectName("btn_import")
        self.btn_import.setProperty("class", "primary")
        self.btn_import.clicked.connect(self._on_import_clicked)
        file_layout.addWidget(self.btn_import)

        # 导出结果按钮
        self.btn_export = QPushButton("💾 导出结果")
        self.btn_export.setObjectName("btn_export")
        self.btn_export.clicked.connect(self._on_export_clicked)
        self.btn_export.setEnabled(False)
        file_layout.addWidget(self.btn_export)

        # 主题切换按钮
        self.btn_theme_toggle = QPushButton("🌙 切换主题")
        self.btn_theme_toggle.setObjectName("btn_theme_toggle")
        self.btn_theme_toggle.clicked.connect(self._on_theme_toggle_clicked)
        self.btn_theme_toggle.setToolTip("在亮色和暗色主题之间切换")
        file_layout.addWidget(self.btn_theme_toggle)

        file_layout.addStretch()
        main_layout.addWidget(file_group)

    def _create_processing_mode_group(self, main_layout):
        """创建处理模式组"""
        mode_group = QGroupBox("处理模式")
        mode_group.setObjectName("processing_mode_group")

        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        mode_layout.setSpacing(8)

        # 自动检测模式
        self.auto_mode_checkbox = QCheckBox("🤖 自动检测水印")
        self.auto_mode_checkbox.setChecked(True)
        self.auto_mode_checkbox.toggled.connect(self._on_auto_mode_changed)
        mode_layout.addWidget(self.auto_mode_checkbox)

        # 手动选择模式
        self.manual_mode_checkbox = QCheckBox("✏️ 手动选择水印区域")
        self.manual_mode_checkbox.toggled.connect(self._on_manual_mode_changed)
        mode_layout.addWidget(self.manual_mode_checkbox)

        mode_layout.addStretch()
        main_layout.addWidget(mode_group)

    def _on_import_clicked(self):
        """处理文件导入按钮点击"""
        self.logger.debug("File import requested")
        self.file_import_requested.emit()

    def _on_export_clicked(self):
        """处理文件导出按钮点击"""
        self.logger.debug("File export requested")
        self.file_export_requested.emit()

    def _on_theme_toggle_clicked(self):
        """处理主题切换按钮点击"""
        self.logger.debug("Theme toggle requested")
        self.theme_toggle_requested.emit()

    def _on_auto_mode_changed(self, checked):
        """处理自动模式变化"""
        self.logger.debug(f"Auto mode changed: {checked}")
        if checked:
            self.manual_mode_checkbox.setChecked(False)
        self.auto_mode_changed.emit(checked)

    def _on_manual_mode_changed(self, checked):
        """处理手动模式变化"""
        self.logger.debug(f"Manual mode changed: {checked}")
        if checked:
            self.auto_mode_checkbox.setChecked(False)
        self.manual_mode_changed.emit(checked)

    def set_export_enabled(self, enabled):
        """设置导出按钮是否可用"""
        self.btn_export.setEnabled(enabled)

    def is_auto_mode(self):
        """检查是否为自动模式"""
        return self.auto_mode_checkbox.isChecked()

    def is_manual_mode(self):
        """检查是否为手动模式"""
        return self.manual_mode_checkbox.isChecked()

    def _create_file_queue_group(self, main_layout):
        """创建文件队列显示组"""
        self.queue_group = QGroupBox("文件队列")
        self.queue_group.setObjectName("file_queue_group")
        self.queue_group.setVisible(False)  # 初始隐藏

        queue_layout = QVBoxLayout(self.queue_group)
        queue_layout.setContentsMargins(8, 8, 8, 8)
        queue_layout.setSpacing(4)

        # 队列信息标签
        self.queue_info_label = QLabel("已选择 0 个文件")
        self.queue_info_label.setObjectName("queue_info_label")
        queue_layout.addWidget(self.queue_info_label)

        # 文件列表
        self.file_list_widget = QListWidget()
        self.file_list_widget.setMaximumHeight(120)
        queue_layout.addWidget(self.file_list_widget)

        # 操作按钮行
        btn_layout = QHBoxLayout()

        self.btn_remove_file = QPushButton("移除选中")
        self.btn_remove_file.clicked.connect(self._on_remove_file)
        btn_layout.addWidget(self.btn_remove_file)

        self.btn_clear_queue = QPushButton("清空队列")
        self.btn_clear_queue.clicked.connect(self._on_clear_queue)
        btn_layout.addWidget(self.btn_clear_queue)

        btn_layout.addStretch()
        queue_layout.addLayout(btn_layout)

        # 批量处理辅助操作（导出清单 / 打开输出目录）
        batch_action_layout = QHBoxLayout()

        self.btn_open_output_dir = QPushButton("📂 打开输出目录")
        self.btn_open_output_dir.setToolTip("打开选中文件（或第一个文件）的输出目录")
        self.btn_open_output_dir.clicked.connect(self._on_open_output_dir)
        batch_action_layout.addWidget(self.btn_open_output_dir)

        self.btn_export_manifest = QPushButton("📄 导出处理清单")
        self.btn_export_manifest.setToolTip("导出当前队列的处理清单（JSON）")
        self.btn_export_manifest.clicked.connect(self._on_export_manifest)
        batch_action_layout.addWidget(self.btn_export_manifest)

        batch_action_layout.addStretch()
        queue_layout.addLayout(batch_action_layout)

        main_layout.addWidget(self.queue_group)

    def update_queue_display(self, queue_data: list):
        """
        更新队列显示

        Args:
            queue_data: 队列数据列表，每项包含 input_path, status, progress
        """
        self.file_list_widget.clear()

        if not queue_data:
            self.queue_group.setVisible(False)
            return

        self.queue_group.setVisible(True)

        # 状态图标映射
        status_icons = {
            ProcessingStatus.WAITING: "⏳",
            ProcessingStatus.PROCESSING: "🔄",
            ProcessingStatus.COMPLETED: "✅",
            ProcessingStatus.FAILED: "❌",
            ProcessingStatus.CANCELLED: "⏹️",
        }

        for item in queue_data:
            filename = os.path.basename(item.get("input_path", ""))
            status = item.get("status")
            progress = item.get("progress", 0)

            # 处理中显示进度百分比
            if status == ProcessingStatus.PROCESSING:
                icon = f"🔄 {progress}%"
            else:
                icon = status_icons.get(status, "⏳")

            list_item = QListWidgetItem(f"{icon} {filename}")
            self.file_list_widget.addItem(list_item)

        # 更新统计信息
        total = len(queue_data)
        completed = sum(1 for i in queue_data if i.get("status") == ProcessingStatus.COMPLETED)
        failed = sum(1 for i in queue_data if i.get("status") == ProcessingStatus.FAILED)
        cancelled = sum(1 for i in queue_data if i.get("status") == ProcessingStatus.CANCELLED)

        self.queue_info_label.setText(
            f"文件队列: {total} 个 | 完成: {completed} | 失败: {failed} | 取消: {cancelled}"
        )

    def show_queue(self):
        """显示队列区域"""
        self.queue_group.setVisible(True)

    def hide_queue(self):
        """隐藏队列区域"""
        self.queue_group.setVisible(False)

    def _on_remove_file(self):
        """移除选中的文件"""
        current_row = self.file_list_widget.currentRow()
        if current_row >= 0:
            self.file_remove_requested.emit(current_row)

    def _on_clear_queue(self):
        """清空队列"""
        self.queue_clear_requested.emit()

    def _on_open_output_dir(self):
        """打开输出目录"""
        current_row = self.file_list_widget.currentRow()
        self.open_output_dir_requested.emit(current_row)

    def _on_export_manifest(self):
        """导出批处理清单"""
        self.export_manifest_requested.emit()
