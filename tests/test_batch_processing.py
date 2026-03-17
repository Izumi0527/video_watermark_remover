#!/usr/bin/env python3
# -*- coding: utf-8 BOM-*-
"""
批量处理功能测试脚本

测试批量处理组件的基本功能
"""

import os
import sys

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.config_manager import ConfigManager
from app.ui.widgets.batch.batch_processing_widget import BatchProcessingWidget


class BatchProcessingTestWindow(QMainWindow):
    """批量处理测试窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量处理功能测试")
        self.setGeometry(100, 100, 1000, 700)

        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 创建批量处理组件
        self.batch_widget = BatchProcessingWidget()

        # 加载配置
        config = ConfigManager.load_config()
        self.batch_widget.set_config(config)

        # 设置测试AI参数
        test_ai_params = {"auto_detect": True, "detection_sensitivity": 0.5, "user_mask": None}
        self.batch_widget.set_ai_params(test_ai_params)

        # 连接信号用于测试
        self.batch_widget.processing_started.connect(self._on_processing_started)
        self.batch_widget.processing_finished.connect(self._on_processing_finished)

        layout.addWidget(self.batch_widget)

        print("批量处理测试窗口初始化完成")
        print("请使用界面添加文件并测试批量处理功能")

    def _on_processing_started(self):
        """处理开始回调"""
        print("[OK] 测试信号: 批量处理已开始")

    def _on_processing_finished(self):
        """处理完成回调"""
        print("[OK] 测试信号: 批量处理已完成")


def main():
    """主函数"""
    print("启动批量处理功能测试...")

    app = QApplication(sys.argv)

    # 创建测试窗口
    test_window = BatchProcessingTestWindow()
    test_window.show()

    print("📋 测试窗口已显示，您可以:")
    print("  1. 点击'添加文件'按钮选择要处理的图片/视频")
    print("  2. 查看文件队列显示")
    print("  3. 点击'开始批量处理'测试处理流程")
    print("  4. 观察进度显示和状态更新")

    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
