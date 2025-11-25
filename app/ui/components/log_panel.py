import logging
from datetime import datetime

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QWidget):
    """
    日志面板组件
    显示实时处理日志和状态信息
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._max_lines = 1000  # 最大显示行数
        self._init_ui()
        self._setup_log_handler()

    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 统一顶部边距为0，确保与左侧预览区域对齐
        layout.setSpacing(0)  # 统一间距设置

        # 限制日志面板的最大高度，让窗口更紧凑
        self.setMaximumHeight(280)

        # 创建日志显示组
        log_group = QGroupBox("处理日志")
        log_group.setObjectName("log_group")

        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        log_layout.setSpacing(0)

        # 日志控制栏
        self._create_log_controls(log_layout)

        # 日志文本区域
        self._create_log_text_area(log_layout)

        layout.addWidget(log_group)

    def _create_log_controls(self, parent_layout):
        """创建日志控制栏"""
        controls_layout = QHBoxLayout()

        # 日志级别选择
        level_label = QLabel("日志级别:")
        controls_layout.addWidget(level_label)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.currentTextChanged.connect(self._on_log_level_changed)
        controls_layout.addWidget(self.log_level_combo)

        controls_layout.addStretch()

        # 自动滚动选项
        self.auto_scroll_checkbox = QCheckBox("自动滚动")
        self.auto_scroll_checkbox.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_checkbox)

        # 清空日志按钮
        self.btn_clear_log = QPushButton("🗑️ 清空")
        self.btn_clear_log.setObjectName("btn_clear_log")
        self.btn_clear_log.clicked.connect(self._clear_log)
        self.btn_clear_log.setMaximumWidth(80)
        controls_layout.addWidget(self.btn_clear_log)

        # 保存日志按钮
        self.btn_save_log = QPushButton("💾 保存")
        self.btn_save_log.setObjectName("btn_save_log")
        self.btn_save_log.clicked.connect(self._save_log)
        self.btn_save_log.setMaximumWidth(80)
        controls_layout.addWidget(self.btn_save_log)

        parent_layout.addLayout(controls_layout)

    def _create_log_text_area(self, parent_layout):
        """创建日志文本显示区域"""
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMinimumHeight(200)

        # 设置字体
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.log_text_edit.setFont(font)

        # 设置样式
        self.log_text_edit.setObjectName("log_output")

        parent_layout.addWidget(self.log_text_edit)

        # 添加初始日志
        self._add_log_message("INFO", "🚀 日志系统已启动")

    def _setup_log_handler(self):
        """设置日志处理器"""
        # 这里可以添加自定义的日志处理器
        # 将日志消息重定向到本面板
        pass

    def _on_log_level_changed(self, level):
        """日志级别变化处理"""
        self.logger.info(f"Log level changed to: {level}")

    def _clear_log(self):
        """清空日志"""
        self.log_text_edit.clear()
        self._add_log_message("INFO", "📝 日志已清空")

    def _save_log(self):
        """保存日志到文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/processing_log_{timestamp}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.log_text_edit.toPlainText())

            self._add_log_message("INFO", f"📁 日志已保存到: {filename}")
        except Exception as e:
            self._add_log_message("ERROR", f"❌ 保存日志失败: {str(e)}")

    def _add_log_message(self, level, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 根据日志级别设置颜色
        # INFO 使用 None 以跟随主题默认字体颜色，解决亮色模式下不可见的问题
        color_map = {
            "DEBUG": "#888888",
            "INFO": None,
            "WARNING": "#ffaa00",
            "ERROR": "#ff4444",
        }

        color = color_map.get(level)

        # 格式化消息
        formatted_message = f'<span style="color: #888888">[{timestamp}]</span> '

        if color:
            formatted_message += (
                f'<span style="color: {color}; font-weight: bold">[{level}]</span> '
            )
            formatted_message += f'<span style="color: {color}">{message}</span>'
        else:
            # 无特定颜色（如 INFO），使用默认字体颜色（亮色模式为黑，暗色模式为白）
            formatted_message += f'<span style="font-weight: bold">[{level}]</span> '
            formatted_message += f"<span>{message}</span>"

        # 添加到文本区域
        cursor = self.log_text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(formatted_message + "<br>")

        # 控制最大行数
        self._limit_log_lines()

        # 自动滚动到底部
        if self.auto_scroll_checkbox.isChecked():
            self.log_text_edit.ensureCursorVisible()

    def _limit_log_lines(self):
        """限制日志行数"""
        document = self.log_text_edit.document()
        if document and document.blockCount() > self._max_lines:
            first_block = document.firstBlock()
            if first_block:
                cursor = QTextCursor(first_block)
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()

    @pyqtSlot(str)
    def add_info_log(self, message):
        """添加信息日志"""
        self._add_log_message("INFO", message)

    @pyqtSlot(str)
    def add_warning_log(self, message):
        """添加警告日志"""
        self._add_log_message("WARNING", message)

    @pyqtSlot(str)
    def add_error_log(self, message):
        """添加错误日志"""
        self._add_log_message("ERROR", message)

    @pyqtSlot(str)
    def add_debug_log(self, message):
        """添加调试日志"""
        if self.log_level_combo.currentText() == "DEBUG":
            self._add_log_message("DEBUG", message)

    def add_status_message(self, message):
        """添加状态消息（信息级别）"""
        self.add_info_log(f"📊 {message}")

    def add_progress_message(self, message):
        """添加进度消息"""
        self.add_info_log(f"⏳ {message}")

    def add_success_message(self, message):
        """添加成功消息"""
        self.add_info_log(f"✅ {message}")

    def add_error_message(self, message):
        """添加错误消息"""
        self.add_error_log(f"❌ {message}")
