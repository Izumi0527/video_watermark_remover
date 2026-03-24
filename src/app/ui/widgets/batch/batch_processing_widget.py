#!/usr/bin/env python3
"""
批量处理队列组件 - 主Widget

提供以下功能：
1. 文件队列管理
2. 批量添加文件
3. 队列进度显示
4. 自动依次处理
5. 处理状态跟踪

"""

from typing import Any, Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget

# 导入配置管理器
from app.config.config_manager import ConfigManager

from .batch_file_manager import BatchFileManager

# 导入拆分出的模块
from .batch_processor_thread import BatchProcessorThread, ProcessingStatus
from .batch_ui_components import BatchUIComponents


class BatchProcessingWidget(QWidget):
    """
    批量处理组件 - 重构版本

    提供批量文件处理的用户界面，使用模块化架构
    """

    # 信号定义
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化组件
        self.file_manager = BatchFileManager(self)
        self.batch_processor = None
        self.ai_params = {}
        self.config = None

        # AI模型预加载支持
        self.preloaded_ai_handler = None

        # 并发处理配置
        self.max_concurrent_files = 4  # 默认并发处理4个文件

        # 自动重试配置
        self.auto_retry_failed = True  # 默认自动重试
        self.max_retry_count = 3  # 默认重试次数
        self._stop_requested = False  # 批量停止请求标记（用于取消/完成口径分流）

        # UI组件引用
        self.ui_components = {}
        self.control_buttons = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化界面"""
        # 创建主布局和分割器
        layout, splitter = BatchUIComponents.create_main_layout()
        self.setLayout(layout)

        # 创建标题
        title_label = BatchUIComponents.create_title_label()
        layout.addWidget(title_label)

        # 创建控制按钮区域
        control_layout, self.control_buttons = BatchUIComponents.create_control_buttons()
        layout.addLayout(control_layout)

        # 创建文件队列组
        queue_group, file_list, queue_info_label = BatchUIComponents.create_file_queue_group()
        self.ui_components["file_list"] = file_list
        self.ui_components["queue_info_label"] = queue_info_label
        splitter.addWidget(queue_group)

        # 创建进度组
        progress_group, progress_components = BatchUIComponents.create_progress_group()
        self.ui_components.update(progress_components)
        splitter.addWidget(progress_group)

        layout.addWidget(splitter)

    def _connect_signals(self):
        """连接信号"""
        self.control_buttons["add_files"].clicked.connect(self.add_files)
        self.control_buttons["clear_queue"].clicked.connect(self.clear_queue)
        self.control_buttons["start_batch"].clicked.connect(self.start_batch_processing)
        self.control_buttons["stop_batch"].clicked.connect(self.stop_batch_processing)

    def set_ai_params(self, ai_params: Dict[str, Any]):
        """设置AI参数"""
        self.ai_params = ai_params

    def set_config(self, config):
        """设置配置并从中读取批处理参数"""
        self.config = config
        if config:
            # 从配置读取最大并发数
            self.max_concurrent_files = ConfigManager.get_batch_max_concurrent(config, default=4)
            # 读取自动重试设置
            self.auto_retry_failed = ConfigManager.get_batch_auto_retry(config, default=True)
            self.max_retry_count = ConfigManager.get_batch_max_retry_count(config, default=3)

    def set_preloaded_ai_handler(self, ai_handler):
        """
        设置预加载的AI处理器

        Args:
            ai_handler: 预加载的AIHandler实例，用于批量处理时复用
        """
        self.preloaded_ai_handler = ai_handler

    def set_max_concurrent_files(self, max_concurrent: int):
        """
        设置最大并发文件数

        Args:
            max_concurrent: 最大并发文件数（建议1-8，默认4）
        """
        self.max_concurrent_files = max(1, min(max_concurrent, 8))  # 限制在1-8之间

    def add_files(self):
        """添加文件到队列"""
        selected_files = self.file_manager.show_add_files_dialog()
        if selected_files:
            added_count = self.file_manager.add_files_batch(selected_files)
            if added_count > 0:
                self._update_queue_display()

    def clear_queue(self):
        """清空队列"""
        if self.file_manager.clear_queue_with_confirmation():
            self._update_queue_display()
            self._reset_ui_state()

    def start_batch_processing(self):
        """开始批量处理"""
        self._stop_requested = False
        queue_manager = self.file_manager.get_queue_manager()
        queue = queue_manager.get_queue()

        if not queue:
            QMessageBox.information(self, "提示", "队列为空，请先添加文件")
            return

        if self.batch_processor and self.batch_processor.isRunning():
            QMessageBox.warning(self, "警告", "批量处理正在进行中")
            return

        # 重置所有文件状态为等待
        self.file_manager.reset_all_files_to_waiting()

        # 创建并启动批量处理线程（支持预加载AI模型、并发处理和自动重试）
        self.batch_processor = BatchProcessorThread(
            queue=queue,
            ai_params=self.ai_params,
            config=self.config,
            preloaded_ai_handler=self.preloaded_ai_handler,  # 传递预加载的AI处理器
            max_concurrent_files=self.max_concurrent_files,  # 传递并发数配置
            auto_retry_failed=self.auto_retry_failed,  # 传递自动重试配置
            max_retry_count=self.max_retry_count,  # 传递最大重试次数
            parent=self,
        )

        # 连接信号
        self.batch_processor.current_file_changed.connect(self._on_current_file_changed)
        self.batch_processor.file_progress.connect(self._on_file_progress)
        self.batch_processor.overall_progress.connect(self._on_overall_progress)
        self.batch_processor.file_completed.connect(self._on_file_completed)
        self.batch_processor.batch_completed.connect(self._on_batch_completed)
        self.batch_processor.status_message.connect(self._on_status_message)

        self.batch_processor.start()

        # 更新UI状态
        self._set_processing_ui_state(True)
        self.processing_started.emit()

    def stop_batch_processing(self):
        """停止批量处理"""
        if self.batch_processor and self.batch_processor.isRunning():
            self._stop_requested = True
            self.batch_processor.stop()
            self.batch_processor.wait(5000)  # 等待最多5秒

            if self.batch_processor.isRunning():
                self.batch_processor.terminate()

            self._reset_ui_state()

    def _update_queue_display(self):
        """更新队列显示"""
        self.file_manager.update_queue_display(
            self.ui_components["file_list"], self.ui_components["queue_info_label"]
        )

    def _set_processing_ui_state(self, processing: bool):
        """设置处理状态的UI状态"""
        self.control_buttons["start_batch"].setEnabled(not processing)
        self.control_buttons["stop_batch"].setEnabled(processing)
        self.control_buttons["add_files"].setEnabled(not processing)
        self.control_buttons["clear_queue"].setEnabled(not processing)

    def _reset_ui_state(self):
        """重置UI状态 (Phase 4 Stage 1.4 - 增强版)"""
        self._set_processing_ui_state(False)
        self.ui_components["current_progress_bar"].setValue(0)
        self.ui_components["overall_progress_bar"].setValue(0)
        self._update_statistics()  # 更新统计信息

    def _update_statistics(self):
        """更新批量处理统计信息 (Phase 4 Stage 1.4)"""
        stats = self.file_manager.get_queue_statistics()

        # 更新统计标签
        self.ui_components["total_label"].setText(f"总计: {stats['total']}")
        self.ui_components["success_label"].setText(f"✅ 成功: {stats['completed']}")
        self.ui_components["failed_label"].setText(f"❌ 失败: {stats['failed']}")
        self.ui_components["waiting_label"].setText(f"⏳ 等待: {stats['waiting']}")
        self.ui_components["concurrent_label"].setText(f"🔄 处理中: {stats['processing']}")

    # 批量处理事件处理方法
    def _on_current_file_changed(self, index: int, filename: str):
        """当前处理文件变化 (Phase 4 Stage 1.4 - 增强版)"""
        self.ui_components["current_file_label"].setText(f"正在处理: {filename}")
        queue_manager = self.file_manager.get_queue_manager()
        queue_manager.update_file_status(index, ProcessingStatus.PROCESSING)
        self._update_queue_display()
        self._update_statistics()  # 更新统计信息

    def _on_file_progress(self, progress: int, file_index: int):
        """文件处理进度更新 (Phase 4 Stage 1.4 - 增强版)"""
        self.ui_components["current_progress_bar"].setValue(progress)
        queue_manager = self.file_manager.get_queue_manager()
        queue_manager.update_file_status(file_index, ProcessingStatus.PROCESSING, progress)
        self._update_queue_display()

    def _on_overall_progress(self, progress: int):
        """总体进度更新"""
        self.ui_components["overall_progress_bar"].setValue(progress)

    def _on_file_completed(
        self,
        index: int,
        output_path: str,
        status: object,
        error_message: str,
        processing_details: object,
    ) -> None:
        """文件处理完成 (Phase 4 Stage 1.4 - 增强版)"""
        final_status = status if isinstance(status, ProcessingStatus) else ProcessingStatus.FAILED
        queue_manager = self.file_manager.get_queue_manager()
        safe_error = str(error_message or "").strip()

        if processing_details is not None:
            queue_manager.update_file_processing_details(index, processing_details)

        if final_status == ProcessingStatus.CANCELLED:
            current = queue_manager.get_file_info(index) or {}
            current_progress = int(current.get("progress", 0) or 0)
            queue_manager.update_file_status(
                index, ProcessingStatus.CANCELLED, current_progress, safe_error or "用户取消"
            )
        elif final_status == ProcessingStatus.FAILED:
            queue_manager.update_file_status(
                index, ProcessingStatus.FAILED, 100, safe_error or "处理失败"
            )
        else:
            queue_manager.update_file_status(index, final_status, 100, "")

        self._update_queue_display()
        self._update_statistics()  # 更新统计信息

    def _on_batch_completed(self):
        """批量处理完成"""
        cancelled = self._stop_requested or (
            self.batch_processor is not None and getattr(self.batch_processor, "should_stop", False)
        )

        if cancelled:
            queue_manager = self.file_manager.get_queue_manager()
            queue = queue_manager.get_queue()
            for idx, item in enumerate(queue):
                item_status = item.get("status")
                if item_status in (ProcessingStatus.WAITING, ProcessingStatus.PROCESSING):
                    progress = int(item.get("progress", 0) or 0)
                    queue_manager.update_file_status(
                        idx, ProcessingStatus.CANCELLED, progress, "用户取消"
                    )

            self.ui_components["current_file_label"].setText("批量处理已取消")
            self._update_queue_display()
            self._update_statistics()
            self._reset_ui_state()
            self.processing_finished.emit()

            QMessageBox.information(self, "已取消", "批量处理已取消")
        else:
            self.ui_components["current_file_label"].setText("批量处理已完成")
            self._reset_ui_state()
            self.processing_finished.emit()

            # 显示完成统计
            stats = self.file_manager.get_queue_statistics()
            QMessageBox.information(
                self,
                "处理完成",
                f"批量处理完成！\n总计: {stats['total']}\n成功: {stats['completed']}\n失败: {stats['failed']}",
            )

        self._stop_requested = False

    def _on_status_message(self, message: str):
        """状态消息更新"""
        self.ui_components["status_label"].setText(message)


# 示例用法
if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = BatchProcessingWidget()
    widget.show()

    sys.exit(app.exec())
