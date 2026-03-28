#!/usr/bin/env python3
"""
信号处理器模块

负责处理 MainWindow 的所有信号响应逻辑，实现业务逻辑与 UI 组装的分离。

"""

import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

# 导入配置
from ..config.advanced_params import AdvancedParamsSnapshot, ResolvedPerformanceConfig
from ..config.styles.colors import DEFAULT_THEME

# 导入视频处理线程
from ..core.video.output_strategy import resolve_output_path
from ..core.video.thread import VideoProcessorThread

# 导入帧提取工具
from ..core.video.workers.frame_reader import extract_video_first_frame
from ..utils import IMAGE_FILE_EXTENSIONS, VIDEO_FILE_EXTENSIONS

# 导入AI参数构建器
from .utils import MEDIA_IMPORT_FILTER, AIParamsBuilder

# 导入批处理组件
from .widgets.batch.batch_processor_thread import (
    BatchProcessorThread,
    FileQueueManager,
    ProcessingStatus,
)


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
        self.video_processor_thread: Optional[VideoProcessorThread] = None

        # 文件队列管理器和批处理线程
        self.file_queue_manager = FileQueueManager()
        self.batch_processor: Optional[BatchProcessorThread] = None
        self.is_batch_mode = False  # 是否为批量处理模式
        self._batch_stop_requested = False  # 批量停止请求标记（用于取消/完成口径分流）
        self._last_batch_ai_params: Optional[dict] = None
        self._last_batch_ai_params_generated_at: Optional[str] = None
        self._last_batch_config: Optional[dict] = None
        self._last_batch_runtime_config: Optional[dict] = None
        self._single_stop_requested = False

        # 设置日志
        self.logger = logging.getLogger(__name__)
        self.logger.info("SignalHandler initialized")

    # ==================== 文件处理信号 ====================

    def handle_import_file(self, parent_widget) -> None:
        """
        处理文件导入请求 - 支持单选和多选

        Args:
            parent_widget: 父窗口组件，用于显示对话框
        """
        try:
            file_paths = self._show_multi_file_dialog(
                parent_widget,
                "选择图片或视频文件",
                MEDIA_IMPORT_FILTER,
            )

            if not file_paths:
                return  # 用户取消

            if len(file_paths) == 1:
                # 单文件模式 - 使用现有逻辑
                self._handle_single_file(file_paths[0])
            else:
                # 多文件模式 - 进入队列模式
                self._handle_multiple_files(file_paths)

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
        if not self.output_file_path or not os.path.exists(self.output_file_path):
            self.log_panel.add_warning_log("没有可导出的处理结果，请先完成处理")
            return

        try:
            source_path = self.output_file_path
            source_suffix = Path(source_path).suffix
            suffix_label = source_suffix.lstrip(".").upper() if source_suffix else "文件"
            filters = (
                f"{suffix_label} 文件 (*{source_suffix});;所有文件 (*)" if source_suffix else "所有文件 (*)"
            )

            file_path, _ = self._show_save_dialog(
                parent_widget,
                "另存为处理后的文件",
                filters,
                default_filename=os.path.basename(source_path),
            )

            if file_path:
                target_path = Path(file_path)
                if source_suffix:
                    # 另存为：保持源文件扩展名，避免误以为做了格式转换
                    if not target_path.suffix:
                        target_path = target_path.with_suffix(source_suffix)
                    elif target_path.suffix.lower() != source_suffix.lower():
                        target_path = target_path.with_suffix(source_suffix)

                if os.path.abspath(str(target_path)) == os.path.abspath(source_path):
                    self.log_panel.add_warning_log("导出路径与处理结果相同，无需另存")
                    return

                shutil.copy2(source_path, str(target_path))
                self.preferences.set_preference("paths", "last_output_dir", str(target_path.parent))

                status_msg = f"文件已导出: {target_path.name}"
                self.status_updated.emit(status_msg)
                self.log_panel.add_success_message(f"文件导出成功: {target_path}")
                self.logger.info(f"File exported: {target_path}")

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
                current_theme = getattr(self.style_manager, "current_theme", DEFAULT_THEME)
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

        if enabled:
            if hasattr(self.preview_panel, "clear_manual_selections"):
                self.preview_panel.clear_manual_selections()
            self.manual_selections = []

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
        if enabled:
            status_msg = "已进入手动模式，请重新框选水印区域"
        else:
            status_msg = "处理模式切换为: 自动检测"
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
        """处理开始处理请求 - 支持单文件和批量模式"""
        if not self.input_file_path:
            self.log_panel.add_warning_log("请先选择要处理的文件")
            return

        if self.video_processor_thread:
            if self.video_processor_thread.isRunning():
                self.log_panel.add_warning_log("当前任务尚未完全结束，请稍候后再开始新任务")
                self.logger.warning(
                    "Start requested while previous processing thread still running"
                )
                return
            self.video_processor_thread = None

        try:
            self.control_panel.set_processing_state(True)
            self.preview_panel.show_processing_progress(
                self._build_processing_progress_message(self.input_file_path)
            )
            self.output_file_path = None
            self.file_panel.set_export_enabled(False)

            # 判断是否为批量模式
            if self.is_batch_mode:
                self._start_batch_processing()
                return

            # 单文件模式 - 保持原有逻辑
            self.status_updated.emit(
                self._build_start_processing_status_message(self.input_file_path)
            )

            # 获取高级参数
            advanced_params = {}
            if hasattr(self.control_panel, "get_advanced_parameters"):
                advanced_params = self.control_panel.get_advanced_parameters()
                self.logger.debug(f"[参数获取] 成功获取 {len(advanced_params)} 个高级参数")
            else:
                self.logger.warning("[参数获取] ControlPanel不支持高级参数，使用默认值")

            # 使用AI参数构建器构建完整参数
            params_builder = AIParamsBuilder()
            ai_params = params_builder.build_from_ui(
                preferences=self.preferences,
                advanced_params=advanced_params,
                manual_selections=self.manual_selections,
                input_file_path=self.input_file_path,
                is_batch=False,
            )
            runtime_performance = self._resolve_runtime_performance_config(
                params_builder=params_builder,
                advanced_params=advanced_params,
                input_file_path=self.input_file_path,
                is_batch=False,
                ai_params=ai_params,
            ).to_manifest_dict()
            output_path = resolve_output_path(self.input_file_path, ai_params)

            # 使用预加载的AI模型 (如果可用)
            preloaded_ai_handler = None
            if self.main_window and hasattr(self.main_window, "ai_handler"):
                preloaded_ai_handler = self.main_window.ai_handler

            self.video_processor_thread = VideoProcessorThread(
                input_path=self.input_file_path,
                output_path=output_path,
                ai_params=ai_params,
                config=self.main_window.config if self.main_window else None,
                preloaded_ai_handler=preloaded_ai_handler,
                enable_multiprocess=bool(ai_params.get("enable_multiprocess", False)),
                num_processes=ai_params.get("num_processes"),
                use_pipeline=bool(ai_params.get("use_pipeline", False)),
                runtime_performance=runtime_performance,
            )
            self._single_stop_requested = False

            # 连接信号
            worker_thread = self.video_processor_thread
            worker_thread.progress.connect(self.control_panel.update_progress)
            worker_thread.status.connect(self.log_panel.add_status_message)
            worker_thread.finished.connect(
                lambda output_path, thread=worker_thread: self._on_processing_finished_with_thread(
                    output_path, thread
                )
            )
            worker_thread.error.connect(
                lambda error_msg, thread=worker_thread: self._on_processing_error_with_thread(
                    error_msg, thread
                )
            )
            worker_thread.preview_update.connect(
                self.preview_panel.update_processing_preview_from_bgr
            )

            # 连接详细进度信号 (Phase 4 Stage 1.4)
            worker_thread.detailed_progress.connect(self.control_panel.update_detailed_progress)

            # 启动处理线程
            worker_thread.start()

            self.logger.info("Processing started with detailed progress tracking")

        except Exception as e:
            error_msg = f"处理启动失败: {str(e)}"
            self.log_panel.add_error_message(error_msg)
            self.control_panel.set_processing_state(False)
            self.control_panel.reset_progress()
            self.logger.error(error_msg)

    def _on_processing_finished(self, output_path: str):
        """处理完成回调 (Phase 4 Stage 1.4)"""
        # 兼容旧连接方式：默认允许收尾
        return self._on_processing_finished_with_thread(output_path, None)

    def _on_processing_finished_with_thread(
        self,
        output_path: str,
        source_thread: Optional[VideoProcessorThread],
    ) -> None:
        """处理完成回调（带线程实例防抖，避免旧线程回调污染新状态）"""
        if source_thread is not None and self.video_processor_thread is not source_thread:
            self.logger.debug("忽略过期处理线程的完成回调")
            return

        self.control_panel.set_processing_state(False)
        self.control_panel.reset_progress()
        self._release_video_processor_thread_if_stopped(source_thread)
        self._single_stop_requested = False
        if output_path:
            self.log_panel.add_success_message(f"处理完成: {output_path}")
            self.status_updated.emit("处理完成")

            # 保存输出路径
            self.output_file_path = output_path

            # 启用导出按钮
            self.file_panel.set_export_enabled(True)

            # 加载处理后的结果到PreviewPanel
            self._load_processed_result(output_path)
        else:
            self.log_panel.add_warning_log("处理被取消")
            self.status_updated.emit("处理取消")
            self.output_file_path = None
            self.file_panel.set_export_enabled(False)

    def _on_processing_error(self, error_msg: str):
        """处理错误回调 (Phase 4 Stage 1.4)"""
        return self._on_processing_error_with_thread(error_msg, None)

    def _on_processing_error_with_thread(
        self,
        error_msg: str,
        source_thread: Optional[VideoProcessorThread],
    ) -> None:
        """处理错误回调（带线程实例防抖，避免旧线程回调污染新状态）"""
        if source_thread is not None and self.video_processor_thread is not source_thread:
            self.logger.debug("忽略过期处理线程的错误回调")
            return

        self.control_panel.set_processing_state(False)
        self.control_panel.reset_progress()
        self.log_panel.add_error_message(f"处理失败: {error_msg}")
        self.status_updated.emit("处理失败")
        self.output_file_path = None
        self.file_panel.set_export_enabled(False)
        self._release_video_processor_thread_if_stopped(source_thread)
        self._single_stop_requested = False

    def _release_video_processor_thread_if_stopped(
        self,
        source_thread: Optional[VideoProcessorThread],
    ) -> None:
        """仅在线程真正停止后释放引用，避免清理阶段跨线程对象销毁。"""
        thread = source_thread or self.video_processor_thread
        if thread is None:
            return
        if thread.isRunning():
            self.logger.debug("处理线程仍在运行，延迟释放线程引用")
            return
        if self.video_processor_thread is thread:
            self.video_processor_thread = None

    def handle_stop_processing(self) -> None:
        """处理停止处理请求 (Phase 4 Stage 1.4)"""
        stopped_msg = "处理已停止"

        # 批量模式：不在 UI 线程阻塞等待（避免卡顿）；由 batch_completed 负责最终收尾
        if self.batch_processor and self.batch_processor.isRunning():
            self._batch_stop_requested = True
            self.batch_processor.stop()
            stopped_msg = "批量停止请求已发送"

        thread = self.video_processor_thread
        if thread:
            thread.stop()
            if thread.isRunning():
                # 不在 UI 线程同步 wait，避免阻塞与生命周期竞态
                self._single_stop_requested = True
                stopped_msg = "停止请求已发送，等待线程安全退出"
                self.logger.info("停止请求已发送：处理线程正在退出")
            else:
                self.video_processor_thread = None
                self._single_stop_requested = False
                self.control_panel.set_processing_state(False)
                self.control_panel.reset_progress()  # 同时重置详细进度
        else:
            self.control_panel.set_processing_state(False)
            self.control_panel.reset_progress()  # 同时重置详细进度

        if not (thread and thread.isRunning()):
            self.control_panel.set_processing_state(False)

        self.status_updated.emit(stopped_msg)
        self.output_file_path = None
        self.file_panel.set_export_enabled(False)
        self.logger.info("Processing stopped")

    def handle_progress_update(self, value: int) -> None:
        """
        处理进度更新

        Args:
            value: 进度值（0-100）
        """
        self.control_panel.update_progress(value)
        self.log_panel.add_progress_message(f"处理进度: {value}%")

    def _get_media_type_label(self, file_path_or_name: str) -> str:
        """根据文件扩展名返回媒体类型文案。"""
        file_ext = os.path.splitext(str(file_path_or_name or ""))[1].lower()
        if file_ext in IMAGE_FILE_EXTENSIONS:
            return "图片"
        if file_ext in VIDEO_FILE_EXTENSIONS:
            return "视频"
        return "文件"

    def _build_processing_progress_message(self, file_path_or_name: str) -> str:
        """构建处理中预览文案。"""
        media_type = self._get_media_type_label(file_path_or_name)
        return f"⏳ 正在处理{media_type}，请稍候..."

    def _build_start_processing_status_message(self, file_path_or_name: str) -> str:
        """构建开始处理状态文案。"""
        media_type = self._get_media_type_label(file_path_or_name)
        return f"开始处理{media_type}..."

    def _build_batch_processing_status_message(self, filename: str) -> str:
        """构建批处理当前文件状态文案。"""
        media_type = self._get_media_type_label(filename)
        return f"正在处理{media_type}: {filename}"

    # ==================== 工具方法 ====================

    def _extract_video_first_frame(self, video_path: str):
        """
        提取视频第一帧 (委托给core层实现)

        Args:
            video_path: 视频文件路径

        Returns:
            numpy.ndarray: RGB格式的第一帧图像，如果提取失败则返回None
        """
        return extract_video_first_frame(video_path)

    def _load_processed_result(self, output_path: str):
        """
        加载处理后的结果到PreviewPanel

        Args:
            output_path: 处理后的文件路径
        """
        try:
            from PyQt6.QtGui import QImage, QPixmap

            file_ext = os.path.splitext(output_path)[1].lower()

            if file_ext in IMAGE_FILE_EXTENSIONS:
                # 图片文件：直接加载
                pixmap = QPixmap(output_path)
                if not pixmap.isNull():
                    processing_info = {
                        "detection_method": ("自动检测" if self.file_panel.is_auto_mode() else "手动选择"),
                        "manual_regions_count": (
                            len(self.manual_selections) if self.manual_selections else 0
                        ),
                    }
                    self.preview_panel.set_processed_image(pixmap, processing_info)
                    self.logger.info(f"Loaded processed image: {output_path}")
                else:
                    self.logger.warning(f"Failed to load processed image: {output_path}")

            elif file_ext in VIDEO_FILE_EXTENSIONS:
                # 视频文件：提取第一帧作为预览
                first_frame = self._extract_video_first_frame(output_path)
                if first_frame is not None:
                    # 转换numpy数组为QPixmap
                    import numpy as np

                    # 确保是uint8类型
                    if first_frame.dtype != np.uint8:
                        first_frame = (first_frame * 255).astype(np.uint8)

                    h, w, c = first_frame.shape
                    bytes_per_line = 3 * w
                    q_image = QImage(
                        first_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
                    )
                    pixmap = QPixmap.fromImage(q_image)

                    if not pixmap.isNull():
                        processing_info = {
                            "detection_method": (
                                "自动检测" if self.file_panel.is_auto_mode() else "手动选择"
                            ),
                            "manual_regions_count": (
                                len(self.manual_selections) if self.manual_selections else 0
                            ),
                        }
                        self.preview_panel.set_processed_image(pixmap, processing_info)
                        self.logger.info(f"Loaded processed video preview: {output_path}")
                    else:
                        self.logger.warning(
                            f"Failed to create pixmap from video frame: {output_path}"
                        )
                else:
                    self.logger.warning(
                        f"Failed to extract first frame from processed video: {output_path}"
                    )

            else:
                self.logger.warning(f"Unsupported file format for preview: {file_ext}")

        except Exception as e:
            self.logger.error(f"Error loading processed result: {e}")

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

    def _show_multi_file_dialog(self, parent, title: str, filters: str) -> list[str]:
        """
        显示多选文件对话框

        Args:
            parent: 父窗口组件
            title: 对话框标题
            filters: 文件过滤器

        Returns:
            选中的文件路径列表
        """
        from PyQt6.QtWidgets import QFileDialog

        last_dir = self.preferences.get_preference(
            "paths", "last_input_dir", os.path.expanduser("~")
        )
        file_paths: list[str]
        file_paths, _ = QFileDialog.getOpenFileNames(parent, title, last_dir, filters)

        if file_paths:
            self.preferences.set_preference(
                "paths", "last_input_dir", os.path.dirname(file_paths[0])
            )

        return file_paths

    def _handle_single_file(self, file_path: str):
        """
        处理单个文件 - 保持原有逻辑

        Args:
            file_path: 文件路径
        """
        self.is_batch_mode = False
        self._clear_last_batch_snapshot()
        self.file_queue_manager.clear_queue()
        self.file_panel.hide_queue()

        self.input_file_path = file_path
        self.output_file_path = None
        self.file_panel.set_export_enabled(False)

        # 获取文件扩展名判断文件类型
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext in IMAGE_FILE_EXTENSIONS:
            # 图片文件
            self.preview_panel.set_image(file_path)
            self.preview_panel.set_manual_selection_image(file_path)
            status_msg = f"✅ 已选择图片: {os.path.basename(file_path)}"
            self.log_panel.add_status_message(f"图片文件已加载: {os.path.basename(file_path)}")

        elif file_ext in VIDEO_FILE_EXTENSIONS:
            # 视频文件
            first_frame = self._extract_video_first_frame(file_path)
            if first_frame is not None:
                self.preview_panel.set_image_from_array(first_frame)
                self.preview_panel.set_manual_selection_image_from_array(first_frame)
                status_msg = f"✅ 已选择视频: {os.path.basename(file_path)} (显示第一帧)"
                self.log_panel.add_status_message(f"视频文件已加载: {os.path.basename(file_path)}")
            else:
                self.preview_panel.show_video_placeholder(file_path)
                status_msg = f"✅ 已选择视频: {os.path.basename(file_path)}"
                self.log_panel.add_warning_log(f"视频文件已加载，但无法预览: {os.path.basename(file_path)}")

        else:
            # 不支持的格式
            status_msg = f"⚠️ 不支持的文件格式: {file_ext}"
            self.log_panel.add_warning_log(status_msg)
            self.logger.warning(f"Unsupported file format: {file_ext}")
            return

        self.control_panel.set_start_button_enabled(True)
        self.status_updated.emit(status_msg)

        # 如果当前是手动模式，自动切换到手动选择标签页
        if hasattr(self.file_panel, "is_manual_mode") and self.file_panel.is_manual_mode():
            self.preview_panel.switch_to_manual_tab()

        self.logger.info(f"File imported: {file_path} ({file_ext})")

    def _handle_multiple_files(self, file_paths: list):
        """
        处理多个文件 - 进入队列模式

        Args:
            file_paths: 文件路径列表
        """
        self.is_batch_mode = True
        self.input_file_path = file_paths[0]  # 第一个文件用于预览
        self.output_file_path = None
        self.file_panel.set_export_enabled(False)

        # 清空旧队列，添加新文件
        self._clear_last_batch_snapshot()
        self.file_queue_manager.clear_queue()
        for path in file_paths:
            self.file_queue_manager.add_file(path)

        # 更新UI
        self._update_file_queue_display()
        self.file_panel.show_queue()

        # 预览第一个文件
        file_ext = os.path.splitext(file_paths[0])[1].lower()

        if file_ext in IMAGE_FILE_EXTENSIONS:
            self.preview_panel.set_image(file_paths[0])
        elif file_ext in VIDEO_FILE_EXTENSIONS:
            first_frame = self._extract_video_first_frame(file_paths[0])
            if first_frame is not None:
                self.preview_panel.set_image_from_array(first_frame)

        # 更新状态
        status_msg = f"✅ 已选择 {len(file_paths)} 个文件，准备批量处理"
        self.status_updated.emit(status_msg)
        self.log_panel.add_status_message(f"已添加 {len(file_paths)} 个文件到队列")

        self.control_panel.set_start_button_enabled(True)
        self.logger.info(f"Added {len(file_paths)} files to batch queue")

    def _show_save_dialog(
        self, parent, title: str, filters: str, default_filename: Optional[str] = None
    ):
        """
        显示保存文件对话框

        Args:
            parent: 父窗口组件
            title: 对话框标题
            filters: 文件过滤器
            default_filename: 默认文件名（可选）

        Returns:
            (file_path, selected_filter) 元组
        """
        from PyQt6.QtWidgets import QFileDialog

        last_dir = self.preferences.get_preference(
            "paths", "last_output_dir", os.path.expanduser("~")
        )
        initial_path = (
            os.path.join(last_dir, default_filename) if default_filename else str(last_dir)
        )
        file_path, selected_filter = QFileDialog.getSaveFileName(
            parent, title, initial_path, filters
        )

        if file_path:
            self.preferences.set_preference("paths", "last_output_dir", os.path.dirname(file_path))

        return file_path, selected_filter

    # ==================== 批处理相关方法 ====================

    def _start_batch_processing(self):  # noqa: C901
        """启动批量处理"""
        self._batch_stop_requested = False
        queue = self.file_queue_manager.get_queue()
        if not queue:
            self.log_panel.add_warning_log("处理队列为空")
            return

        self.status_updated.emit(f"开始批量处理 {len(queue)} 个文件...")

        # 获取高级参数
        advanced_params = {}
        if hasattr(self.control_panel, "get_advanced_parameters"):
            advanced_params = self.control_panel.get_advanced_parameters()

        params_builder = AIParamsBuilder()
        (
            ai_params,
            file_ai_params_by_index,
            file_ai_params_by_file_id,
            file_runtime_performance_by_index,
            file_runtime_performance_by_file_id,
            batch_config,
            runtime_config,
        ) = self._build_batch_runtime_payloads(
            queue=queue,
            params_builder=params_builder,
            advanced_params=advanced_params,
        )
        for index, queue_item in enumerate(queue):
            file_id = str(queue_item.get("file_id", "") or "")

            file_runtime_performance = None
            if file_id:
                file_runtime_performance = file_runtime_performance_by_file_id.get(file_id)
            if file_runtime_performance is None:
                file_runtime_performance = file_runtime_performance_by_index.get(index)
            if file_runtime_performance is not None:
                updated_runtime = False
                if file_id and hasattr(
                    self.file_queue_manager, "update_file_runtime_performance_by_id"
                ):
                    updated_runtime = bool(
                        self.file_queue_manager.update_file_runtime_performance_by_id(
                            file_id,
                            file_runtime_performance,
                        )
                    )
                if not updated_runtime:
                    self.file_queue_manager.update_file_runtime_performance(
                        index, file_runtime_performance
                    )

            file_ai_params = None
            if file_id:
                file_ai_params = file_ai_params_by_file_id.get(file_id)
            if file_ai_params is None:
                file_ai_params = file_ai_params_by_index.get(index)
            if not file_ai_params:
                continue

            if file_id and hasattr(self.file_queue_manager, "update_file_ai_params_by_id"):
                self.file_queue_manager.update_file_ai_params_by_id(file_id, file_ai_params)
            elif hasattr(self.file_queue_manager, "update_file_ai_params"):
                self.file_queue_manager.update_file_ai_params(index, file_ai_params)

            input_path = str(queue_item.get("input_path", "") or "")
            if not input_path:
                continue

            output_path = resolve_output_path(input_path, file_ai_params)
            updated_output_path = False
            if file_id and hasattr(self.file_queue_manager, "update_file_output_path_by_id"):
                updated_output_path = bool(
                    self.file_queue_manager.update_file_output_path_by_id(file_id, output_path)
                )
            if not updated_output_path:
                self.file_queue_manager.update_file_output_path(index, output_path)

            output_config_snapshot = self._build_output_config_snapshot(file_ai_params)
            updated_output_config = False
            if file_id and hasattr(self.file_queue_manager, "update_file_output_config_by_id"):
                updated_output_config = bool(
                    self.file_queue_manager.update_file_output_config_by_id(
                        file_id,
                        output_config_snapshot,
                    )
                )
            if not updated_output_config and hasattr(
                self.file_queue_manager, "update_file_output_config"
            ):
                self.file_queue_manager.update_file_output_config(index, output_config_snapshot)

        queue = self.file_queue_manager.get_queue()

        max_concurrent_files = int(batch_config.get("max_concurrent_files", 1) or 1)
        auto_retry_failed = bool(batch_config.get("auto_retry_failed", True))
        max_retry_count = int(batch_config.get("max_retry_count", 3) or 0)
        self._remember_last_batch_snapshot(
            ai_params=ai_params,
            batch_config=batch_config,
            runtime_config=runtime_config,
        )

        preloaded_ai_handler = None
        if self.main_window and hasattr(self.main_window, "ai_handler"):
            preloaded_ai_handler = self.main_window.ai_handler

        self.batch_processor = BatchProcessorThread(
            queue=queue,
            ai_params=ai_params,
            file_ai_params_by_index=file_ai_params_by_index,
            file_ai_params_by_file_id=file_ai_params_by_file_id,
            config=self.main_window.config if self.main_window else None,
            preloaded_ai_handler=preloaded_ai_handler,
            max_concurrent_files=max_concurrent_files,
            auto_retry_failed=auto_retry_failed,
            max_retry_count=max_retry_count,
        )

        self.batch_processor.current_file_changed.connect(self._on_batch_file_changed)
        self.batch_processor.file_progress.connect(self._on_batch_file_progress)
        self.batch_processor.overall_progress.connect(self._on_batch_overall_progress)
        self.batch_processor.file_completed.connect(self._on_batch_file_completed)
        self.batch_processor.batch_completed.connect(self._on_batch_completed)
        self.batch_processor.status_message.connect(self._on_batch_status)

        self.batch_processor.start()
        self.logger.info("Batch processing started")

    def _resolve_batch_file_id(self, index: int) -> Optional[str]:
        """根据批处理线程索引解析稳定 file_id。"""
        if self.batch_processor is None:
            return None

        queue = getattr(self.batch_processor, "file_queue", None)
        if not isinstance(queue, list):
            queue = getattr(self.batch_processor, "queue", None)
        if not isinstance(queue, list):
            return None
        if index < 0 or index >= len(queue):
            return None

        item = queue[index]
        if not isinstance(item, dict):
            return None

        file_id = str(item.get("file_id", "") or "").strip()
        return file_id or None

    def _on_batch_file_changed(self, index: int, filename: str):
        """批处理当前文件变化。"""
        if self._batch_stop_requested:
            return

        has_batch_context = self.batch_processor is not None
        file_id = self._resolve_batch_file_id(index)
        if has_batch_context and not file_id:
            self.logger.debug("批处理回调未解析到稳定 file_id，忽略当前文件变化: index=%s", index)
            return

        if file_id and hasattr(self.file_queue_manager, "update_file_status_by_id"):
            updated = bool(
                self.file_queue_manager.update_file_status_by_id(
                    file_id,
                    ProcessingStatus.PROCESSING,
                )
            )
            if not updated:
                self.logger.debug("批处理文件已从队列移除，忽略当前文件变化回调: file_id=%s", file_id)
                return
        elif has_batch_context:
            self.logger.debug(
                "文件队列管理器缺少 file_id 状态更新接口，忽略当前文件变化: file_id=%s",
                file_id,
            )
            return
        else:
            self.file_queue_manager.update_file_status(index, ProcessingStatus.PROCESSING)

        self._update_file_queue_display()
        self.preview_panel.show_processing_progress(
            self._build_processing_progress_message(filename)
        )
        self.status_updated.emit(self._build_batch_processing_status_message(filename))

    def _on_batch_file_progress(self, progress: int, file_index: int):
        """批处理文件进度更新。"""
        if self._batch_stop_requested:
            return

        has_batch_context = self.batch_processor is not None
        file_id = self._resolve_batch_file_id(file_index)
        if has_batch_context and not file_id:
            self.logger.debug("批处理回调未解析到稳定 file_id，忽略进度更新: index=%s", file_index)
            return

        if file_id and hasattr(self.file_queue_manager, "update_file_status_by_id"):
            updated = bool(
                self.file_queue_manager.update_file_status_by_id(
                    file_id,
                    ProcessingStatus.PROCESSING,
                    progress,
                )
            )
            if not updated:
                self.logger.debug("批处理文件已从队列移除，忽略进度回调: file_id=%s", file_id)
                return
        elif has_batch_context:
            self.logger.debug(
                "文件队列管理器缺少 file_id 状态更新接口，忽略进度回调: file_id=%s",
                file_id,
            )
            return
        else:
            self.file_queue_manager.update_file_status(
                file_index,
                ProcessingStatus.PROCESSING,
                progress,
            )

        self._update_file_queue_display()

    def _on_batch_overall_progress(self, progress: int) -> None:
        """批处理总体进度更新"""
        if self._batch_stop_requested:
            return
        self.control_panel.update_progress(progress)

    def _on_batch_file_completed(  # noqa: C901
        self,
        index: int,
        output_path: str,
        status: object,
        error_message: str,
        processing_details: object,
    ) -> None:
        """批处理单个文件完成。"""
        final_status = status if isinstance(status, ProcessingStatus) else ProcessingStatus.FAILED
        safe_error = str(error_message or "").strip()

        has_batch_context = self.batch_processor is not None
        file_id = self._resolve_batch_file_id(index)
        if has_batch_context and not file_id:
            self.logger.debug("批处理回调未解析到稳定 file_id，忽略完成回调: index=%s", index)
            return
        resolved_file_id = file_id or ""

        supports_lookup_by_id = has_batch_context and hasattr(
            self.file_queue_manager,
            "get_file_info_by_id",
        )
        supports_details_by_id = has_batch_context and hasattr(
            self.file_queue_manager,
            "update_file_processing_details_by_id",
        )
        supports_status_by_id = has_batch_context and hasattr(
            self.file_queue_manager,
            "update_file_status_by_id",
        )

        if processing_details is not None:
            if supports_details_by_id:
                updated_details = bool(
                    self.file_queue_manager.update_file_processing_details_by_id(
                        resolved_file_id,
                        processing_details,
                    )
                )
                if not updated_details and supports_lookup_by_id:
                    if self.file_queue_manager.get_file_info_by_id(resolved_file_id) is None:
                        self.logger.debug("批处理文件已从队列移除，忽略处理详情回写: file_id=%s", file_id)
                        return
                if not updated_details:
                    self.file_queue_manager.update_file_processing_details(
                        index, processing_details
                    )
            else:
                self.file_queue_manager.update_file_processing_details(index, processing_details)

        if supports_lookup_by_id:
            current = self.file_queue_manager.get_file_info_by_id(resolved_file_id)
            if current is None:
                self.logger.debug("批处理文件已从队列移除，忽略完成回调: file_id=%s", file_id)
                return
        else:
            current = self.file_queue_manager.get_file_info(index) or {}

        if final_status == ProcessingStatus.CANCELLED:
            current_progress = int(current.get("progress", 0) or 0)
            if supports_status_by_id:
                updated_status = bool(
                    self.file_queue_manager.update_file_status_by_id(
                        resolved_file_id,
                        ProcessingStatus.CANCELLED,
                        current_progress,
                        safe_error or "用户取消",
                    )
                )
                if not updated_status and supports_lookup_by_id:
                    self.logger.debug("批处理文件已从队列移除，忽略取消状态回写: file_id=%s", file_id)
                    return
                if not updated_status:
                    self.file_queue_manager.update_file_status(
                        index,
                        ProcessingStatus.CANCELLED,
                        current_progress,
                        safe_error or "用户取消",
                    )
            else:
                self.file_queue_manager.update_file_status(
                    index,
                    ProcessingStatus.CANCELLED,
                    current_progress,
                    safe_error or "用户取消",
                )
        elif final_status == ProcessingStatus.FAILED:
            if supports_status_by_id:
                updated_status = bool(
                    self.file_queue_manager.update_file_status_by_id(
                        resolved_file_id,
                        ProcessingStatus.FAILED,
                        100,
                        safe_error or "处理失败",
                    )
                )
                if not updated_status and supports_lookup_by_id:
                    self.logger.debug("批处理文件已从队列移除，忽略失败状态回写: file_id=%s", file_id)
                    return
                if not updated_status:
                    self.file_queue_manager.update_file_status(
                        index,
                        ProcessingStatus.FAILED,
                        100,
                        safe_error or "处理失败",
                    )
            else:
                self.file_queue_manager.update_file_status(
                    index,
                    ProcessingStatus.FAILED,
                    100,
                    safe_error or "处理失败",
                )
        else:
            if supports_status_by_id:
                updated_status = bool(
                    self.file_queue_manager.update_file_status_by_id(
                        resolved_file_id,
                        final_status,
                        100,
                        "",
                    )
                )
                if not updated_status and supports_lookup_by_id:
                    self.logger.debug("批处理文件已从队列移除，忽略完成状态回写: file_id=%s", file_id)
                    return
                if not updated_status:
                    self.file_queue_manager.update_file_status(index, final_status, 100, "")
            else:
                self.file_queue_manager.update_file_status(index, final_status, 100, "")

        self._update_file_queue_display()

    def _on_batch_completed(self):
        """批处理全部完成"""
        self.control_panel.set_processing_state(False)

        # 取消路径：将未完成项统一标记为 CANCELLED，避免误判为 FAILED/COMPLETED
        if self._batch_stop_requested or (
            self.batch_processor and self.batch_processor.should_stop
        ):
            queue = self.file_queue_manager.get_queue()
            for idx, item in enumerate(queue):
                item_status = item.get("status")
                if item_status in (ProcessingStatus.WAITING, ProcessingStatus.PROCESSING):
                    progress = int(item.get("progress", 0) or 0)
                    self.file_queue_manager.update_file_status(
                        idx, ProcessingStatus.CANCELLED, progress, "用户取消"
                    )

            self._update_file_queue_display()

            total = self.file_queue_manager.get_queue_size()
            completed = self.file_queue_manager.get_completed_count()
            failed = self.file_queue_manager.get_failed_count()
            cancelled = sum(
                1
                for item in self.file_queue_manager.get_queue()
                if item.get("status") == ProcessingStatus.CANCELLED
            )

            msg = f"批量处理已取消: 成功 {completed} 个, 失败 {failed} 个, 取消 {cancelled} 个 (共 {total} 个)"
            self.status_updated.emit(msg)
            self.log_panel.add_warning_log(msg)
        else:
            # 正常完成路径
            stats = {
                "total": self.file_queue_manager.get_queue_size(),
                "completed": self.file_queue_manager.get_completed_count(),
                "failed": self.file_queue_manager.get_failed_count(),
            }

            self.status_updated.emit(
                f"批量处理完成: {stats['completed']}/{stats['total']} 成功, {stats['failed']} 失败"
            )
            self.log_panel.add_success_message(
                f"批量处理完成: 成功 {stats['completed']} 个, 失败 {stats['failed']} 个"
            )

        self._batch_stop_requested = False
        self.batch_processor = None

    def _on_batch_status(self, message: str):
        """批处理状态消息"""
        self.log_panel.add_status_message(message)

    def _update_file_queue_display(self):
        """更新文件队列显示"""
        queue = self.file_queue_manager.get_queue()
        self.file_panel.update_queue_display(queue)

    def handle_queue_clear(self):
        """处理清空队列请求"""
        self._clear_last_batch_snapshot()
        self.file_queue_manager.clear_queue()
        self.file_panel.hide_queue()
        self.is_batch_mode = False
        self.input_file_path = None
        self.output_file_path = None
        self.file_panel.set_export_enabled(False)
        self.control_panel.set_start_button_enabled(False)
        self.status_updated.emit("队列已清空")

    def handle_file_remove(self, index: int):  # noqa: C901
        """处理移除文件请求"""
        target_item = self.file_queue_manager.get_file_info(index)
        if target_item is None:
            self.status_updated.emit("未找到要移除的队列项")
            return

        target_file_id = str(target_item.get("file_id", "") or "").strip()
        target_status = target_item.get("status")

        if (
            self.batch_processor is not None
            and hasattr(self.batch_processor, "isRunning")
            and self.batch_processor.isRunning()
            and not getattr(self.batch_processor, "should_stop", False)
        ):
            if target_status != ProcessingStatus.WAITING:
                self.log_panel.add_warning_log("仅允许在批量处理中移除等待中的队列项")
                self.status_updated.emit("当前队列项已开始处理，无法移除")
                return

            if not target_file_id or not hasattr(self.batch_processor, "remove_pending_file"):
                self.log_panel.add_warning_log("当前批处理线程不支持按 file_id 移除等待项")
                self.status_updated.emit("当前批处理线程不支持移除等待项")
                return

            removed = bool(self.batch_processor.remove_pending_file(target_file_id))
            if not removed:
                self.log_panel.add_warning_log("该等待项已提交执行或正在处理，无法安全移除")
                self.status_updated.emit("该等待项已提交执行，无法移除")
                return

            queue_removed = False
            if hasattr(self.file_queue_manager, "remove_file_by_id"):
                queue_removed = bool(self.file_queue_manager.remove_file_by_id(target_file_id))
            if not queue_removed:
                queue_removed = bool(self.file_queue_manager.remove_file(index))
            if not queue_removed:
                self.status_updated.emit("移除等待项失败")
                return

            self._clear_last_batch_snapshot()
            queue = self.file_queue_manager.get_queue()
            if not queue:
                self.handle_queue_clear()
            else:
                self._update_file_queue_display()
                self.status_updated.emit(f"已移除等待项，队列中还有 {len(queue)} 个文件")
            return

        self.file_queue_manager.remove_file(index)

        queue = self.file_queue_manager.get_queue()
        if not queue:
            self.handle_queue_clear()
        else:
            self._clear_last_batch_snapshot()
            self._update_file_queue_display()
            self.status_updated.emit(f"队列中还有 {len(queue)} 个文件")

    def handle_open_output_dir(self, index: int) -> None:
        """
        打开输出目录（批量模式辅助功能）

        优先打开“当前选中项”的输出目录；若未选中，则打开队列第一个文件的输出目录。
        若输出文件尚未生成，则打开输出路径所在目录（通常与输入目录一致）。
        """
        file_info = self._get_queue_item_or_first(index)
        if not file_info:
            self.log_panel.add_warning_log("处理队列为空")
            return

        input_path = str(file_info.get("input_path", "") or "")
        output_path = str(file_info.get("output_path", "") or "")

        directory = self._resolve_output_directory(input_path=input_path, output_path=output_path)
        if not directory:
            self.log_panel.add_warning_log("无法确定输出目录")
            return

        if not os.path.isdir(directory):
            self.log_panel.add_warning_log(f"输出目录不存在: {directory}")
            return

        ok, msg = self._open_path_in_file_manager(directory=directory, output_path=output_path)
        if ok:
            self.status_updated.emit(msg)
            self.log_panel.add_status_message(msg)
        else:
            self.log_panel.add_warning_log(msg)

    def _get_queue_item_or_first(self, index: int) -> Optional[dict[str, Any]]:
        """获取队列项：优先 index，否则返回第一个。"""
        queue = self.file_queue_manager.get_queue()
        if not queue:
            return None

        if 0 <= index < len(queue):
            return queue[index]
        return queue[0]

    def _resolve_output_directory(self, input_path: str, output_path: str) -> str:
        """从输入/输出路径解析需要打开的目录。"""
        if output_path:
            return os.path.dirname(output_path)
        if input_path:
            return os.path.dirname(input_path)
        return ""

    def _open_path_in_file_manager(  # noqa: C901
        self, directory: str, output_path: str
    ) -> tuple[bool, str]:
        """使用系统文件管理器打开目录或定位输出文件。"""
        try:
            if os.name == "nt":
                windir = os.environ.get("WINDIR") or r"C:\Windows"
                explorer = os.path.join(windir, "explorer.exe")

                if output_path and os.path.isfile(output_path):
                    result = subprocess.run([explorer, "/select,", output_path], check=False)
                    if result.returncode != 0:
                        return (
                            False,
                            f"无法打开资源管理器定位文件（返回码 {result.returncode}）",
                        )
                    return (True, f"已定位输出文件: {os.path.basename(output_path)}")

                result = subprocess.run([explorer, directory], check=False)
                if result.returncode != 0:
                    return (False, f"无法打开输出目录（返回码 {result.returncode}）")
                return (True, f"已打开输出目录: {directory}")

            if sys.platform == "darwin":
                open_cmd = "/usr/bin/open"
                result = subprocess.run([open_cmd, directory], check=False)
                if result.returncode != 0:
                    return (False, f"当前环境无法打开文件管理器（返回码 {result.returncode}）")
                return (True, f"已打开输出目录: {directory}")

            xdg_open = shutil.which("xdg-open")
            if not xdg_open:
                return (False, "当前环境缺少 xdg-open，无法打开文件管理器")

            result = subprocess.run([xdg_open, directory], check=False)
            if result.returncode != 0:
                return (False, f"当前环境无法打开文件管理器（返回码 {result.returncode}）")
            return (True, f"已打开输出目录: {directory}")

        except Exception as e:  # noqa: BLE001
            return (False, f"打开输出目录失败: {e}")

    def handle_export_batch_manifest(self, parent_widget) -> None:  # noqa: C901
        """
        导出批处理清单（JSON）

        用于保存当前队列的处理状态，便于追溯与排查问题。
        """
        queue = self.file_queue_manager.get_queue()
        if not queue:
            self.log_panel.add_warning_log("处理队列为空")
            return

        stats = {
            "total": self.file_queue_manager.get_queue_size(),
            "completed": self.file_queue_manager.get_completed_count(),
            "failed": self.file_queue_manager.get_failed_count(),
            "processing": self.file_queue_manager.get_processing_count(),
            "pending": self.file_queue_manager.get_pending_count(),
        }

        manifest_items: list[dict[str, Any]] = []

        run_ai_params: Optional[dict] = None
        ai_params_source: str = "none"
        ai_params_generated_at: Optional[str] = None
        batch_config: Optional[dict] = None
        runtime_config: Optional[dict] = None
        computed_item_runtime_performance: dict[int, dict[str, Any]] = {}
        computed_item_ai_params: dict[int, dict[str, Any]] = {}

        if self.batch_processor is not None and hasattr(self.batch_processor, "ai_params"):
            run_ai_params = dict(getattr(self.batch_processor, "ai_params", {}) or {})
            ai_params_source = "batch_processor"
            ai_params_generated_at = self._last_batch_ai_params_generated_at
            batch_config = {
                "max_concurrent_files": getattr(self.batch_processor, "max_concurrent_files", None),
                "auto_retry_failed": getattr(self.batch_processor, "auto_retry_failed", None),
                "max_retry_count": getattr(self.batch_processor, "max_retry_count", None),
            }
            runtime_config = dict(self._last_batch_runtime_config or {})
            if not runtime_config:
                runtime_config = self._build_runtime_config_snapshot(
                    ai_params=run_ai_params,
                    batch_config=batch_config,
                )
        elif self._last_batch_ai_params is not None:
            run_ai_params = dict(self._last_batch_ai_params)
            ai_params_source = "last_batch"
            ai_params_generated_at = self._last_batch_ai_params_generated_at
            batch_config = dict(self._last_batch_config or {})
            runtime_config = dict(self._last_batch_runtime_config or {})
            if not runtime_config:
                runtime_config = self._build_runtime_config_snapshot(
                    ai_params=run_ai_params,
                    batch_config=batch_config,
                )
        else:
            # 兜底：按当前 UI/偏好构建一次参数快照（可能与实际运行参数不一致）
            try:
                advanced_params = {}
                if hasattr(self.control_panel, "get_advanced_parameters"):
                    advanced_params = self.control_panel.get_advanced_parameters()
                params_builder = AIParamsBuilder()
                (
                    run_ai_params,
                    computed_item_ai_params,
                    _computed_item_ai_params_by_file_id,
                    computed_item_runtime_performance,
                    _computed_item_runtime_performance_by_file_id,
                    batch_config,
                    runtime_config,
                ) = self._build_batch_runtime_payloads(
                    queue=queue,
                    params_builder=params_builder,
                    advanced_params=advanced_params,
                )
                ai_params_source = "computed_at_export"
                ai_params_generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception as exc:  # noqa: BLE001
                self.logger.debug(f"导出清单时构建参数快照失败（不影响导出）: {exc}")

        manifest: dict[str, Any] = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "app_version": None,
            "platform": sys.platform,
            "os_name": os.name,
            "stats": stats,
            "batch": {
                "max_concurrent_files": (
                    batch_config.get("max_concurrent_files")
                    if isinstance(batch_config, dict)
                    else None
                ),
                "auto_retry_failed": (
                    batch_config.get("auto_retry_failed")
                    if isinstance(batch_config, dict)
                    else None
                ),
                "max_retry_count": (
                    batch_config.get("max_retry_count") if isinstance(batch_config, dict) else None
                ),
            },
            "run": {
                "ai_params": self._make_json_safe(run_ai_params) if run_ai_params else None,
                "ai_params_source": ai_params_source,
                "ai_params_generated_at": ai_params_generated_at,
                "runtime_performance": (
                    self._make_json_safe(runtime_config) if runtime_config else None
                ),
            },
            "items": manifest_items,
        }

        try:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app and hasattr(app, "applicationVersion"):
                version = str(app.applicationVersion() or "").strip()
                manifest["app_version"] = version if version else None
        except Exception as e:  # noqa: BLE001
            self.logger.debug(f"获取应用版本失败（不影响清单导出）: {e}")

        for idx, item in enumerate(queue):
            status = item.get("status")
            if isinstance(status, ProcessingStatus):
                status_value = status.value
            else:
                status_value = str(status)
            item_runtime_performance = item.get("runtime_performance")
            if item_runtime_performance is None:
                item_runtime_performance = computed_item_runtime_performance.get(idx)
            item_output_config = item.get("output_config")
            if item_output_config is None:
                item_ai_params = computed_item_ai_params.get(idx)
                if item_ai_params:
                    item_output_config = self._build_output_config_snapshot(item_ai_params)
            item_output_path = item.get("output_path", "")
            if ai_params_source == "computed_at_export":
                item_ai_params = computed_item_ai_params.get(idx)
                input_path = str(item.get("input_path", "") or "")
                if input_path and item_ai_params:
                    item_output_path = resolve_output_path(input_path, item_ai_params)
            manifest_items.append(
                {
                    "index": idx,
                    "file_id": item.get("file_id"),
                    "input_path": item.get("input_path", ""),
                    "output_path": item_output_path,
                    "status": status_value,
                    "progress": int(item.get("progress", 0) or 0),
                    "error_message": item.get("error_message", ""),
                    "processing_details": self._make_json_safe(item.get("processing_details")),
                    "runtime_performance": self._make_json_safe(item_runtime_performance),
                    "output_config": self._make_json_safe(item_output_config),
                }
            )

        default_name = f"batch_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = self._show_save_dialog(
            parent_widget,
            "导出批处理清单",
            "JSON文件 (*.json);;所有文件 (*)",
            default_filename=default_name,
        )

        if not file_path:
            return

        try:
            target_path = Path(file_path)
            if target_path.suffix.lower() != ".json":
                target_path = target_path.with_suffix(".json")

            target_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self.preferences.set_preference("paths", "last_output_dir", str(target_path.parent))

            self.status_updated.emit(f"批处理清单已导出: {target_path.name}")
            self.log_panel.add_success_message(f"批处理清单导出成功: {target_path}")
            self.logger.info(f"Batch manifest exported: {target_path}")

        except Exception as e:
            error_msg = f"批处理清单导出失败: {e}"
            self.log_panel.add_error_message(error_msg)
            self.logger.error(error_msg)

    def _remember_last_batch_snapshot(
        self,
        ai_params: dict,
        batch_config: dict,
        runtime_config: Optional[dict] = None,
    ) -> None:
        """缓存最近一次批处理运行快照，供任务结束后导出 manifest 使用。"""
        self._last_batch_ai_params = dict(ai_params)
        self._last_batch_ai_params_generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._last_batch_config = dict(batch_config)
        self._last_batch_runtime_config = dict(runtime_config or {})

    def _clear_last_batch_snapshot(self) -> None:
        """清空最近一次批处理运行快照，避免新队列误复用旧批次参数。"""
        self._last_batch_ai_params = None
        self._last_batch_ai_params_generated_at = None
        self._last_batch_config = None
        self._last_batch_runtime_config = None

    def _build_file_runtime_payload(
        self,
        *,
        params_builder: Any,
        advanced_params: dict,
        input_file_path: Optional[str],
    ) -> tuple[dict[str, Any], ResolvedPerformanceConfig]:
        """构建单文件实际运行时参数与统一性能快照。"""
        ai_params = params_builder.build_from_ui(
            preferences=self.preferences,
            advanced_params=advanced_params,
            manual_selections=self.manual_selections,
            input_file_path=input_file_path,
            is_batch=True,
        )
        runtime_config = self._resolve_runtime_performance_config(
            params_builder=params_builder,
            advanced_params=advanced_params,
            input_file_path=input_file_path,
            is_batch=True,
            ai_params=ai_params,
        )
        return (ai_params, runtime_config)

    @staticmethod
    def _build_output_config_snapshot(
        ai_params: Optional[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """从运行时参数中提取可导出的输出配置快照。"""
        if not ai_params:
            return None
        snapshot = AdvancedParamsSnapshot.from_dict(ai_params)
        return snapshot.resolve_output_config().to_ai_params()

    @staticmethod
    def _summarize_mixed_values(values: list[Any], *, mixed_value: Any = None) -> Any:
        """若文件级值不一致，则返回 mixed_value。"""
        if not values:
            return None
        first_value = values[0]
        if all(value == first_value for value in values[1:]):
            return first_value
        return mixed_value

    def _build_batch_ai_params_summary(
        self,
        *,
        file_ai_params_by_index: dict[int, dict[str, Any]],
        runtime_config: dict[str, Any],
    ) -> dict[str, Any]:
        """为 manifest 与批次级兜底保留一份批次摘要参数。"""
        if not file_ai_params_by_index:
            return {}

        ordered_file_ai_params = [
            dict(file_ai_params_by_index[index]) for index in sorted(file_ai_params_by_index)
        ]
        summary = dict(ordered_file_ai_params[0])
        summary.pop("add_processed_suffix", None)

        if len(ordered_file_ai_params) == 1:
            return summary

        summary["processing_mode"] = self._summarize_mixed_values(
            [params.get("processing_mode") for params in ordered_file_ai_params],
            mixed_value="mixed",
        )
        summary["resolved_processing_mode"] = runtime_config.get("resolved_processing_mode")
        summary["enable_multiprocess"] = self._summarize_mixed_values(
            [params.get("enable_multiprocess") for params in ordered_file_ai_params],
        )
        summary["use_pipeline"] = self._summarize_mixed_values(
            [params.get("use_pipeline") for params in ordered_file_ai_params],
        )
        summary["num_processes"] = self._summarize_mixed_values(
            [params.get("num_processes") for params in ordered_file_ai_params],
        )
        summary["gpu_memory_mb"] = self._summarize_mixed_values(
            [params.get("gpu_memory_mb") for params in ordered_file_ai_params],
        )
        summary["enable_cache"] = self._summarize_mixed_values(
            [params.get("enable_cache") for params in ordered_file_ai_params],
        )
        summary["cache_size_mb"] = self._summarize_mixed_values(
            [params.get("cache_size_mb") for params in ordered_file_ai_params],
        )
        summary["output_format"] = self._summarize_mixed_values(
            [params.get("output_format") for params in ordered_file_ai_params],
            mixed_value="mixed",
        )
        summary["compression_quality"] = self._summarize_mixed_values(
            [params.get("compression_quality") for params in ordered_file_ai_params],
        )
        summary["add_suffix"] = self._summarize_mixed_values(
            [params.get("add_suffix") for params in ordered_file_ai_params],
        )
        summary["add_timestamp"] = self._summarize_mixed_values(
            [params.get("add_timestamp") for params in ordered_file_ai_params],
        )
        summary["preserve_audio"] = self._summarize_mixed_values(
            [params.get("preserve_audio") for params in ordered_file_ai_params],
        )
        summary.pop("add_processed_suffix", None)
        return summary

    def _build_batch_runtime_summary(
        self,
        file_runtime_performance: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """将文件级运行时配置汇总为批次摘要。"""
        if not file_runtime_performance:
            return {}

        summary = dict(file_runtime_performance[0])
        summary["resolution_scope"] = "file_level"

        string_fields = {
            "requested_processing_mode": "mixed",
            "resolved_processing_mode": "mixed",
        }
        scalar_fields = (
            "worker_count",
            "enable_multiprocess",
            "use_pipeline",
            "gpu_memory_budget_mb",
            "enable_cache",
            "cache_size_mb",
            "batch_max_concurrent_files",
            "batch_auto_retry_failed",
            "batch_max_retry_count",
        )

        for key, mixed_value in string_fields.items():
            summary[key] = self._summarize_mixed_values(
                [config.get(key) for config in file_runtime_performance],
                mixed_value=mixed_value,
            )

        for key in scalar_fields:
            summary[key] = self._summarize_mixed_values(
                [config.get(key) for config in file_runtime_performance]
            )

        distinct_requested_modes = sorted(
            {
                str(config.get("requested_processing_mode"))
                for config in file_runtime_performance
                if config.get("requested_processing_mode") is not None
            }
        )
        if len(distinct_requested_modes) > 1:
            summary["distinct_requested_processing_modes"] = distinct_requested_modes

        distinct_resolved_modes = sorted(
            {
                str(config.get("resolved_processing_mode"))
                for config in file_runtime_performance
                if config.get("resolved_processing_mode") is not None
            }
        )
        if len(distinct_resolved_modes) > 1:
            summary["distinct_resolved_processing_modes"] = distinct_resolved_modes

        return summary

    def _build_batch_runtime_payloads(
        self,
        *,
        queue: list[dict[str, Any]],
        params_builder: Any,
        advanced_params: dict,
    ) -> tuple[
        dict[str, Any],
        dict[int, dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[int, dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[str, Any],
        dict[str, Any],
    ]:
        """为批处理统一构建批次摘要、文件级参数与文件级运行时快照。"""
        file_ai_params_by_index: dict[int, dict[str, Any]] = {}
        file_ai_params_by_file_id: dict[str, dict[str, Any]] = {}
        file_runtime_performance_by_index: dict[int, dict[str, Any]] = {}
        file_runtime_performance_by_file_id: dict[str, dict[str, Any]] = {}

        for index, item in enumerate(queue):
            input_file_path = item.get("input_path") if isinstance(item, dict) else None
            file_id = str(item.get("file_id", "") or "").strip() if isinstance(item, dict) else ""
            ai_params, runtime_config = self._build_file_runtime_payload(
                params_builder=params_builder,
                advanced_params=advanced_params,
                input_file_path=input_file_path,
            )
            resolved_ai_params = dict(ai_params)
            resolved_runtime_config = runtime_config.to_manifest_dict()
            file_ai_params_by_index[index] = resolved_ai_params
            file_runtime_performance_by_index[index] = resolved_runtime_config
            if file_id:
                file_ai_params_by_file_id[file_id] = dict(resolved_ai_params)
                file_runtime_performance_by_file_id[file_id] = dict(resolved_runtime_config)

        ordered_runtime_performance = [
            file_runtime_performance_by_index[index]
            for index in sorted(file_runtime_performance_by_index)
        ]
        batch_runtime_config = self._build_batch_runtime_summary(ordered_runtime_performance)
        batch_ai_params = self._build_batch_ai_params_summary(
            file_ai_params_by_index=file_ai_params_by_index,
            runtime_config=batch_runtime_config,
        )
        batch_config = {
            "max_concurrent_files": int(
                batch_runtime_config.get("batch_max_concurrent_files", 1) or 1
            ),
            "auto_retry_failed": bool(batch_runtime_config.get("batch_auto_retry_failed", True)),
            "max_retry_count": int(batch_runtime_config.get("batch_max_retry_count", 3) or 0),
        }
        return (
            batch_ai_params,
            file_ai_params_by_index,
            file_ai_params_by_file_id,
            file_runtime_performance_by_index,
            file_runtime_performance_by_file_id,
            batch_config,
            batch_runtime_config,
        )

    def _resolve_runtime_performance_config(  # noqa: C901
        self,
        *,
        params_builder: Any,
        advanced_params: dict,
        input_file_path: Optional[str],
        is_batch: bool,
        ai_params: Optional[dict] = None,
    ) -> ResolvedPerformanceConfig:
        """优先复用 builder 的统一解析入口，必要时回退到运行时字段重建。"""
        build_runtime_config = getattr(params_builder, "build_resolved_performance_config", None)
        if callable(build_runtime_config):
            try:
                resolved_runtime_config = build_runtime_config(
                    advanced_params=advanced_params,
                    input_file_path=input_file_path,
                    is_batch=is_batch,
                )
                if isinstance(resolved_runtime_config, ResolvedPerformanceConfig):
                    return resolved_runtime_config
                to_manifest_dict = getattr(resolved_runtime_config, "to_manifest_dict", None)
                if callable(to_manifest_dict):
                    manifest = to_manifest_dict()
                    if isinstance(manifest, dict):
                        try:
                            return ResolvedPerformanceConfig(**manifest)
                        except TypeError:
                            self.logger.debug(
                                "builder.build_resolved_performance_config 返回了不完整 manifest，回退兼容路径"
                            )
            except TypeError:
                self.logger.debug("builder.build_resolved_performance_config 不支持新签名，回退兼容路径")

        batch_config = {}
        build_batch_config = getattr(params_builder, "build_batch_config", None)
        if callable(build_batch_config):
            try:
                batch_config = build_batch_config(
                    advanced_params,
                    input_file_path=input_file_path,
                )
            except TypeError:
                batch_config = build_batch_config(advanced_params)
        return ResolvedPerformanceConfig.from_runtime_sources(
            ai_params=ai_params,
            batch_config=batch_config,
        )

    def _build_runtime_config_snapshot(
        self,
        *,
        ai_params: Optional[dict],
        batch_config: Optional[dict],
    ) -> Optional[dict]:
        """根据运行时参数重建可导出的统一性能快照。"""
        if ai_params is None and batch_config is None:
            return None
        return ResolvedPerformanceConfig.from_runtime_sources(
            ai_params=ai_params,
            batch_config=batch_config,
        ).to_manifest_dict()

    @staticmethod
    def _try_call_json_method(value: Any, method_name: str) -> tuple[bool, Any]:
        """尝试调用对象上的序列化辅助方法。"""
        method = getattr(value, method_name, None)
        if not callable(method):
            return (False, None)

        try:
            return (True, method())
        except Exception:  # noqa: BLE001
            return (False, None)

    @staticmethod
    def _make_json_safe(value: Any) -> Any:
        """
        将对象转换为 json.dumps 可序列化的结构。

        说明：
        - 批处理清单是“排查与追溯”用途，遇到无法序列化的类型时，保守降级为字符串。
        """
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, Path):
            return str(value)

        if isinstance(value, Enum):
            return value.value

        if isinstance(value, dict):
            return {str(k): SignalHandler._make_json_safe(v) for k, v in value.items()}

        if isinstance(value, (list, tuple, set)):
            return [SignalHandler._make_json_safe(v) for v in value]

        # numpy 标量等：尽量提取为 Python 原生类型
        item_ok, item_value = SignalHandler._try_call_json_method(value, "item")
        if item_ok:
            return item_value

        list_ok, list_value = SignalHandler._try_call_json_method(value, "tolist")
        if list_ok:
            return list_value

        return str(value)

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
        if self.batch_processor and self.batch_processor.isRunning():
            self.batch_processor.stop()
            self.batch_processor.wait(2000)

        # 停止处理线程
        if self.video_processor_thread and self.video_processor_thread.isRunning():
            self.video_processor_thread.stop()
            self.video_processor_thread.wait(5000)

        self.logger.info("SignalHandler cleaned up")
