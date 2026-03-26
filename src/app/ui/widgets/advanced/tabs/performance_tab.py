#!/usr/bin/env python3
"""
性能参数Tab页面
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PerformanceParametersTab:
    """性能参数Tab页面"""

    @staticmethod
    def create_tab(parent_widget):
        """创建性能参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 线程设置组
        thread_group = QGroupBox("线程设置")
        thread_layout = QFormLayout(thread_group)

        parent_widget.thread_count_spin = QSpinBox()
        parent_widget.thread_count_spin.setMinimum(1)
        parent_widget.thread_count_spin.setMaximum(16)
        parent_widget.thread_count_spin.setValue(4)
        parent_widget.thread_count_spin.setSpecialValueText("自动")
        thread_layout.addRow("处理线程数:", parent_widget.thread_count_spin)

        layout.addWidget(thread_group)

        # GPU 深度学习修复组
        gpu_group = QGroupBox("GPU 深度学习修复")
        gpu_layout = QVBoxLayout(gpu_group)

        parent_widget.enable_gpu_check = QCheckBox("启用深度学习修复后端（LaMa / 兼容 U-Net，需要 CUDA 与权重）")
        gpu_layout.addWidget(parent_widget.enable_gpu_check)

        parent_widget.gpu_memory_spin = QSpinBox()
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
        parent_widget.cache_size_spin.setMinimum(64)
        parent_widget.cache_size_spin.setMaximum(4096)
        parent_widget.cache_size_spin.setValue(512)
        parent_widget.cache_size_spin.setSuffix(" MB")
        cache_layout.addRow("缓存大小:", parent_widget.cache_size_spin)

        parent_widget.enable_cache_check = QCheckBox("启用结果缓存")
        parent_widget.enable_cache_check.setChecked(True)
        cache_layout.addRow("", parent_widget.enable_cache_check)

        layout.addWidget(cache_group)
        layout.addStretch()

        return tab
