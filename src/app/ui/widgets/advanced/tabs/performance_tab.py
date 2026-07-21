#!/usr/bin/env python3
"""
性能参数Tab页面
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .....config.advanced_params import PROCESSING_MODE_UI_OPTIONS, processing_mode_to_label


class PerformanceParametersTab:
    """性能参数Tab页面"""

    @staticmethod
    def create_tab(parent_widget):
        """创建性能参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 运行模式组
        thread_group = QGroupBox("运行模式")
        thread_layout = QFormLayout(thread_group)

        parent_widget.processing_mode_combo = QComboBox()
        for mode in PROCESSING_MODE_UI_OPTIONS:
            parent_widget.processing_mode_combo.addItem(processing_mode_to_label(mode), mode)
        parent_widget.configure_panel_combo_box(
            parent_widget.processing_mode_combo,
            minimum_contents_length=14,
            tooltip="不同处理模式会影响吞吐、显存占用与稳定性；资源紧张时建议使用更保守的模式。",
        )
        thread_layout.addRow("处理模式:", parent_widget.processing_mode_combo)
        mode_hint_label = QLabel("说明：模式会影响速度与资源占用。")
        mode_hint_label.setWordWrap(True)
        mode_hint_label.setToolTip("提示：显存紧张或深度学习后端下，程序可能自动收敛为更保守的模式。")
        thread_layout.addRow("", mode_hint_label)

        parent_widget.worker_count_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.worker_count_spin,
            tooltip="控制处理并行度，0 表示自动分配。",
        )
        parent_widget.worker_count_spin.setMinimum(0)
        parent_widget.worker_count_spin.setMaximum(16)
        parent_widget.worker_count_spin.setValue(0)
        parent_widget.worker_count_spin.setSpecialValueText("自动")
        thread_layout.addRow("并行度:", parent_widget.worker_count_spin)

        layout.addWidget(thread_group)

        # GPU 深度学习修复组
        gpu_group = QGroupBox("GPU 深度学习修复")
        gpu_layout = QVBoxLayout(gpu_group)

        parent_widget.enable_gpu_check = QCheckBox("启用深度修复（需 CUDA/权重）")
        parent_widget.enable_gpu_check.setToolTip("启用深度学习修复后端（LaMa）。需要 CUDA 环境与模型权重。")
        gpu_layout.addWidget(parent_widget.enable_gpu_check)

        parent_widget.gpu_memory_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.gpu_memory_spin,
            tooltip="限制深度修复后端可使用的显存预算。",
        )
        parent_widget.gpu_memory_spin.setMinimum(512)
        parent_widget.gpu_memory_spin.setMaximum(16384)
        parent_widget.gpu_memory_spin.setValue(2048)
        parent_widget.gpu_memory_spin.setSuffix(" MB")
        gpu_layout.addWidget(QLabel("GPU内存限制:"))
        gpu_layout.addWidget(parent_widget.gpu_memory_spin)

        layout.addWidget(gpu_group)

        # 缓存设置组
        cache_group = QGroupBox("缓存设置")
        cache_layout = QFormLayout(cache_group)

        parent_widget.cache_size_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.cache_size_spin,
            tooltip="控制缓存上限，过大可能增加内存占用。",
        )
        parent_widget.cache_size_spin.setMinimum(64)
        parent_widget.cache_size_spin.setMaximum(4096)
        parent_widget.cache_size_spin.setValue(512)
        parent_widget.cache_size_spin.setSuffix(" MB")
        cache_layout.addRow("缓存大小:", parent_widget.cache_size_spin)

        parent_widget.enable_cache_check = QCheckBox("启用结果缓存")
        parent_widget.enable_cache_check.setChecked(True)
        cache_layout.addRow("", parent_widget.enable_cache_check)

        layout.addWidget(cache_group)

        # 批处理策略组
        batch_group = QGroupBox("批处理策略")
        batch_layout = QFormLayout(batch_group)

        parent_widget.batch_max_concurrent_files_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.batch_max_concurrent_files_spin,
            tooltip="限制批处理同时运行的文件数量。",
        )
        parent_widget.batch_max_concurrent_files_spin.setMinimum(1)
        parent_widget.batch_max_concurrent_files_spin.setMaximum(16)
        parent_widget.batch_max_concurrent_files_spin.setValue(1)
        batch_layout.addRow("并发文件数:", parent_widget.batch_max_concurrent_files_spin)

        parent_widget.batch_auto_retry_failed_check = QCheckBox("失败后自动重试")
        parent_widget.batch_auto_retry_failed_check.setChecked(True)
        batch_layout.addRow("", parent_widget.batch_auto_retry_failed_check)

        parent_widget.batch_max_retry_count_spin = QSpinBox()
        parent_widget.configure_panel_spin_box(
            parent_widget.batch_max_retry_count_spin,
            tooltip="失败任务的最大自动重试次数。",
        )
        parent_widget.batch_max_retry_count_spin.setMinimum(0)
        parent_widget.batch_max_retry_count_spin.setMaximum(10)
        parent_widget.batch_max_retry_count_spin.setValue(3)
        batch_layout.addRow("最大重试次数:", parent_widget.batch_max_retry_count_spin)

        layout.addWidget(batch_group)
        layout.addStretch()

        return tab
