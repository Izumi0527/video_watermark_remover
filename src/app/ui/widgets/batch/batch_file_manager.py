#!/usr/bin/env python3
"""
批量处理文件管理模块

提供批量处理的文件操作和队列管理功能：
1. 文件添加和验证
2. 队列显示更新
3. 文件状态管理
4. 队列清理操作

"""

import os
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox, QWidget

from ...utils import MEDIA_IMPORT_FILTER
from .batch_processor_thread import FileQueueManager, ProcessingStatus


class BatchFileManager:
    """批量处理文件管理器"""

    def __init__(self, parent_widget: QWidget):
        """
        初始化文件管理器

        Args:
            parent_widget: 父组件，用于显示对话框
        """
        self.parent = parent_widget
        self.queue_manager = FileQueueManager()

    def show_add_files_dialog(self) -> List[str]:
        """
        显示添加文件对话框

        Returns:
            选中的文件路径列表
        """
        file_dialog = QFileDialog(self.parent)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(MEDIA_IMPORT_FILTER)

        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files = list(file_dialog.selectedFiles())
            return selected_files
        return []

    def add_file_to_queue(self, input_path: str) -> bool:
        """
        将文件添加到队列

        Args:
            input_path: 输入文件路径

        Returns:
            是否添加成功
        """
        if not os.path.exists(input_path):
            QMessageBox.warning(self.parent, "警告", f"文件不存在: {input_path}")
            return False

        # 生成输出路径
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_processed{ext}"

        # 检查是否已经存在
        queue = self.queue_manager.get_queue()
        for item in queue:
            if item["input_path"] == input_path:
                QMessageBox.information(
                    self.parent, "提示", f"文件已在队列中: {os.path.basename(input_path)}"
                )
                return False

        # 添加到队列
        self.queue_manager.add_file(input_path, output_path)
        return True

    def add_files_batch(self, file_paths: List[str]) -> int:
        """
        批量添加文件

        Args:
            file_paths: 文件路径列表

        Returns:
            成功添加的文件数量
        """
        added_count = 0
        for file_path in file_paths:
            if self.add_file_to_queue(file_path):
                added_count += 1
        return added_count

    def update_queue_display(self, file_list: QListWidget, queue_info_label: QLabel) -> None:
        """
        更新队列显示

        Args:
            file_list: 文件列表组件
            queue_info_label: 队列信息标签
        """
        file_list.clear()
        queue = self.queue_manager.get_queue()

        if not queue:
            queue_info_label.setText("队列为空")
            return

        for index, file_info in enumerate(queue):
            input_path = file_info["input_path"]
            status = file_info["status"]
            progress = file_info.get("progress", 0)

            # 创建列表项
            filename = os.path.basename(input_path)
            status_text = self._get_status_text(status)

            if status == ProcessingStatus.PROCESSING:
                item_text = f"[{progress}%] {filename} - {status_text}"
            else:
                item_text = f"{filename} - {status_text}"

            list_item = QListWidgetItem(item_text)

            # 设置状态颜色
            if status == ProcessingStatus.COMPLETED:
                list_item.setBackground(Qt.GlobalColor.green)
            elif status == ProcessingStatus.FAILED:
                list_item.setBackground(Qt.GlobalColor.lightGray)
            elif status == ProcessingStatus.PROCESSING:
                list_item.setBackground(Qt.GlobalColor.cyan)

            file_list.addItem(list_item)

        # 更新队列信息
        total = len(queue)
        completed = self.queue_manager.get_completed_count()
        failed = self.queue_manager.get_failed_count()
        pending = self.queue_manager.get_pending_count()

        info_text = f"总计: {total} | 等待: {pending} | 已完成: {completed} | 失败: {failed}"
        queue_info_label.setText(info_text)

    def _get_status_text(self, status: ProcessingStatus) -> str:
        """
        获取状态文本

        Args:
            status: 处理状态

        Returns:
            状态文本
        """
        status_map = {
            ProcessingStatus.WAITING: "等待中",
            ProcessingStatus.PROCESSING: "处理中",
            ProcessingStatus.COMPLETED: "已完成",
            ProcessingStatus.FAILED: "失败",
            ProcessingStatus.CANCELLED: "已取消",
        }
        return status_map.get(status, "未知")

    def clear_queue_with_confirmation(self) -> bool:
        """
        带确认的清空队列操作

        Returns:
            是否执行了清空操作
        """
        if self.queue_manager.get_queue_size() == 0:
            return False

        reply = QMessageBox.question(
            self.parent,
            "确认清空",
            "确定要清空所有队列吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.queue_manager.clear_queue()
            return True
        return False

    def get_queue_manager(self) -> FileQueueManager:
        """
        获取队列管理器

        Returns:
            文件队列管理器实例
        """
        return self.queue_manager

    def reset_all_files_to_waiting(self) -> None:
        """重置所有文件状态为等待"""
        for index in range(self.queue_manager.get_queue_size()):
            self.queue_manager.update_file_status(index, ProcessingStatus.WAITING)

    def get_queue_statistics(self) -> dict:
        """
        获取队列统计信息

        Returns:
            包含统计信息的字典，键名:
            - total: 总文件数
            - completed: 已完成数
            - failed: 失败数
            - waiting: 等待处理数
            - processing: 正在处理数
        """
        return {
            "total": self.queue_manager.get_queue_size(),
            "completed": self.queue_manager.get_completed_count(),
            "failed": self.queue_manager.get_failed_count(),
            "waiting": self.queue_manager.get_pending_count(),
            "processing": self.queue_manager.get_processing_count(),
        }
