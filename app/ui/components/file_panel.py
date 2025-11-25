import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget


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
