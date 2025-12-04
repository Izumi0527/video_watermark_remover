#!/usr/bin/env python3
"""
批量处理UI组件模块

提供批量处理组件的UI创建和样式功能：
1. 控制按钮区域创建
2. 进度显示区域创建
3. 文件队列列表创建
4. 按钮样式和布局管理

"""

from typing import Dict, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class BatchUIComponents:
    """批量处理UI组件创建器"""

    @staticmethod
    def create_title_label() -> QLabel:
        """
        创建标题标签

        Returns:
            配置好的标题标签
        """
        title_label = QLabel("批量处理队列")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        return title_label

    @staticmethod
    def create_control_buttons() -> Tuple[QHBoxLayout, Dict[str, QPushButton]]:
        """
        创建控制按钮区域

        Returns:
            (布局, 按钮字典)
        """
        control_layout = QHBoxLayout()
        buttons = {}

        # 添加文件按钮
        add_files_btn = QPushButton("添加文件")
        buttons["add_files"] = add_files_btn
        control_layout.addWidget(add_files_btn)

        # 清空队列按钮
        clear_queue_btn = QPushButton("清空队列")
        buttons["clear_queue"] = clear_queue_btn
        control_layout.addWidget(clear_queue_btn)

        # 开始处理按钮（使用全局样式）
        start_batch_btn = QPushButton("开始批量处理")
        start_batch_btn.setObjectName("btn_success")
        buttons["start_batch"] = start_batch_btn
        control_layout.addWidget(start_batch_btn)

        # 停止处理按钮
        stop_batch_btn = QPushButton("停止处理")
        stop_batch_btn.setObjectName("btn_danger")
        stop_batch_btn.setEnabled(False)
        buttons["stop_batch"] = stop_batch_btn
        control_layout.addWidget(stop_batch_btn)

        control_layout.addStretch()
        return control_layout, buttons

    @staticmethod
    def create_file_queue_group() -> Tuple[QGroupBox, QListWidget, QLabel]:
        """
        创建文件队列组

        Returns:
            (分组框, 文件列表, 信息标签)
        """
        queue_group = QGroupBox("文件队列")
        queue_layout = QVBoxLayout(queue_group)

        file_list = QListWidget()
        file_list.setMinimumHeight(200)
        queue_layout.addWidget(file_list)

        queue_info_label = QLabel("队列为空")
        queue_info_label.setObjectName("queue_info_label")
        queue_layout.addWidget(queue_info_label)

        return queue_group, file_list, queue_info_label

    @staticmethod
    def create_progress_group() -> Tuple[QGroupBox, Dict[str, QWidget]]:
        """
        创建进度显示组 (Phase 4 Stage 1.4 - 增强版)

        Returns:
            (分组框, 进度组件字典)
        """
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_group)
        progress_components: Dict[str, QWidget] = {}

        # 统计信息区域 (Phase 4 Stage 1.4)
        stats_layout = QHBoxLayout()

        # 总文件数
        total_label = QLabel("总计: 0")
        total_label.setObjectName("batch_stat_total")
        progress_components["total_label"] = total_label
        stats_layout.addWidget(total_label)

        # 成功数
        success_label = QLabel("✅ 成功: 0")
        success_label.setObjectName("batch_stat_success")
        progress_components["success_label"] = success_label
        stats_layout.addWidget(success_label)

        # 失败数
        failed_label = QLabel("❌ 失败: 0")
        failed_label.setObjectName("batch_stat_failed")
        progress_components["failed_label"] = failed_label
        stats_layout.addWidget(failed_label)

        # 等待数
        waiting_label = QLabel("⏳ 等待: 0")
        waiting_label.setObjectName("batch_stat_waiting")
        progress_components["waiting_label"] = waiting_label
        stats_layout.addWidget(waiting_label)

        # 并发处理数 (Phase 4 Stage 1.4)
        concurrent_label = QLabel("🔄 处理中: 0")
        concurrent_label.setObjectName("batch_stat_concurrent")
        progress_components["concurrent_label"] = concurrent_label
        stats_layout.addWidget(concurrent_label)

        stats_layout.addStretch()
        progress_layout.addLayout(stats_layout)

        # 当前文件信息
        current_file_label = QLabel("等待开始处理...")
        current_file_label.setObjectName("current_file_label")
        progress_components["current_file_label"] = current_file_label
        progress_layout.addWidget(current_file_label)

        # 当前文件进度条
        current_progress_bar = QProgressBar()
        current_progress_bar.setObjectName("current_progress_bar")
        current_progress_bar.setRange(0, 100)
        current_progress_bar.setValue(0)
        progress_components["current_progress_bar"] = current_progress_bar
        progress_layout.addWidget(current_progress_bar)

        # 总体进度条
        overall_layout = QHBoxLayout()
        overall_layout.addWidget(QLabel("总体进度:"))
        overall_progress_bar = QProgressBar()
        overall_progress_bar.setObjectName("overall_progress_bar")
        overall_progress_bar.setRange(0, 100)
        overall_progress_bar.setValue(0)
        progress_components["overall_progress_bar"] = overall_progress_bar
        overall_layout.addWidget(overall_progress_bar)
        progress_layout.addLayout(overall_layout)

        # 状态标签
        status_label = QLabel("准备就绪")
        status_label.setObjectName("batch_status_label")
        progress_components["status_label"] = status_label
        progress_layout.addWidget(status_label)

        return progress_group, progress_components

    @staticmethod
    def create_main_layout() -> Tuple[QVBoxLayout, QSplitter]:
        """
        创建主布局

        Returns:
            (主布局, 分割器)
        """
        layout = QVBoxLayout()
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Vertical)

        return layout, splitter
