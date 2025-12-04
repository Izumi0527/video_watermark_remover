#!/usr/bin/env python3
# mypy: disable-error-code=unreachable
"""
批量处理线程组件

包含批量处理的线程逻辑和状态管理：
1. 处理状态枚举
2. 批量处理线程类（支持并发处理）
3. 文件处理队列管理

"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

# 导入视频处理线程
from ....core.video.video_processor import VideoProcessorThread


class ProcessingStatus(Enum):
    """处理状态枚举"""

    WAITING = "waiting"  # 等待处理
    PROCESSING = "processing"  # 正在处理
    COMPLETED = "completed"  # 处理完成
    FAILED = "failed"  # 处理失败
    CANCELLED = "cancelled"  # 已取消


class BatchProcessorThread(QThread):
    """
    批量处理线程（支持并发处理）

    使用 ThreadPoolExecutor 实现多文件并发处理，大幅提升批量处理速度。
    支持复用预加载的 AI 模型，避免重复加载。
    """

    # 信号定义
    current_file_changed = pyqtSignal(int, str)  # 当前处理文件索引和名称
    file_progress = pyqtSignal(int, int)  # 当前文件进度百分比和文件索引
    overall_progress = pyqtSignal(int)  # 总体进度百分比
    file_completed = pyqtSignal(int, str, bool)  # 文件完成：索引，输出路径，是否成功
    batch_completed = pyqtSignal()  # 批量处理完成
    status_message = pyqtSignal(str)  # 状态消息

    def __init__(
        self,
        queue: Optional[List[Dict[str, Any]]] = None,
        ai_params: Optional[Dict[str, Any]] = None,
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files: int = 4,
        parent=None,
    ):
        """
        初始化批量处理线程

        Args:
            file_queue: 文件队列（包含 input_path 和 output_path 的字典列表）
            ai_params: AI 处理参数
            config: 配置对象
            preloaded_ai_handler: 预加载的 AI 处理器（可选）
            max_concurrent_files: 最大并发文件数（默认4个）
            parent: 父对象
        """
        super().__init__(parent)
        self.file_queue: List[Dict[str, Any]] = queue or []
        self.ai_params: Dict[str, Any] = ai_params or {}
        self.config = config
        self.preloaded_ai_handler = preloaded_ai_handler
        self.max_concurrent_files = max_concurrent_files
        self.is_running = False
        self.should_stop = False
        self.logger = logging.getLogger(__name__)

        # 线程安全的锁（用于更新共享状态）
        self._lock = Lock()
        self._completed_count = 0

        if preloaded_ai_handler:
            self.logger.info("批量处理将使用预加载的AI模型，性能将得到优化")
        self.logger.info(f"批量处理并发数：{max_concurrent_files}")

    def set_queue(self, file_queue):
        """设置文件队列"""
        self.file_queue = file_queue or []
        self.should_stop = False
        self._completed_count = 0

    def run(self):
        """
        运行批量处理（并发版本）

        使用 ThreadPoolExecutor 实现多文件并发处理，大幅提升处理速度。
        """
        if not self.file_queue:
            self.status_message.emit("[WARNING] 处理队列为空")
            self.batch_completed.emit()
            return

        self.is_running = True
        total_files = len(self.file_queue)
        self._completed_count = 0

        self.status_message.emit(
            f"[INFO] 开始并发批量处理 {total_files} 个文件 " f"(并发数: {self.max_concurrent_files})"
        )

        # 使用 ThreadPoolExecutor 实现并发处理
        with ThreadPoolExecutor(max_workers=self.max_concurrent_files) as executor:
            # 提交所有任务到线程池
            future_to_index = {}
            for index, file_info in enumerate(self.file_queue):
                if self.should_stop:
                    break

                input_path = file_info.get("input_path", "")
                output_path = file_info.get("output_path", "")

                if not input_path or not output_path:
                    self.logger.error(f"文件路径无效：{file_info}")
                    continue

                # 提交任务到线程池
                future = executor.submit(
                    self._process_single_file_wrapper,
                    index,
                    input_path,
                    output_path,
                    total_files,
                )
                future_to_index[future] = index

            # 收集处理结果
            for future in as_completed(future_to_index):
                if self.should_stop:
                    self.status_message.emit("[INFO] 批量处理已取消")
                    break

                index = future_to_index[future]
                try:
                    output_path, success = future.result()

                    # 发送文件完成信号
                    self.file_completed.emit(index, output_path if success else "", success)

                    # 线程安全地更新完成计数和总体进度
                    with self._lock:
                        self._completed_count += 1
                        overall_progress = int((self._completed_count / total_files) * 100)
                        self.overall_progress.emit(overall_progress)

                except Exception as e:
                    self.logger.error(f"处理文件 {index} 时发生异常: {e}")
                    self.file_completed.emit(index, "", False)

        self.is_running = False

        if not self.should_stop:
            self.status_message.emit(f"[SUCCESS] 批量处理完成 ({self._completed_count}/{total_files})")

        self.batch_completed.emit()

    def _process_single_file_wrapper(
        self, index: int, input_path: str, output_path: str, total_files: int
    ) -> tuple[str, bool]:
        """
        单文件处理包装器（用于线程池）

        Args:
            index: 文件索引
            input_path: 输入文件路径
            output_path: 输出文件路径
            total_files: 总文件数

        Returns:
            (output_path, success) 元组
        """
        # 更新当前处理文件（线程安全）
        filename = os.path.basename(input_path)
        self.current_file_changed.emit(index, filename)
        self.status_message.emit(f"[INFO] 处理文件 {index + 1}/{total_files}: {filename}")

        # 调用实际处理方法
        success = self._process_single_file(input_path, output_path, index)

        return (output_path, success)

    def _process_single_file(self, input_path: str, output_path: str, file_index: int) -> bool:
        """
        处理单个文件（使用 VideoProcessorThread）

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            file_index: 文件索引

        Returns:
            bool: 处理是否成功
        """
        try:
            # 检查输入文件是否存在
            if not os.path.exists(input_path):
                self.logger.error(f"输入文件不存在: {input_path}")
                return False

            # 创建输出目录
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 创建 VideoProcessorThread 进行实际处理
            processor = VideoProcessorThread(
                input_path=input_path,
                output_path=output_path,
                ai_params=self.ai_params,
                config=self.config,
                preloaded_ai_handler=self.preloaded_ai_handler,  # 复用预加载的AI模型
            )

            # 连接进度信号
            processor.progress.connect(
                lambda progress: self.file_progress.emit(progress, file_index)
            )

            # 创建事件循环标志
            processing_completed = False
            processing_success = False
            processing_error = None

            def on_finished(result_path):
                nonlocal processing_completed, processing_success
                processing_completed = True
                processing_success = bool(result_path)

            def on_error(error_msg):
                nonlocal processing_completed, processing_error
                processing_completed = True
                processing_error = error_msg

            # 连接完成和错误信号
            processor.finished.connect(on_finished)
            processor.error.connect(on_error)

            # 同步运行处理（在当前线程中）
            processor.run()

            # 检查处理结果
            if processing_error:
                self.logger.error(f"文件处理失败: {input_path} - {processing_error}")
                return False

            if processing_success and os.path.exists(output_path):
                self.logger.info(f"文件处理完成: {input_path} -> {output_path}")
                return True
            else:
                self.logger.warning(f"文件处理未生成输出: {input_path}")
                return False

        except Exception as e:
            self.logger.error(f"处理单个文件时发生异常: {e}", exc_info=True)
            return False

    def stop(self):
        """停止处理"""
        self.should_stop = True
        self.status_message.emit("[INFO] 正在停止批量处理...")


class FileQueueManager:
    """文件队列管理器"""

    def __init__(self):
        self.queue: List[Dict[str, Any]] = []

    def add_file(self, input_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """添加文件到队列"""
        if not output_path:
            # 自动生成输出路径
            name, ext = os.path.splitext(input_path)
            output_path = f"{name}_processed{ext}"

        file_info = {
            "input_path": input_path,
            "output_path": output_path,
            "status": ProcessingStatus.WAITING,
            "progress": 0,
            "error_message": "",
        }

        self.queue.append(file_info)
        return file_info

    def remove_file(self, index: int) -> bool:
        """从队列中移除文件"""
        if 0 <= index < len(self.queue):
            self.queue.pop(index)
            return True
        return False

    def clear_queue(self):
        """清空队列"""
        self.queue.clear()

    def get_queue(self) -> List[Dict[str, Any]]:
        """获取队列"""
        return self.queue.copy()

    def update_file_status(
        self, index: int, status: ProcessingStatus, progress: int = 0, error_message: str = ""
    ):
        """更新文件状态"""
        if 0 <= index < len(self.queue):
            self.queue[index]["status"] = status
            self.queue[index]["progress"] = progress
            self.queue[index]["error_message"] = error_message

    def get_file_info(self, index: int) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        if index < 0 or index >= len(self.queue):
            return None
        return self.queue[index].copy()
        return {}

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return len(self.queue)

    def get_pending_count(self) -> int:
        """获取等待处理的文件数量"""
        return sum(1 for item in self.queue if item["status"] == ProcessingStatus.WAITING)

    def get_completed_count(self) -> int:
        """获取已完成的文件数量"""
        return sum(1 for item in self.queue if item["status"] == ProcessingStatus.COMPLETED)

    def get_failed_count(self) -> int:
        """获取失败的文件数量"""
        return sum(1 for item in self.queue if item["status"] == ProcessingStatus.FAILED)
