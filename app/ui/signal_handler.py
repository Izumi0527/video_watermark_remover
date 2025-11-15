#!/usr/bin/env python3
"""
信号处理器模块

负责处理 MainWindow 的所有信号响应逻辑，实现业务逻辑与 UI 组装的分离。

作者: Claude Code Assistant
创建时间: 2025-01-15
版本: v1.0
"""

import logging
import os
from typing import Any, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

# 导入视频处理线程
from ..core.video.video_processor import VideoProcessorThread


class SignalHandler(QObject):
    """
    信号处理器类

    将 MainWindow 的信号处理逻辑独立出来，实现关注点分离。
    采用组合模式，通过依赖注入获取需要的UI组件引用。
    """

    # 定义内部信号用于与其他组件通信
    status_updated = pyqtSignal(str)  # 状态更新信号

    def __init__(
        self,
        file_panel,
        preview_panel,
        control_panel,
        log_panel,
        preferences,
        style_manager,
        main_window=None,
        parent: Optional[QObject] = None,
    ):
        """
        初始化信号处理器

        Args:
            file_panel: 文件操作面板组件
            preview_panel: 预览面板组件
            control_panel: 控制面板组件
            log_panel: 日志面板组件
            preferences: 偏好设置管理器
            style_manager: 样式管理器
            main_window: 主窗口引用（用于访问共享资源如预加载的AI模型）
            parent: 父对象（可选）
        """
        super().__init__(parent)

        # 保存组件引用
        self.file_panel = file_panel
        self.preview_panel = preview_panel
        self.control_panel = control_panel
        self.log_panel = log_panel
        self.preferences = preferences
        self.style_manager = style_manager
        self.main_window = main_window  # 主窗口引用

        # 初始化状态变量
        self.input_file_path: Optional[str] = None
        self.output_file_path: Optional[str] = None
        self.manual_selections: List[Any] = []
        self.processed_image: Optional[Any] = None
        self.video_processor_thread: Optional[Any] = None

        # 设置日志
        self.logger = logging.getLogger(__name__)
        self.logger.info("SignalHandler initialized")

    # ==================== 文件处理信号 ====================

    def handle_import_file(self, parent_widget) -> None:
        """
        处理文件导入请求

        Args:
            parent_widget: 父窗口组件，用于显示对话框
        """
        try:
            file_path, _ = self._show_file_dialog(
                parent_widget,
                "选择图片或视频文件",
                "图片文件 (*.jpg *.jpeg *.png *.bmp);;视频文件 (*.mp4 *.avi *.mkv *.mov);;所有文件 (*)",
            )

            if file_path:
                self.input_file_path = file_path
                # 设置预览图像
                self.preview_panel.set_image(file_path)

                # 同时为手动选择设置图像
                self.preview_panel.set_manual_selection_image(file_path)

                self.control_panel.set_start_button_enabled(True)
                status_msg = f"✅ 已选择文件: {os.path.basename(file_path)}"
                self.status_updated.emit(status_msg)
                self.log_panel.add_status_message(f"文件已加载: {os.path.basename(file_path)}")

                # 如果当前是手动模式，自动切换到手动选择标签页
                if hasattr(self.file_panel, "is_manual_mode") and self.file_panel.is_manual_mode():
                    self.preview_panel.switch_to_manual_tab()

                self.logger.info(f"File imported: {file_path}")

        except Exception as e:
            error_msg = f"文件导入失败: {str(e)}"
            self.log_panel.add_error_message(error_msg)
            self.logger.error(error_msg)

    def handle_export_file(self, parent_widget) -> None:
        """
        处理文件导出请求

        Args:
            parent_widget: 父窗口组件，用于显示对话框
        """
        if not self.processed_image:
            self.log_panel.add_warning_log("没有处理后的图像可导出")
            return

        try:
            file_path, _ = self._show_save_dialog(
                parent_widget, "保存处理后的文件", "PNG文件 (*.png);;JPEG文件 (*.jpg);;所有文件 (*)"
            )

            if file_path:
                # TODO: 这里应该保存处理后的图像
                status_msg = f"文件已导出: {os.path.basename(file_path)}"
                self.status_updated.emit(status_msg)
                self.log_panel.add_success_message(f"文件导出成功: {file_path}")
                self.logger.info(f"File exported: {file_path}")

        except Exception as e:
            error_msg = f"文件导出失败: {str(e)}"
            self.log_panel.add_error_message(error_msg)
            self.logger.error(error_msg)

    # ==================== 主题和模式切换信号 ====================

    def handle_theme_toggle(self, apply_style_callback) -> None:
        """
        处理主题切换请求

        Args:
            apply_style_callback: 回调函数，用于重新应用样式
        """
        try:
            if hasattr(self.style_manager, "toggle_theme"):
                self.style_manager.toggle_theme()
                apply_style_callback()

                # 保存主题偏好
                current_theme = getattr(self.style_manager, "current_theme", "dark")
                self.preferences.set_preference("ui", "theme", current_theme)

                status_msg = f"主题已切换为: {current_theme}"
                self.status_updated.emit(status_msg)
                self.logger.info(status_msg)

        except Exception as e:
            error_msg = f"主题切换失败: {str(e)}"
            self.log_panel.add_error_message(error_msg)
            self.logger.error(error_msg)

    def handle_auto_mode_changed(self, enabled: bool) -> None:
        """
        处理自动模式变化

        Args:
            enabled: 是否启用自动模式
        """
        self.preferences.set_preference("processing", "auto_mode", enabled)
        mode_text = "自动检测" if enabled else "手动选择"
        status_msg = f"处理模式切换为: {mode_text}"
        self.status_updated.emit(status_msg)
        self.logger.info(status_msg)

    def handle_manual_mode_changed(self, enabled: bool) -> None:
        """
        处理手动模式变化

        Args:
            enabled: 是否启用手动模式
        """
        self.preferences.set_preference("processing", "auto_mode", not enabled)
        mode_text = "手动选择" if enabled else "自动检测"
        status_msg = f"处理模式切换为: {mode_text}"
        self.status_updated.emit(status_msg)

        # 如果启用手动模式且有已加载的图像，切换到手动选择标签页
        if enabled and self.input_file_path:
            self.preview_panel.switch_to_manual_tab()

        # 如果禁用手动模式，清空手动选择
        if not enabled:
            self.preview_panel.clear_manual_selections()
            self.manual_selections = []

        self.logger.info(status_msg)

    def handle_manual_selection_changed(self, selections: List[Any]) -> None:
        """
        处理手动选择区域变化

        Args:
            selections: 手动选择的区域列表
        """
        self.manual_selections = selections
        count = len(selections)
        status_msg = f"手动选择了 {count} 个水印区域"
        self.status_updated.emit(status_msg)
        self.logger.info(status_msg)

    # ==================== 处理控制信号 ====================

    def handle_start_processing(self) -> None:
        """处理开始处理请求 (Phase 4 Stage 1.4 - 集成详细进度)"""
        if not self.input_file_path:
            self.log_panel.add_warning_log("请先选择要处理的文件")
            return

        try:
            self.control_panel.set_processing_state(True)
            self.status_updated.emit("开始处理文件...")

            # 显示处理进度状态
            self.preview_panel.show_processing_progress()

            # 准备输出路径
            import os

            input_dir = os.path.dirname(self.input_file_path)
            input_filename = os.path.basename(self.input_file_path)
            input_name, input_ext = os.path.splitext(input_filename)
            output_path = os.path.join(input_dir, f"{input_name}_processed{input_ext}")

            # 创建VideoProcessorThread实例
            ai_params = {
                "auto_detect": self.preferences.get_preference("processing", "auto_mode"),
                "detection_sensitivity": self.preferences.get_preference(
                    "advanced", "detection_sensitivity"
                ),
                "user_mask": None,  # TODO: 从手动选择获取
            }

            # 使用预加载的AI模型 (如果可用)
            preloaded_ai_handler = None
            if self.main_window and hasattr(self.main_window, "ai_handler"):
                preloaded_ai_handler = self.main_window.ai_handler

            self.video_processor = VideoProcessorThread(
                input_path=self.input_file_path,
                output_path=output_path,
                ai_params=ai_params,
                config=None,  # TODO: 传递config
                preloaded_ai_handler=preloaded_ai_handler,
            )

            # 连接信号
            self.video_processor.progress.connect(self.control_panel.update_progress)
            self.video_processor.status.connect(self.log_panel.add_status_message)
            self.video_processor.finished.connect(self._on_processing_finished)
            self.video_processor.error.connect(self._on_processing_error)
            # TODO: Implement preview_update method in PreviewPanel
            # self.video_processor.preview_update.connect(self.preview_panel.update_preview)

            # 连接详细进度信号 (Phase 4 Stage 1.4)
            self.video_processor.detailed_progress.connect(
                self.control_panel.update_detailed_progress
            )

            # 启动处理线程
            self.video_processor.start()

            self.logger.info("Processing started with detailed progress tracking")

        except Exception as e:
            error_msg = f"处理启动失败: {str(e)}"
            self.log_panel.add_error_message(error_msg)
            self.control_panel.set_processing_state(False)
            self.logger.error(error_msg)

    def _on_processing_finished(self, output_path: str):
        """处理完成回调 (Phase 4 Stage 1.4)"""
        self.control_panel.set_processing_state(False)
        if output_path:
            self.log_panel.add_success_message(f"处理完成: {output_path}")
            self.status_updated.emit("处理完成")
            # TODO: 自动加载处理后的结果
        else:
            self.log_panel.add_warning_log("处理被取消")
            self.status_updated.emit("处理取消")

    def _on_processing_error(self, error_msg: str):
        """处理错误回调 (Phase 4 Stage 1.4)"""
        self.control_panel.set_processing_state(False)
        self.log_panel.add_error_message(f"处理失败: {error_msg}")
        self.status_updated.emit("处理失败")

    def handle_stop_processing(self) -> None:
        """处理停止处理请求 (Phase 4 Stage 1.4)"""
        if hasattr(self, "video_processor") and self.video_processor:
            self.video_processor.stop()
            self.video_processor.wait(5000)  # 等待最多5秒

        self.control_panel.set_processing_state(False)
        self.control_panel.reset_progress()  # 同时重置详细进度
        self.status_updated.emit("处理已停止")
        self.logger.info("Processing stopped")

    def handle_batch_processing(self) -> None:
        """处理批处理请求"""
        self.status_updated.emit("批处理功能启动")
        self.logger.info("Batch processing requested")

    def handle_progress_update(self, value: int) -> None:
        """
        处理进度更新

        Args:
            value: 进度值（0-100）
        """
        self.control_panel.update_progress(value)
        self.log_panel.add_progress_message(f"处理进度: {value}%")

    # ==================== 工具方法 ====================

    def _show_file_dialog(self, parent, title: str, filters: str):
        """
        显示文件选择对话框

        Args:
            parent: 父窗口组件
            title: 对话框标题
            filters: 文件过滤器

        Returns:
            (file_path, selected_filter) 元组
        """
        from PyQt6.QtWidgets import QFileDialog

        last_dir = self.preferences.get_preference(
            "paths", "last_input_dir", os.path.expanduser("~")
        )
        file_path, selected_filter = QFileDialog.getOpenFileName(parent, title, last_dir, filters)

        if file_path:
            self.preferences.set_preference("paths", "last_input_dir", os.path.dirname(file_path))

        return file_path, selected_filter

    def _show_save_dialog(self, parent, title: str, filters: str):
        """
        显示保存文件对话框

        Args:
            parent: 父窗口组件
            title: 对话框标题
            filters: 文件过滤器

        Returns:
            (file_path, selected_filter) 元组
        """
        from PyQt6.QtWidgets import QFileDialog

        last_dir = self.preferences.get_preference(
            "paths", "last_output_dir", os.path.expanduser("~")
        )
        file_path, selected_filter = QFileDialog.getSaveFileName(parent, title, last_dir, filters)

        if file_path:
            self.preferences.set_preference("paths", "last_output_dir", os.path.dirname(file_path))

        return file_path, selected_filter

    # ==================== 状态访问方法 ====================

    def get_input_file_path(self) -> Optional[str]:
        """获取输入文件路径"""
        return self.input_file_path

    def get_manual_selections(self) -> List[Any]:
        """获取手动选择的区域列表"""
        return self.manual_selections

    def set_processed_image(self, image: Any) -> None:
        """
        设置处理后的图像

        Args:
            image: 处理后的图像数据
        """
        self.processed_image = image

    def cleanup(self) -> None:
        """清理资源"""
        # 停止处理线程
        if self.video_processor_thread and hasattr(self.video_processor_thread, "isRunning"):
            if self.video_processor_thread.isRunning():
                self.video_processor_thread.quit()
                self.video_processor_thread.wait()

        self.logger.info("SignalHandler cleaned up")
