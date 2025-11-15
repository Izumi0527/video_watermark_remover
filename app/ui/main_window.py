from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QSplitter, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import os
import logging

# 导入重构后的组件
from .components.file_panel import FilePanel
from .components.preview_panel import PreviewPanel
from .components.control_panel import ControlPanel
from .components.log_panel import LogPanel

# 导入现有模块
from ..config.config_manager import ConfigManager
from ..config.modern_style_manager import ModernStyleManager
from ..config.user_preferences_manager import get_preferences_manager


class MainWindow(QMainWindow):
    """
    重构后的主窗口类
    采用模块化组件设计，单一职责原则
    每个UI组件独立管理自己的状态和逻辑
    """

    # 信号定义
    progress_signal = pyqtSignal(int)  # Progress updates
    status_signal = pyqtSignal(str)  # Status messages
    finished_signal = pyqtSignal(str)  # Completion signal

    def __init__(self, config=None):
        super().__init__()

        # 初始化核心属性
        self.config = config or ConfigManager.load_config()
        self.video_processor_thread = None
        self.input_file_path = None
        self.output_file_path = None
        self.manual_selections = []
        self.processed_image = None

        # 初始化偏好设置和样式管理
        self.preferences = get_preferences_manager()
        saved_theme = self.preferences.get_preference("ui", "theme", "dark")
        self.style_manager = ModernStyleManager(saved_theme)

        # 设置窗口属性
        self.setWindowTitle("智能视频水印去除工具 - v0.3.0 重构版")
        self._restore_window_geometry()

        # 初始化UI和连接信号
        self._init_ui()
        self._apply_modern_style()
        self._connect_signals()
        self._restore_ui_state()

        # 设置日志
        self.logger = logging.getLogger(__name__)
        self.logger.info("MainWindow initialized successfully (refactored version)")

    def _init_ui(self):
        """初始化用户界面 - 模块化组件组装"""
        # 创建中央部件和主布局
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 添加标题
        self._create_title_section(main_layout)

        # 创建主要内容区域 - 使用分割器
        content_splitter = QSplitter(Qt.Orientation.Vertical)

        # 创建顶部控制区域
        top_section = self._create_top_section()
        content_splitter.addWidget(top_section)

        # 创建底部日志区域
        self.log_panel = LogPanel()
        content_splitter.addWidget(self.log_panel)

        # 设置分割器比例 (75% 控制区域, 25% 日志区域)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(content_splitter)

    def _create_title_section(self, main_layout):
        """创建标题区域"""
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)

        title_label = QLabel("🎬 智能水印去除工具 - v0.3.0 重构版")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        self.lbl_status = QLabel("📁 请选择图片或视频文件开始处理...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("QLabel { color: #666; padding: 10px; }")
        main_layout.addWidget(self.lbl_status)

    def _create_top_section(self):
        """创建顶部控制区域"""
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)

        # 文件操作面板
        self.file_panel = FilePanel()
        top_layout.addWidget(self.file_panel)

        # 创建水平分割器用于预览和控制
        horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 预览面板
        self.preview_panel = PreviewPanel()
        horizontal_splitter.addWidget(self.preview_panel)

        # 控制面板
        self.control_panel = ControlPanel()
        horizontal_splitter.addWidget(self.control_panel)

        # 设置水平分割器比例 (70% 预览, 30% 控制)
        horizontal_splitter.setStretchFactor(0, 7)
        horizontal_splitter.setStretchFactor(1, 3)

        top_layout.addWidget(horizontal_splitter)

        return top_widget

    def _connect_signals(self):
        """连接组件信号 - 采用观察者模式"""

        # 文件面板信号
        self.file_panel.file_import_requested.connect(self._handle_import_file)
        self.file_panel.file_export_requested.connect(self._handle_export_file)
        self.file_panel.theme_toggle_requested.connect(self._handle_theme_toggle)
        self.file_panel.auto_mode_changed.connect(self._handle_auto_mode_changed)
        self.file_panel.manual_mode_changed.connect(self._handle_manual_mode_changed)

        # 预览面板信号
        self.preview_panel.manual_selection_changed.connect(self._handle_manual_selection_changed)

        # 控制面板信号
        self.control_panel.start_processing_requested.connect(self._handle_start_processing)
        self.control_panel.stop_processing_requested.connect(self._handle_stop_processing)
        self.control_panel.batch_processing_requested.connect(self._handle_batch_processing)

        # 内部信号连接到日志面板
        self.status_signal.connect(self.log_panel.add_status_message)
        self.progress_signal.connect(self._handle_progress_update)

    def _apply_modern_style(self):
        """应用现代化样式"""
        if hasattr(self.style_manager, "apply_style"):
            self.style_manager.apply_style(self)

        # 更新主题切换按钮文本
        current_theme = (
            self.style_manager.current_theme
            if hasattr(self.style_manager, "current_theme")
            else "dark"
        )
        theme_icon = "☀️" if current_theme == "dark" else "🌙"
        self.file_panel.btn_theme_toggle.setText(f"{theme_icon} 切换主题")

    def _restore_window_geometry(self):
        """恢复窗口几何信息"""
        try:
            geometry = self.preferences.get_preference("window", "geometry", None)
            if geometry:
                self.restoreGeometry(geometry)
            else:
                self.setMinimumSize(1200, 800)
                self.resize(1400, 900)
        except Exception as e:
            self.logger.warning(f"Failed to restore window geometry: {e}")
            self.setMinimumSize(1200, 800)
            self.resize(1400, 900)

    def _restore_ui_state(self):
        """恢复UI状态"""
        # 恢复处理模式
        auto_mode = self.preferences.get_preference("processing", "auto_mode", True)
        self.file_panel.auto_mode_checkbox.setChecked(auto_mode)
        self.file_panel.manual_mode_checkbox.setChecked(not auto_mode)

        # 恢复预览标签页
        tab_index = self.preferences.get_preference("ui", "preview_tab_index", 0)
        self.preview_panel.set_current_tab_index(tab_index)

    # 信号处理方法
    def _handle_import_file(self):
        """处理文件导入请求"""
        try:
            file_path, _ = self._show_file_dialog(
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
                self.lbl_status.setText(f"✅ 已选择文件: {os.path.basename(file_path)}")
                self.status_signal.emit(f"文件已加载: {os.path.basename(file_path)}")
                
                # 如果当前是手动模式，自动切换到手动选择标签页
                if hasattr(self.file_panel, 'is_manual_mode') and self.file_panel.is_manual_mode():
                    self.preview_panel.switch_to_manual_tab()

        except Exception as e:
            self.log_panel.add_error_message(f"文件导入失败: {str(e)}")

    def _handle_export_file(self):
        """处理文件导出请求"""
        if not self.processed_image:
            self.log_panel.add_warning_log("没有处理后的图像可导出")
            return

        try:
            file_path, _ = self._show_save_dialog(
                "保存处理后的文件", "PNG文件 (*.png);;JPEG文件 (*.jpg);;所有文件 (*)"
            )

            if file_path:
                # 这里应该保存处理后的图像
                self.status_signal.emit(f"文件已导出: {os.path.basename(file_path)}")
                self.log_panel.add_success_message(f"文件导出成功: {file_path}")

        except Exception as e:
            self.log_panel.add_error_message(f"文件导出失败: {str(e)}")

    def _handle_theme_toggle(self):
        """处理主题切换请求"""
        try:
            if hasattr(self.style_manager, "toggle_theme"):
                self.style_manager.toggle_theme()
                self._apply_modern_style()

                # 保存主题偏好
                current_theme = getattr(self.style_manager, "current_theme", "dark")
                self.preferences.set_preference("ui", "theme", current_theme)

                self.status_signal.emit(f"主题已切换为: {current_theme}")
        except Exception as e:
            self.log_panel.add_error_message(f"主题切换失败: {str(e)}")

    def _handle_auto_mode_changed(self, enabled):
        """处理自动模式变化"""
        self.preferences.set_preference("processing", "auto_mode", enabled)
        mode_text = "自动检测" if enabled else "手动选择"
        self.status_signal.emit(f"处理模式切换为: {mode_text}")

    def _handle_manual_mode_changed(self, enabled):
        """处理手动模式变化"""
        self.preferences.set_preference("processing", "auto_mode", not enabled)
        mode_text = "手动选择" if enabled else "自动检测"
        self.status_signal.emit(f"处理模式切换为: {mode_text}")
        
        # 如果启用手动模式且有已加载的图像，切换到手动选择标签页
        if enabled and self.input_file_path:
            self.preview_panel.switch_to_manual_tab()
        
        # 如果禁用手动模式，清空手动选择
        if not enabled:
            self.preview_panel.clear_manual_selections()
            self.manual_selections = []

    def _handle_manual_selection_changed(self, selections):
        """处理手动选择区域变化"""
        self.manual_selections = selections
        count = len(selections)
        self.status_signal.emit(f"手动选择了 {count} 个水印区域")

    def _handle_start_processing(self):
        """处理开始处理请求"""
        if not self.input_file_path:
            self.log_panel.add_warning_log("请先选择要处理的文件")
            return

        try:
            self.control_panel.set_processing_state(True)
            self.status_signal.emit("开始处理文件...")
            
            # 显示处理进度状态
            self.preview_panel.show_processing_progress()

            # 这里启动视频处理线程
            # TODO: 集成VideoProcessorThread
            
            # 为了测试对比功能，添加一个模拟处理完成
            from PyQt6.QtCore import QTimer
            self.test_timer = QTimer()
            self.test_timer.timeout.connect(self._simulate_processing_complete)
            self.test_timer.setSingleShot(True)
            self.test_timer.start(2000)  # 2秒后模拟完成

        except Exception as e:
            self.log_panel.add_error_message(f"处理启动失败: {str(e)}")
            self.control_panel.set_processing_state(False)
            
    def _simulate_processing_complete(self):
        """模拟处理完成（用于测试对比功能）"""
        try:
            # 模拟处理信息
            processing_info = {
                "detection_method": "手动选择" if self.manual_selections else "自动检测",
                "manual_regions_count": len(self.manual_selections) if self.manual_selections else 0,
                "auto_regions_count": 3 if not self.manual_selections else 0,
                "processing_time": 1.85
            }
            
            # 创建一个模拟的处理后图像（实际应用中这会是真正的处理结果）
            from PyQt6.QtGui import QPixmap
            if self.input_file_path:
                processed_pixmap = QPixmap(self.input_file_path)  # 暂时使用原图
                self.preview_panel.set_processed_image(processed_pixmap, processing_info)
                
            self.control_panel.set_processing_state(False)
            self.status_signal.emit("✅ 处理完成！")
            self.log_panel.add_info_log("图像处理完成，请查看对比效果")
            
        except Exception as e:
            self.log_panel.add_error_message(f"处理完成模拟失败: {str(e)}")

    def _handle_stop_processing(self):
        """处理停止处理请求"""
        self.control_panel.set_processing_state(False)
        self.status_signal.emit("处理已停止")

    def _handle_batch_processing(self):
        """处理批处理请求"""
        self.status_signal.emit("批处理功能启动")

    def _handle_progress_update(self, value):
        """处理进度更新"""
        self.control_panel.update_progress(value)
        self.log_panel.add_progress_message(f"处理进度: {value}%")

    # 工具方法
    def _show_file_dialog(self, title, filters):
        """显示文件选择对话框"""
        from PyQt6.QtWidgets import QFileDialog

        last_dir = self.preferences.get_preference(
            "paths", "last_input_dir", os.path.expanduser("~")
        )
        file_path, selected_filter = QFileDialog.getOpenFileName(self, title, last_dir, filters)

        if file_path:
            self.preferences.set_preference("paths", "last_input_dir", os.path.dirname(file_path))

        return file_path, selected_filter

    def _show_save_dialog(self, title, filters):
        """显示保存文件对话框"""
        from PyQt6.QtWidgets import QFileDialog

        last_dir = self.preferences.get_preference(
            "paths", "last_output_dir", os.path.expanduser("~")
        )
        file_path, selected_filter = QFileDialog.getSaveFileName(self, title, last_dir, filters)

        if file_path:
            self.preferences.set_preference("paths", "last_output_dir", os.path.dirname(file_path))

        return file_path, selected_filter

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            # 保存窗口几何信息
            self.preferences.set_preference("window", "geometry", self.saveGeometry())

            # 保存当前预览标签页
            current_tab = self.preview_panel.get_current_tab_index()
            self.preferences.set_preference("ui", "preview_tab_index", current_tab)

            # 停止处理线程
            if self.video_processor_thread and self.video_processor_thread.isRunning():
                self.video_processor_thread.quit()
                self.video_processor_thread.wait()

            self.logger.info("MainWindow closed successfully")
            event.accept()

        except Exception as e:
            self.logger.error(f"Error closing window: {e}")
            event.accept()
