import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QGroupBox, QLabel, QSplitter, QTabWidget, QVBoxLayout, QWidget

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

        # 创建预览区域组
        preview_group = QGroupBox("预览区域")
        preview_layout = QVBoxLayout(preview_group)

        # 创建标签页
        self.preview_tabs = QTabWidget()

        # 简单预览标签页
        self._create_simple_preview_tab()

        # 手动选择标签页
        self._create_manual_select_tab()

        # 效果对比标签页
        self._create_comparison_tab()

        preview_layout.addWidget(self.preview_tabs)
        layout.addWidget(preview_group)

    def _create_simple_preview_tab(self):
        """创建简单预览标签页"""
        self.simple_preview_tab = QWidget()
        simple_layout = QVBoxLayout(self.simple_preview_tab)

        self.preview_area = QLabel("🖼️ 图片预览区域\n\n请选择图片文件进行预览")
        self.preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_area.setMinimumSize(640, 360)
        self.preview_area.setStyleSheet(
            """
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
                color: #888;
                font-size: 14px;
            }
        """
        )
        simple_layout.addWidget(self.preview_area)

        self.preview_tabs.addTab(self.simple_preview_tab, "📷 简单预览")

    def _create_manual_select_tab(self):
        """创建手动选择标签页"""
        self.manual_select_tab = QWidget()
        manual_layout = QVBoxLayout(self.manual_select_tab)

        # 使用真正的ImageSelectorWidget替换占位符
        self.image_selector = ImageSelectorWidget()
        self.image_selector.selection_changed.connect(self._on_manual_selection_changed)
        manual_layout.addWidget(self.image_selector)

        self.preview_tabs.addTab(self.manual_select_tab, "✏️ 手动选择")

    def _create_comparison_tab(self):
        """创建效果对比标签页"""
        self.comparison_tab = QWidget()
        comparison_layout = QVBoxLayout(self.comparison_tab)

        # 添加对比信息显示区域
        self.comparison_info_label = QLabel("📊 对比信息：请先处理图像")
        self.comparison_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comparison_info_label.setStyleSheet(
            """
            QLabel {
                background-color: #f0f8ff;
                border: 1px solid #007acc;
                border-radius: 5px;
                padding: 10px;
                color: #007acc;
                font-weight: bold;
            }
        """
        )
        comparison_layout.addWidget(self.comparison_info_label)

        # 创建分割器用于左右对比
        self.comparison_splitter = QSplitter(Qt.Orientation.Horizontal)

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

        comparison_layout.addWidget(self.comparison_splitter)

        self.preview_tabs.addTab(self.comparison_tab, "⚖️ 效果对比")

    def _create_image_frame(self, title):
        """创建图像框架"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)

        # 标题
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 图像显示区域
        image_label = QLabel("暂无图片")
        image_label.setObjectName("image_label")  # 设置对象名以便查找
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setMinimumSize(300, 200)
        image_label.setStyleSheet(
            """
            QLabel {
                border: 1px solid #ccc;
                background-color: #f9f9f9;
                color: #888;
            }
        """
        )
        layout.addWidget(image_label)

        return frame

    def set_image(self, image_path):
        """设置预览图像"""
        try:
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
                    300,
                    200,
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

    def set_processed_image(self, processed_pixmap, processing_info=None):
        """设置处理后的图像"""
        if processed_pixmap and not processed_pixmap.isNull():
            # 更新对比区域的处理后图像
            scaled_pixmap = processed_pixmap.scaled(
                300,
                200,
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
        self.preview_area.setText("🖼️ 图片预览区域\n\n请选择图片文件进行预览")

        self.original_image_label.clear()
        self.original_image_label.setText("暂无图片")

        self.processed_image_label.clear()
        self.processed_image_label.setText("暂无图片")

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
                    padding: 10px;
                    color: #4CAF50;
                    font-weight: bold;
                }
            """
            )
        else:
            # 基本的完成信息
            self.comparison_info_label.setText("✅ 图像处理完成 - 对比效果如下")
            self.comparison_info_label.setStyleSheet(
                """
                QLabel {
                    background-color: #e8f5e8;
                    border: 1px solid #4CAF50;
                    border-radius: 5px;
                    padding: 10px;
                    color: #4CAF50;
                    font-weight: bold;
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
                padding: 10px;
                color: #856404;
                font-weight: bold;
            }
        """
        )

    def reset_comparison_display(self):
        """重置对比显示状态"""
        self.comparison_info_label.setText("📊 对比信息：请先处理图像")
        self.comparison_info_label.setStyleSheet(
            """
            QLabel {
                background-color: #f0f8ff;
                border: 1px solid #007acc;
                border-radius: 5px;
                padding: 10px;
                color: #007acc;
                font-weight: bold;
            }
        """
        )

        # 清空处理后图像
        self.processed_image_label.clear()
        self.processed_image_label.setText("暂无图片")
        self._processed_image = None

    def switch_to_comparison_tab(self):
        """切换到对比标签页"""
        self.preview_tabs.setCurrentWidget(self.comparison_tab)
        self.logger.debug("Switched to comparison tab")
