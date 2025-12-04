#!/usr/bin/env python3
"""
输出参数Tab页面
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class OutputParametersTab:
    """输出参数Tab页面"""

    @staticmethod
    def create_tab(parent_widget):
        """创建输出参数标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 输出格式组
        format_group = QGroupBox("输出格式")
        format_layout = QFormLayout(format_group)

        parent_widget.output_format_combo = QComboBox()
        parent_widget.output_format_combo.addItems(["保持原格式", "JPG", "PNG", "BMP", "TIFF"])
        format_layout.addRow("输出格式:", parent_widget.output_format_combo)

        layout.addWidget(format_group)

        # 压缩设置组
        compression_group = QGroupBox("压缩设置")
        compression_layout = QFormLayout(compression_group)

        parent_widget.compression_slider = QSlider(Qt.Orientation.Horizontal)
        parent_widget.compression_slider.setMinimum(1)
        parent_widget.compression_slider.setMaximum(100)
        parent_widget.compression_slider.setValue(85)
        parent_widget.compression_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        parent_widget.compression_slider.setTickInterval(10)

        parent_widget.compression_label = QLabel("85%")
        compression_layout.addRow("压缩质量:", parent_widget.compression_slider)
        compression_layout.addRow("当前质量:", parent_widget.compression_label)

        layout.addWidget(compression_group)

        # 文件名设置组
        filename_group = QGroupBox("文件名设置")
        filename_layout = QVBoxLayout(filename_group)

        parent_widget.add_suffix_check = QCheckBox("添加处理后缀")
        parent_widget.add_suffix_check.setChecked(True)
        filename_layout.addWidget(parent_widget.add_suffix_check)

        parent_widget.add_timestamp_check = QCheckBox("添加时间戳")
        filename_layout.addWidget(parent_widget.add_timestamp_check)

        layout.addWidget(filename_group)
        layout.addStretch()

        return tab
