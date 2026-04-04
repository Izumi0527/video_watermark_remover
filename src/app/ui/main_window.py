import logging

from PyQt6.QtCore import QEvent, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QSplitter, QVBoxLayout, QWidget

# 导入现有模块
from .. import APP_NAME, __version__
from ..config.config_manager import ConfigManager
from ..config.preferences import get_preferences_manager
from ..config.styles import ModernStyleManager
from ..config.styles.colors import DEFAULT_THEME
from .components.control_panel import ControlPanel

# 导入重构后的组件
from .components.file_panel import FilePanel
from .components.log_panel import LogPanel
from .components.preview_panel import PreviewPanel
from .signal_handler import SignalHandler


class AIModelPreloader(QThread):
    """
    AI模型预加载线程
    在后台异步加载AI模型，避免阻塞UI，提升用户体验
    """

    # 信号：加载完成时发送AIHandler实例
    finished = pyqtSignal(object)
    # 信号：加载失败时发送错误信息
    error = pyqtSignal(str)

    def __init__(self, config=None, ai_params=None, runtime_performance=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.ai_params = ai_params or {}
        self.runtime_performance = dict(runtime_performance or {})
        self.logger = logging.getLogger(__name__)

    def run(self):
        """后台加载AI模型"""
        try:
            self.logger.info("开始后台加载AI模型...")
            if self.runtime_performance:
                self.logger.info(
                    "预加载运行时配置: requested=%s resolved=%s workers=%s gpu_budget=%sMB",
                    self.runtime_performance.get("requested_processing_mode"),
                    self.runtime_performance.get("resolved_processing_mode"),
                    self.runtime_performance.get("worker_count"),
                    self.runtime_performance.get("gpu_memory_budget_mb"),
                )

            # 延迟导入（避免在 UI 模块导入阶段强依赖 torch）
            from ..core.ai.ai_handler import AIHandler  # noqa: WPS433

            # 创建 AIHandler 并加载模型
            # 重要：预加载必须尽量对齐默认任务参数，否则首任务仍会触发 refresh 二次加载。
            ai_handler = AIHandler(self.config, ai_params=self.ai_params)
            if ai_handler.load_models():
                self.logger.info("AI模型加载成功")
                self.finished.emit(ai_handler)
            else:
                error_msg = "AI模型加载失败"
                self.logger.error(error_msg)
                self.error.emit(error_msg)
        except Exception as e:
            error_msg = f"AI模型加载异常: {str(e)}"
            # 常见：Windows 下先加载 PyQt6(Qt DLL) 再加载 torch 可能触发 WinError 1114
            if isinstance(e, OSError) and getattr(e, "winerror", None) == 1114:
                error_msg += (
                    "\n可能原因：PyQt6/Qt 先加载了与 PyTorch 冲突的 DLL，导致 torch 初始化失败。"
                    "\n建议：使用 main.py 或 scripts/vwr.ps1 启动（本项目已在入口预加载 torch），"
                    "或重启终端/电脑后再试。"
                )
            self.logger.error(error_msg)
            self.error.emit(error_msg)


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

        # 设置日志（需早于依赖logger的调用）
        self.logger = logging.getLogger(__name__)

        # 初始化核心属性
        self.config = config or ConfigManager.load_config()

        # AI模型预加载相关
        self.ai_handler = None  # 预加载的AI处理器（全局共享）
        self.ai_preload_thread = None  # 预加载线程
        self.ai_models_ready = False  # AI模型是否已就绪
        self.last_preload_runtime_performance = None

        # 初始化偏好设置和样式管理
        self.preferences = get_preferences_manager()
        saved_theme = self.preferences.get_preference("ui", "theme", DEFAULT_THEME)
        self.style_manager = ModernStyleManager(saved_theme)

        # 设置窗口属性
        self.setWindowTitle(f"{APP_NAME} - v{__version__}")
        self._restore_window_geometry()

        # 初始化UI（必须在创建signal_handler之前）
        self._init_ui()

        # 创建信号处理器（依赖UI组件）
        self.signal_handler = SignalHandler(
            file_panel=self.file_panel,
            preview_panel=self.preview_panel,
            control_panel=self.control_panel,
            log_panel=self.log_panel,
            preferences=self.preferences,
            style_manager=self.style_manager,
            main_window=self,  # 传入主窗口引用，以便访问预加载的AI模型
            parent=self,
        )

        # 应用样式和连接信号
        self._apply_modern_style()
        self._connect_signals()
        self._restore_ui_state()

        # 记录初始化完成
        self.logger.info("MainWindow initialized successfully (refactored version)")

        # 🚀 延迟500ms后启动AI模型预加载（不阻塞UI）
        QTimer.singleShot(500, self._start_preload_ai_models)

    def _init_ui(self):
        """初始化用户界面 - 模块化组件组装"""
        # 创建中央部件和主布局
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)  # 遵循8dp栅格
        main_layout.setContentsMargins(16, 8, 16, 16)  # 优化top margin

        # 添加标题
        self._create_title_section(main_layout)

        # 创建主分割器 (水平布局: 左侧控制区 | 右侧预览区)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左侧区域容器 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 0, 0, 0)  # 左侧留8px与分割器对齐，确保对称
        left_layout.setSpacing(8)  # 统一间距为8dp

        # 1. 文件操作面板
        self.file_panel = FilePanel()
        left_layout.addWidget(self.file_panel)

        # 2. 控制面板 (占据所有剩余空间，让高级功能可以扩展)
        self.control_panel = ControlPanel()
        left_layout.addWidget(self.control_panel, 1)  # stretch=1，占据剩余空间

        # 3. 日志面板 (固定在底部，高度受限)
        self.log_panel = LogPanel(style_manager=self.style_manager)
        left_layout.addWidget(self.log_panel)

        # 添加弹簧，确保布局紧凑，日志在底部
        # left_layout.addStretch()

        # === 右侧区域容器 (预览面板) ===
        self.preview_panel = PreviewPanel()

        # 将预览面板放在左侧 (Index 0)
        main_splitter.addWidget(self.preview_panel)

        # 将控制面板放在右侧 (Index 1)
        main_splitter.addWidget(left_widget)

        # 保存分割器引用，用于动态调整比例
        self.main_splitter = main_splitter

        # 设置默认分割器比例 (73:27, 即 73% 预览, 27% 控制) - 普通窗口状态
        self._apply_splitter_ratio(is_maximized=False)

        main_layout.addWidget(main_splitter)

    def _create_title_section(self, main_layout):
        """创建标题区域（紧凑型顶部信息栏）"""
        header = QWidget()
        header.setObjectName("header_bar")
        header.setAutoFillBackground(True)  # 确保样式表背景色生效
        header.setFixedHeight(88)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        # 左侧图标
        icon_label = QLabel("🎬")
        icon_font = QFont()
        icon_font.setPointSize(18)
        icon_label.setFont(icon_font)
        header_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 中间标题与副标题
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)

        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)

        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_font.setBold(False)

        title_label = QLabel(f"{APP_NAME} - v{__version__}")
        title_label.setObjectName("title_primary")
        title_label.setFont(title_font)

        subtitle_label = QLabel("AI驱动的图像/视频水印检测与去除")
        subtitle_label.setObjectName("title_secondary")
        subtitle_label.setFont(subtitle_font)

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)

        header_layout.addWidget(title_container, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 右侧状态标签
        self.lbl_status = QLabel("⏳ AI模型准备中（后台加载）")
        self.lbl_status.setObjectName("status_badge")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setFixedHeight(28)
        self.lbl_status.setMinimumWidth(180)
        header_layout.addWidget(self.lbl_status, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(header)

    def _connect_signals(self):
        """连接组件信号 - 采用观察者模式，通过 SignalHandler 统一处理"""

        # 文件面板信号 -> SignalHandler
        self.file_panel.file_import_requested.connect(
            lambda: self.signal_handler.handle_import_file(self)
        )
        self.file_panel.file_export_requested.connect(
            lambda: self.signal_handler.handle_export_file(self)
        )
        self.file_panel.theme_toggle_requested.connect(
            lambda: self.signal_handler.handle_theme_toggle(self._apply_modern_style)
        )
        self.file_panel.auto_mode_changed.connect(self.signal_handler.handle_auto_mode_changed)
        self.file_panel.manual_mode_changed.connect(self.signal_handler.handle_manual_mode_changed)

        # 文件队列操作信号 -> SignalHandler
        self.file_panel.queue_clear_requested.connect(self.signal_handler.handle_queue_clear)
        self.file_panel.file_remove_requested.connect(self.signal_handler.handle_file_remove)
        self.file_panel.open_output_dir_requested.connect(
            self.signal_handler.handle_open_output_dir
        )
        self.file_panel.export_manifest_requested.connect(
            lambda: self.signal_handler.handle_export_batch_manifest(self)
        )

        # 预览面板信号 -> SignalHandler
        self.preview_panel.manual_selection_changed.connect(
            self.signal_handler.handle_manual_selection_changed
        )

        # 控制面板信号 -> SignalHandler
        self.control_panel.start_processing_requested.connect(
            self.signal_handler.handle_start_processing
        )
        self.control_panel.stop_processing_requested.connect(
            self.signal_handler.handle_stop_processing
        )

        # SignalHandler 内部信号 -> UI 组件
        self.signal_handler.status_updated.connect(self.lbl_status.setText)
        self.signal_handler.status_updated.connect(self.log_panel.add_status_message)

        # 进度信号连接
        self.progress_signal.connect(self.signal_handler.handle_progress_update)

    def _apply_modern_style(self):
        """应用现代化样式"""
        if hasattr(self.style_manager, "apply_style"):
            self.style_manager.apply_style(self)

        if hasattr(self, "log_panel") and hasattr(self.log_panel, "refresh_log_view"):
            self.log_panel.refresh_log_view()

        # 更新主题切换按钮文本
        current_theme = (
            self.style_manager.current_theme
            if hasattr(self.style_manager, "current_theme")
            else DEFAULT_THEME
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
                # 放宽最小尺寸限制，支持更多屏幕分辨率
                self.setMinimumSize(1400, 900)
                # 增大默认窗口尺寸，适合高分辨率显示器
                self.resize(1920, 1080)
        except Exception as e:
            self.logger.warning(f"Failed to restore window geometry: {e}")
            self.setMinimumSize(1400, 900)
            self.resize(1920, 1080)

    def _restore_ui_state(self):
        """恢复UI状态"""
        # 恢复处理模式
        auto_mode = self.preferences.get_preference("processing", "auto_mode", True)
        self.file_panel.auto_mode_checkbox.setChecked(auto_mode)
        self.file_panel.manual_mode_checkbox.setChecked(not auto_mode)

        # 恢复预览标签页
        tab_index = self.preferences.get_preference("ui", "preview_tab_index", 0)
        self.preview_panel.set_current_tab_index(tab_index)

    def _start_preload_ai_models(self):
        """启动AI模型预加载线程"""
        try:
            self.logger.info("开始预加载AI模型...")
            self.lbl_status.setText("🔄 正在后台加载AI模型...")

            advanced_params: dict[str, object] = {}
            if hasattr(self.control_panel, "get_advanced_parameters"):
                advanced_params = self.control_panel.get_advanced_parameters() or {}

            # 构建与默认 UI 参数一致的预加载快照，提升首任务命中率。
            from .utils.ai_params_builder import build_preload_runtime_snapshot  # noqa: WPS433

            preload_snapshot = build_preload_runtime_snapshot(
                preferences=self.preferences,
                advanced_params=advanced_params,
                config=self.config,
            )
            preload_ai_params = dict(preload_snapshot.get("ai_params") or {})
            self.last_preload_runtime_performance = dict(
                preload_snapshot.get("runtime_performance") or {}
            )
            if self.last_preload_runtime_performance:
                self.logger.info(
                    "预加载性能参数已解析: requested=%s resolved=%s",
                    self.last_preload_runtime_performance.get("requested_processing_mode"),
                    self.last_preload_runtime_performance.get("resolved_processing_mode"),
                )

            # 创建并启动预加载线程
            self.ai_preload_thread = AIModelPreloader(
                self.config,
                ai_params=preload_ai_params,
                runtime_performance=self.last_preload_runtime_performance,
                parent=self,
            )
            self.ai_preload_thread.finished.connect(self._on_ai_models_loaded)
            self.ai_preload_thread.error.connect(self._on_ai_models_load_error)
            self.ai_preload_thread.start()

        except Exception as e:
            self.logger.error(f"启动AI模型预加载失败: {e}")
            self.lbl_status.setText("⚠️ AI模型预加载失败，首次处理时将重新加载")

    def _on_ai_models_loaded(self, ai_handler):
        """AI模型加载完成回调"""
        self.ai_handler = ai_handler
        self.ai_models_ready = True
        self.lbl_status.setText("✅ AI模型已就绪，可以开始处理")
        self.logger.info("AI模型预加载完成，处理速度将得到优化")

    def _on_ai_models_load_error(self, error_msg):
        """AI模型加载失败回调"""
        self.ai_models_ready = False
        self.lbl_status.setText(f"⚠️ AI模型加载失败: {error_msg}，首次处理时将重新加载")
        self.logger.warning(f"AI模型预加载失败: {error_msg}")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            # 保存窗口几何信息
            self.preferences.set_preference("window", "geometry", self.saveGeometry())

            # 保存当前预览标签页
            current_tab = self.preview_panel.get_current_tab_index()
            self.preferences.set_preference("ui", "preview_tab_index", current_tab)

            # 清理信号处理器资源
            self.signal_handler.cleanup()

            self.logger.info("MainWindow closed successfully")
            event.accept()

        except Exception as e:
            self.logger.error(f"Error closing window: {e}")
            event.accept()

    def changeEvent(self, event):
        """
        监听窗口状态变化事件
        根据最大化/还原状态动态调整分割器比例
        """
        if event.type() == QEvent.Type.WindowStateChange:
            # 检查窗口是否最大化
            is_maximized = self.windowState() == Qt.WindowState.WindowMaximized
            # 延迟 50ms 执行，确保窗口尺寸已更新完成
            QTimer.singleShot(50, lambda: self._apply_splitter_ratio(is_maximized))
            self.logger.debug(f"Window state changed: maximized={is_maximized}")

        super().changeEvent(event)

    def _apply_splitter_ratio(self, is_maximized: bool) -> None:
        """
        根据窗口状态应用分割器比例

        使用 setSizes() 直接设置像素尺寸，而不是 setStretchFactor()
        因为 setStretchFactor() 只影响新增空间的分配，不会主动重新分配现有空间

        Args:
            is_maximized: 窗口是否最大化
                - True: 最大化状态，使用 8:2 比例（80% 预览, 20% 控制）
                - False: 普通状态，使用 73:27 比例（73% 预览, 27% 控制）
        """
        if not hasattr(self, "main_splitter") or self.main_splitter is None:
            return

        # 获取分割器的总宽度
        total_width = self.main_splitter.width()
        if total_width <= 0:
            return

        if is_maximized:
            # 最大化窗口：80% 预览, 20% 控制（大屏幕预览更重要）
            preview_width = int(total_width * 0.8)
            control_width = total_width - preview_width
            self.logger.debug(
                f"Applied maximized ratio 80:20: {preview_width}px + {control_width}px"
            )
        else:
            # 普通窗口：73% 预览, 27% 控制（小窗口控制面板需要更多空间）
            preview_width = int(total_width * 0.73)
            control_width = total_width - preview_width
            self.logger.debug(f"Applied normal ratio 73:27: {preview_width}px + {control_width}px")

        # 使用 setSizes() 直接设置像素尺寸
        self.main_splitter.setSizes([preview_width, control_width])
