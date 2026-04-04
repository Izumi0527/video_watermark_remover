#!/usr/bin/env python3
"""
详细进度显示组件

提供丰富的进度信息展示，包括:
1. 处理阶段指示器 (加载模型、处理帧、合并音频)
2. 帧计数器 (当前帧/总帧数)
3. 处理速度 (fps)
4. 时间信息 (已用时间、预计剩余时间)
5. 进度条 (根据阶段动态着色)

"""

from typing import Any, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ...config.advanced_params import (
    build_processing_mode_runtime_hint,
    build_processing_mode_runtime_summary,
)


class DetailedProgressWidget(QWidget):
    """
    详细进度显示组件

    显示完整的处理进度信息,包括阶段、帧数、速度和时间统计
    """

    # 阶段配置
    PHASE_CONFIG = {
        "idle": {
            "icon": "⏸️",
            "text": "空闲",
            "color": "#CCCCCC",
        },
        "loading_models": {
            "icon": "🔄",
            "text": "加载AI模型",
            "color": "#2196F3",  # 蓝色
        },
        "detecting_watermarks": {
            "icon": "🔍",
            "text": "检测水印",
            "color": "#FF9800",  # 橙色
        },
        "processing_frames": {
            "icon": "🎨",
            "text": "处理视频帧",
            "color": "#4CAF50",  # 绿色
        },
        "merging_audio": {
            "icon": "🎵",
            "text": "合并音频",
            "color": "#9C27B0",  # 紫色
        },
        "completed": {
            "icon": "✅",
            "text": "处理完成",
            "color": "#4CAF50",  # 绿色
        },
        "error": {
            "icon": "❌",
            "text": "处理失败",
            "color": "#F44336",  # 红色
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._reset_display()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建阶段指示器
        self._create_phase_indicator(layout)

        # 创建进度条
        self._create_progress_bar(layout)

        # 创建详细信息网格
        self._create_info_grid(layout)

    def _create_phase_indicator(self, main_layout):
        """创建阶段指示器"""
        phase_container = QFrame()
        phase_container.setObjectName("phase_container")
        phase_container.setFrameShape(QFrame.Shape.StyledPanel)

        phase_layout = QVBoxLayout(phase_container)
        phase_layout.setContentsMargins(10, 5, 10, 3)
        phase_layout.setSpacing(3)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # 阶段图标
        self.phase_icon_label = QLabel("⏸️")
        self.phase_icon_label.setObjectName("phase_icon")
        header_layout.addWidget(self.phase_icon_label)

        # 阶段文本
        self.phase_text_label = QLabel("空闲")
        self.phase_text_label.setObjectName("phase_text")
        header_layout.addWidget(self.phase_text_label)

        header_layout.addStretch()

        phase_layout.addLayout(header_layout)

        self.runtime_summary_label = QLabel("运行模式：--")
        self.runtime_summary_label.setObjectName("runtime_summary_text")
        self.runtime_summary_label.setWordWrap(True)
        phase_layout.addWidget(self.runtime_summary_label)

        self.runtime_hint_label = QLabel("")
        self.runtime_hint_label.setObjectName("runtime_hint_text")
        self.runtime_hint_label.setWordWrap(True)
        self.runtime_hint_label.hide()
        phase_layout.addWidget(self.runtime_hint_label)

        main_layout.addWidget(phase_container)

    def _create_progress_bar(self, main_layout):
        """创建进度条"""
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("detailed_progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

    def _create_info_grid(self, main_layout):
        """创建详细信息网格"""
        info_container = QFrame()
        info_container.setObjectName("info_container")
        info_container.setFrameShape(QFrame.Shape.StyledPanel)

        grid_layout = QGridLayout(info_container)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(10, 10, 10, 10)

        # 第一行: 帧计数器
        frames_label = QLabel("帧进度:")
        frames_label.setProperty("class", "info_label")
        grid_layout.addWidget(frames_label, 0, 0, alignment=Qt.AlignmentFlag.AlignRight)

        self.frames_value_label = QLabel("0 / 0")
        self.frames_value_label.setProperty("class", "info_value")
        grid_layout.addWidget(self.frames_value_label, 0, 1)

        # 第一行: 处理速度
        speed_label = QLabel("处理速度:")
        speed_label.setProperty("class", "info_label")
        grid_layout.addWidget(speed_label, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)

        self.speed_value_label = QLabel("0.0 fps")
        self.speed_value_label.setProperty("class", "info_value")
        grid_layout.addWidget(self.speed_value_label, 0, 3)

        # 第二行: 已用时间
        elapsed_label = QLabel("已用时间:")
        elapsed_label.setProperty("class", "info_label")
        grid_layout.addWidget(elapsed_label, 1, 0, alignment=Qt.AlignmentFlag.AlignRight)

        self.elapsed_value_label = QLabel("00:00")
        self.elapsed_value_label.setProperty("class", "info_value")
        grid_layout.addWidget(self.elapsed_value_label, 1, 1)

        # 第二行: 预计剩余
        eta_label = QLabel("预计剩余:")
        eta_label.setProperty("class", "info_label")
        grid_layout.addWidget(eta_label, 1, 2, alignment=Qt.AlignmentFlag.AlignRight)

        self.eta_value_label = QLabel("--:--")
        self.eta_value_label.setProperty("class", "info_value")
        grid_layout.addWidget(self.eta_value_label, 1, 3)

        main_layout.addWidget(info_container)

    def _reset_display(self):
        """重置显示"""
        self.update_progress(
            {
                "phase": "idle",
                "current_frame": 0,
                "total_frames": 0,
                "processing_speed": 0.0,
                "time_elapsed": 0.0,
                "eta": 0.0,
                "percentage": 0,
            }
        )

    def update_progress(self, progress_data: Dict[str, Any]):
        """
        更新进度显示

        Args:
            progress_data: 进度数据字典,包含:
                - phase: 当前阶段
                - current_frame: 当前帧
                - total_frames: 总帧数
                - processing_speed: 处理速度 (fps)
                - time_elapsed: 已用时间 (秒)
                - eta: 预计剩余时间 (秒)
                - percentage: 百分比进度
        """
        phase = progress_data.get("phase", "idle")
        current_frame = progress_data.get("current_frame", 0)
        total_frames = progress_data.get("total_frames", 0)
        processing_speed = progress_data.get("processing_speed", 0.0)
        time_elapsed = progress_data.get("time_elapsed", 0.0)
        eta = progress_data.get("eta", 0.0)
        percentage = progress_data.get("percentage", 0)
        restriction_reason = progress_data.get("mode_restriction_reason") or progress_data.get(
            "runtime_processing_guard_reason"
        )
        runtime_summary = progress_data.get(
            "runtime_mode_summary"
        ) or build_processing_mode_runtime_summary(
            requested_mode=progress_data.get("requested_processing_mode"),
            resolved_mode=progress_data.get("resolved_processing_mode"),
        )
        runtime_hint = progress_data.get("runtime_mode_hint") or build_processing_mode_runtime_hint(
            restriction_reason
        )

        # 更新阶段指示器
        phase_config = self.PHASE_CONFIG.get(phase, self.PHASE_CONFIG["idle"])
        self.phase_icon_label.setText(phase_config["icon"])
        self.phase_text_label.setText(phase_config["text"])
        self.runtime_summary_label.setText(runtime_summary)
        self.runtime_hint_label.setText(runtime_hint)
        self.runtime_hint_label.setVisible(bool(runtime_hint))

        # 更新进度条
        self.progress_bar.setValue(percentage)

        # 根据阶段更新进度条样式属性
        # Map phase to simpler property values if needed, or use phase name directly
        self.progress_bar.setProperty("phase", phase)
        # Force style update（风格对象可能为空，需判空）
        style = self.progress_bar.style()
        if style is not None:
            style.unpolish(self.progress_bar)
            style.polish(self.progress_bar)

        # 更新帧计数器
        if total_frames > 0:
            self.frames_value_label.setText(f"{current_frame:,} / {total_frames:,}")
        else:
            self.frames_value_label.setText("--")

        # 更新处理速度
        if processing_speed > 0:
            self.speed_value_label.setText(f"{processing_speed:.1f} fps")
        else:
            self.speed_value_label.setText("--")

        # 更新已用时间
        self.elapsed_value_label.setText(self._format_time(time_elapsed))

        # 更新预计剩余时间
        if eta > 0:
            self.eta_value_label.setText(self._format_time(eta))
        else:
            self.eta_value_label.setText("--:--")

    def _format_time(self, seconds: float) -> str:
        """
        格式化时间显示

        Args:
            seconds: 秒数

        Returns:
            格式化的时间字符串 (MM:SS 或 HH:MM:SS)
        """
        if seconds < 0:
            return "--:--"

        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def reset(self):
        """重置进度显示"""
        self._reset_display()

    def set_phase(self, phase: str):
        """
        设置当前阶段

        Args:
            phase: 阶段名称 (idle, loading_models, processing_frames, merging_audio, completed, error)
        """
        phase_config = self.PHASE_CONFIG.get(phase, self.PHASE_CONFIG["idle"])
        self.phase_icon_label.setText(phase_config["icon"])
        self.phase_text_label.setText(phase_config["text"])


# 示例用法
if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建测试窗口
    widget = DetailedProgressWidget()
    widget.setWindowTitle("详细进度显示组件测试")
    widget.resize(500, 200)
    widget.show()

    # 模拟进度更新
    from PyQt6.QtCore import QTimer

    test_data = [
        {
            "phase": "loading_models",
            "current_frame": 0,
            "total_frames": 0,
            "processing_speed": 0.0,
            "time_elapsed": 1.5,
            "eta": 0.0,
            "percentage": 0,
        },
        {
            "phase": "processing_frames",
            "current_frame": 245,
            "total_frames": 1000,
            "processing_speed": 15.2,
            "time_elapsed": 16.1,
            "eta": 49.7,
            "percentage": 25,
        },
        {
            "phase": "processing_frames",
            "current_frame": 500,
            "total_frames": 1000,
            "processing_speed": 14.8,
            "time_elapsed": 33.8,
            "eta": 33.8,
            "percentage": 50,
        },
        {
            "phase": "processing_frames",
            "current_frame": 750,
            "total_frames": 1000,
            "processing_speed": 15.5,
            "time_elapsed": 48.4,
            "eta": 16.1,
            "percentage": 75,
        },
        {
            "phase": "merging_audio",
            "current_frame": 1000,
            "total_frames": 1000,
            "processing_speed": 15.3,
            "time_elapsed": 65.4,
            "eta": 3.2,
            "percentage": 95,
        },
        {
            "phase": "completed",
            "current_frame": 1000,
            "total_frames": 1000,
            "processing_speed": 15.3,
            "time_elapsed": 68.6,
            "eta": 0.0,
            "percentage": 100,
        },
    ]

    current_index = [0]

    def update_test():
        if current_index[0] < len(test_data):
            widget.update_progress(test_data[current_index[0]])
            current_index[0] += 1
        else:
            # 重置测试
            current_index[0] = 0

    # 每2秒更新一次测试数据
    timer = QTimer()
    timer.timeout.connect(update_test)
    timer.start(2000)

    print("✅ 详细进度显示组件测试启动")
    print("每2秒自动更新一次进度数据")

    sys.exit(app.exec())
