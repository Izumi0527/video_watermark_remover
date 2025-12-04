import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# 导入图像选择器组件
from ..widgets.image_selector_widget import ImageSelectorWidget


class PreviewPanel(QWidget):
    """
    预览面板组件
    提供图像预览、对比和手动选择功能
    """

    # 信号定义
    manual_selection_changed = pyqtSignal(list)  # 手动选择区域变化

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._current_image = None
        self._processed_image = None
        self._init_ui()

    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建外层分组框 - 模拟截图样式
        self.preview_group = QGroupBox("预览区域")
        self.preview_group.setObjectName("preview_group")

        group_layout = QVBoxLayout(self.preview_group)
        group_layout.setContentsMargins(0, 0, 0, 0)  # 去除所有边距
        group_layout.setSpacing(0)

        # 创建标签页
        self.preview_tabs = QTabWidget()

        # 简单预览标签页
        self._create_simple_preview_tab()

        # 手动选择标签页
        self._create_manual_select_tab()

        # 效果对比标签页
        self._create_comparison_tab()

        group_layout.addWidget(self.preview_tabs)
        layout.addWidget(self.preview_group)

    def _create_simple_preview_tab(self):
        """创建简单预览标签页"""
        self.simple_preview_tab = QWidget()
        simple_layout = QVBoxLayout(self.simple_preview_tab)

        self.preview_area = QLabel("🖼️ 文件预览区域\n\n请选择图片或视频文件进行预览")
        self.preview_area.setObjectName("preview_placeholder")
        self.preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_area.setMinimumSize(640, 360)
        # 设置size policy让预览区域充分扩展
        self.preview_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 样式将由 style_manager 统一管理
        simple_layout.addWidget(self.preview_area, 1)  # 添加stretch factor

        self.preview_tabs.addTab(self.simple_preview_tab, "📷 简单预览")

    def _create_manual_select_tab(self):
        """创建手动选择标签页"""
        self.manual_select_tab = QWidget()
        manual_layout = QVBoxLayout(self.manual_select_tab)
        manual_layout.setContentsMargins(0, 0, 0, 0)  # 移除容器边距，确保内容充满

        # 使用真正的ImageSelectorWidget替换占位符
        self.image_selector = ImageSelectorWidget()
        self.image_selector.selection_changed.connect(self._on_manual_selection_changed)
        manual_layout.addWidget(self.image_selector, 1)  # 添加伸缩因子，让内容充满容器

        self.preview_tabs.addTab(self.manual_select_tab, "✏️ 手动选择")

    def _create_comparison_tab(self):
        """创建效果对比标签页"""
        self.comparison_tab = QWidget()
        comparison_layout = QVBoxLayout(self.comparison_tab)
        comparison_layout.setContentsMargins(0, 0, 0, 0)  # 移除容器边距，确保内容充满

        # 添加对比信息显示区域
        self.comparison_info_label = QLabel("📊 对比信息：请先处理文件")
        self.comparison_info_label.setObjectName("comparison_info")
        self.comparison_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comparison_info_label.setMinimumHeight(28)  # 设置最小高度防止被压缩
        comparison_layout.addWidget(self.comparison_info_label)

        # 创建分割器用于左右对比
        self.comparison_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.comparison_splitter.setMinimumHeight(340)  # 设置分割器最小高度，确保边框闭合

        # 原图区域
        original_frame = self._create_image_frame("📷 原图")
        self.original_image_label = original_frame.findChild(QLabel, "image_label")

        # 处理后区域
        processed_frame = self._create_image_frame("✨ 处理后")
        self.processed_image_label = processed_frame.findChild(QLabel, "image_label")

        self.comparison_splitter.addWidget(original_frame)
        self.comparison_splitter.addWidget(processed_frame)

        # 设置分割器比例
        self.comparison_splitter.setStretchFactor(0, 1)
        self.comparison_splitter.setStretchFactor(1, 1)

        comparison_layout.addWidget(self.comparison_splitter, 1)  # 添加伸缩因子，让内容充满容器

        self.preview_tabs.addTab(self.comparison_tab, "⚖️ 效果对比")

    def _create_image_frame(self, title):
        """创建图像框架"""
        frame = QFrame()
        frame.setObjectName("preview_container")
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setMinimumHeight(400)  # 增加最小高度
        # 设置frame的size policy
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)  # 遵循8dp栅格
        layout.setSpacing(8)  # 遵循8dp栅格

        # 标题
        title_label = QLabel(title)
        title_label.setObjectName("preview_title")  # Add object name for styling
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 图像显示区域
        image_label = QLabel("暂无文件")
        image_label.setObjectName("image_label")  # 设置对象名以便查找
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setMinimumSize(450, 320)
        # 设置image_label的size policy
        image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 样式将由 style_manager 统一管理
        layout.addWidget(image_label, 1)  # 添加伸缩因子，让图像充满剩余空间

        return frame

    def set_image(self, image_path):
        """设置预览图像"""
        try:
            # 清除之前的内联样式，让全局样式生效
            self.preview_area.setStyleSheet("")

            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 缩放图像以适应预览区域
                scaled_pixmap = pixmap.scaled(
                    640,
                    360,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview_area.setPixmap(scaled_pixmap)
                self.preview_area.setText("")  # 清空文本

                # 同时更新对比区域的原图
                original_scaled = pixmap.scaled(
                    450,
                    320,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.original_image_label.setPixmap(original_scaled)
                self.original_image_label.setText("")

                self._current_image = image_path
                self.logger.info(f"Image preview updated: {image_path}")
            else:
                self.logger.error(f"Failed to load image: {image_path}")
        except Exception as e:
            self.logger.error(f"Error setting preview image: {e}")

    def set_image_from_array(self, image_array):
        """从 numpy 数组设置预览图像（用于视频第一帧）"""
        try:
            import numpy as np
            from PyQt6.QtGui import QImage

            # 清除之前的内联样式，让全局样式生效
            self.preview_area.setStyleSheet("")

            # 确保是 uint8 类型的 RGB 数组
            if image_array.dtype != np.uint8:
                image_array = (image_array * 255).astype(np.uint8)

            h, w, c = image_array.shape
            bytes_per_line = 3 * w
            q_image = QImage(image_array.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)

            if not pixmap.isNull():
                # 缩放图像以适应预览区域
                scaled_pixmap = pixmap.scaled(
                    640,
                    360,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview_area.setPixmap(scaled_pixmap)
                self.preview_area.setText("")

                # 同时更新对比区域的原图
                original_scaled = pixmap.scaled(
                    450,
                    320,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.original_image_label.setPixmap(original_scaled)
                self.original_image_label.setText("")

                self.logger.info("Video first frame preview set")
            else:
                self.logger.error("Failed to create pixmap from array")
        except Exception as e:
            self.logger.error(f"Error setting image from array: {e}")

    def show_video_placeholder(self, video_path):
        """显示视频文件占位符信息"""
        try:
            import cv2

            cap = cv2.VideoCapture(video_path)  # type: ignore[call-arg]

            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()

                placeholder_text = (
                    f"🎬 视频文件\n\n"
                    f"分辨率: {width}x{height}\n"
                    f"帧率: {fps:.2f} fps\n"
                    f"总帧数: {frame_count}\n"
                    f"时长: {duration:.2f} 秒"
                )
            else:
                placeholder_text = "🎬 视频文件\n\n无法读取视频信息"

            self.preview_area.clear()
            self.preview_area.setText(placeholder_text)
            self.preview_area.setStyleSheet(
                """
                QLabel {
                    border: 2px solid #000000;
                    border-radius: 12px;
                    background-color: #1a1a1a;
                    color: #007acc;
                    font-size: 11pt;
                }
            """
            )
            self.logger.info(f"Video placeholder shown for: {video_path}")
        except Exception as e:
            self.logger.error(f"Error showing video placeholder: {e}")

    def set_processed_image(self, processed_pixmap, processing_info=None):
        """设置处理后的图像"""
        if processed_pixmap and not processed_pixmap.isNull():
            # 更新对比区域的处理后图像
            scaled_pixmap = processed_pixmap.scaled(
                450,
                320,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.processed_image_label.setPixmap(scaled_pixmap)
            self.processed_image_label.setText("")
            self._processed_image = processed_pixmap

            # 更新对比信息显示
            self._update_comparison_info(processing_info)

            # 自动切换到对比标签页
            self.preview_tabs.setCurrentWidget(self.comparison_tab)
            self.logger.info("Processed image preview updated")

    def clear_preview(self):
        """清空预览"""
        self.preview_area.clear()
        self.preview_area.setText("🖼️ 文件预览区域\n\n请选择图片或视频文件进行预览")

        self.original_image_label.clear()
        self.original_image_label.setText("暂无文件")

        self.processed_image_label.clear()
        self.processed_image_label.setText("暂无文件")

        # 重置对比信息显示
        self.reset_comparison_display()

        self._current_image = None
        self._processed_image = None

    def get_current_tab_index(self):
        """获取当前标签页索引"""
        return self.preview_tabs.currentIndex()

    def set_current_tab_index(self, index):
        """设置当前标签页"""
        if 0 <= index < self.preview_tabs.count():
            self.preview_tabs.setCurrentIndex(index)

    # 手动选择功能相关方法
    def _on_manual_selection_changed(self, selections):
        """处理手动选择区域变化"""
        self.logger.debug(f"Manual selection changed: {len(selections)} regions")
        # 发射信号给主窗口
        self.manual_selection_changed.emit(selections)

    def set_manual_selection_image(self, image_path):
        """为手动选择设置图像"""
        try:
            success = self.image_selector.setImage(image_path)
            if success:
                self.logger.info(f"Manual selection image set: {image_path}")
            else:
                self.logger.warning(f"Failed to set manual selection image: {image_path}")
            return success
        except Exception as e:
            self.logger.error(f"Error setting manual selection image: {e}")
            return False

    def set_manual_selection_image_from_array(self, image_array):
        """从数组为手动选择设置图像"""
        try:
            success = self.image_selector.setImageFromArray(image_array)
            if success:
                self.logger.info("Manual selection image set from array")
            else:
                self.logger.warning("Failed to set manual selection image from array")
            return success
        except Exception as e:
            self.logger.error(f"Error setting manual selection image from array: {e}")
            return False

    def get_manual_selections(self):
        """获取手动选择的区域"""
        try:
            selections = self.image_selector.getSelections()
            self.logger.debug(f"Retrieved {len(selections)} manual selections")
            return selections
        except Exception as e:
            self.logger.error(f"Error getting manual selections: {e}")
            return []

    def clear_manual_selections(self):
        """清空手动选择"""
        try:
            self.image_selector.clearSelections()
            self.logger.info("Manual selections cleared")
        except Exception as e:
            self.logger.error(f"Error clearing manual selections: {e}")

    def switch_to_manual_tab(self):
        """切换到手动选择标签页"""
        self.preview_tabs.setCurrentWidget(self.manual_select_tab)
        self.logger.debug("Switched to manual selection tab")

    # 预览对比功能增强方法
    def _update_comparison_info(self, processing_info=None):
        """更新对比信息显示"""
        if processing_info:
            # 从处理信息中提取统计数据
            method = processing_info.get("detection_method", "未知")
            regions_count = processing_info.get("manual_regions_count", 0) or processing_info.get(
                "auto_regions_count", 0
            )
            process_time = processing_info.get("processing_time", 0)

            # 格式化显示信息
            info_text = f"📊 处理完成 | 方法: {method}"
            if regions_count > 0:
                info_text += f" | 处理区域: {regions_count}个"
            if process_time > 0:
                info_text += f" | 耗时: {process_time:.2f}秒"

            self.comparison_info_label.setText(info_text)
            self.comparison_info_label.setStyleSheet(
                """
                QLabel {
                    background-color: #e8f5e8;
                    border: 1px solid #4CAF50;
                    border-radius: 5px;
                    padding: 3px 6px;
                    color: #4CAF50;
                    font-weight: 600;
                    font-size: 8pt;
                }
            """
            )
        else:
            # 基本的完成信息
            self.comparison_info_label.setText("✅ 文件处理完成 - 对比效果如下")
            self.comparison_info_label.setStyleSheet(
                """
                QLabel {
                    background-color: #e8f5e8;
                    border: 1px solid #4CAF50;
                    border-radius: 5px;
                    padding: 3px 6px;
                    color: #4CAF50;
                    font-weight: 600;
                    font-size: 8pt;
                }
            """
            )

    def show_processing_progress(self):
        """显示处理中的进度状态"""
        self.comparison_info_label.setText("⏳ 正在处理图像，请稍候...")
        self.comparison_info_label.setStyleSheet(
            """
            QLabel {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 5px;
                padding: 3px 6px;
                color: #856404;
                font-weight: 600;
                font-size: 8pt;
            }
        """
        )

    def reset_comparison_display(self):
        """重置对比显示状态"""
        self.comparison_info_label.setText("📊 对比信息：请先处理文件")
        self.comparison_info_label.setStyleSheet(
            """
            QLabel {
                background-color: #f0f8ff;
                border: 1px solid #007acc;
                border-radius: 5px;
                padding: 3px 6px;
                color: #007acc;
                font-weight: 600;
                font-size: 8pt;
            }
        """
        )

        # 清空处理后图像
        self.processed_image_label.clear()
        self.processed_image_label.setText("暂无文件")
        self._processed_image = None

    def switch_to_comparison_tab(self):
        """切换到对比标签页"""
        self.preview_tabs.setCurrentWidget(self.comparison_tab)
        self.logger.debug("Switched to comparison tab")
