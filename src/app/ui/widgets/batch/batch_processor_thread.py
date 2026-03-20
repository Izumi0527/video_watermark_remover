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
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

# 导入视频处理线程
from ....core.video.thread import VideoProcessorThread


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
    file_completed = pyqtSignal(int, str, object)  # 文件完成：索引，输出路径，处理状态
    batch_completed = pyqtSignal()  # 批量处理完成
    status_message = pyqtSignal(str)  # 状态消息

    def __init__(
        self,
        queue: Optional[List[Dict[str, Any]]] = None,
        ai_params: Optional[Dict[str, Any]] = None,
        config=None,
        preloaded_ai_handler=None,
        max_concurrent_files: int = 4,
        auto_retry_failed: bool = True,
        max_retry_count: int = 3,
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
            auto_retry_failed: 是否自动重试失败的文件（默认True）
            max_retry_count: 最大重试次数（默认3次）
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

        # 自动重试配置
        self.auto_retry_failed = auto_retry_failed
        self.max_retry_count = max_retry_count
        # 重试计数器：{file_index: retry_count}
        self._retry_counts: Dict[int, int] = {}

        # 线程安全的锁（用于更新共享状态）
        self._lock = Lock()
        self._completed_count = 0
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: Dict[Future, int] = {}
        self._active_processors: Dict[int, VideoProcessorThread] = {}

        if preloaded_ai_handler:
            self.logger.info("批量处理将使用预加载的AI模型，性能将得到优化")
        self.logger.info(f"批量处理并发数：{max_concurrent_files}")
        if auto_retry_failed:
            self.logger.info(f"自动重试已启用，最大重试次数：{max_retry_count}")

    def set_queue(self, file_queue):
        """设置文件队列"""
        self.file_queue = file_queue or []
        self.should_stop = False
        self._completed_count = 0
        self._retry_counts.clear()  # 重置重试计数器
        with self._lock:
            self._futures.clear()
            self._active_processors.clear()
        self._executor = None

    def _cancel_pending_futures(self) -> int:
        """尝试取消尚未执行的任务，返回取消数量。"""
        with self._lock:
            futures = list(self._futures.keys())

        cancelled_count = 0
        for future in futures:
            try:
                if future.cancel():
                    cancelled_count += 1
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"取消待执行任务失败: {e}")

        return cancelled_count

    def _stop_active_processors(self) -> None:
        """停止当前正在处理中的子任务（尽力而为）。"""
        with self._lock:
            processors = list(self._active_processors.values())

        for processor in processors:
            try:
                processor.stop()
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"停止子任务失败: {e}")

    def run(self):  # noqa: C901
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

        executor = ThreadPoolExecutor(max_workers=self.max_concurrent_files)
        self._executor = executor
        future_to_index: Dict[Future, int] = {}
        pending_futures: set[Future] = set()

        try:
            # 提交所有任务到线程池
            for index, file_info in enumerate(self.file_queue):
                if self.should_stop:
                    break

                input_path = file_info.get("input_path", "")
                output_path = file_info.get("output_path", "")

                if not input_path or not output_path:
                    self.logger.error(f"文件路径无效：{file_info}")
                    self.file_completed.emit(index, "", ProcessingStatus.FAILED)
                    with self._lock:
                        self._completed_count += 1
                        overall_progress = int((self._completed_count / total_files) * 100)
                    self.overall_progress.emit(overall_progress)
                    continue

                future: Future = executor.submit(
                    self._process_single_file_wrapper,
                    index,
                    input_path,
                    output_path,
                    total_files,
                )
                future_to_index[future] = index
                pending_futures.add(future)
                with self._lock:
                    self._futures[future] = index

            # 轮询收集处理结果（支持随时取消）
            while pending_futures:
                if self.should_stop:
                    self._cancel_pending_futures()
                    self._stop_active_processors()
                    break

                done, pending_futures = wait(
                    pending_futures,
                    timeout=0.2,
                    return_when=FIRST_COMPLETED,
                )

                for future in done:
                    with self._lock:
                        self._futures.pop(future, None)

                    file_index = future_to_index.get(future)
                    if file_index is None:
                        continue

                    try:
                        output_path, status = future.result()
                        self.file_completed.emit(file_index, output_path, status)
                    except Exception as e:  # noqa: BLE001
                        self.logger.error(f"处理文件 {file_index} 时发生异常: {e}")
                        self.file_completed.emit(file_index, "", ProcessingStatus.FAILED)

                    with self._lock:
                        self._completed_count += 1
                        overall_progress = int((self._completed_count / total_files) * 100)
                    self.overall_progress.emit(overall_progress)

        finally:
            self.is_running = False
            self._executor = None
            with self._lock:
                self._futures.clear()

            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=False)

            if self.should_stop:
                self.status_message.emit("[INFO] 批量处理已取消")
            else:
                self.status_message.emit(
                    f"[SUCCESS] 批量处理完成 ({self._completed_count}/{total_files})"
                )

            self.batch_completed.emit()

    def _process_single_file_wrapper(
        self, index: int, input_path: str, output_path: str, total_files: int
    ) -> tuple[str, ProcessingStatus]:
        """
        单文件处理包装器（用于线程池），支持递增延迟自动重试

        Args:
            index: 文件索引
            input_path: 输入文件路径
            output_path: 输出文件路径
            total_files: 总文件数

        Returns:
            (output_path, status) 元组
        """
        if self.should_stop:
            return ("", ProcessingStatus.CANCELLED)

        # 初始化重试计数
        if index not in self._retry_counts:
            self._retry_counts[index] = 0

        # 更新当前处理文件（线程安全）
        filename = os.path.basename(input_path)
        self.current_file_changed.emit(index, filename)

        retry_info = (
            f" (重试 {self._retry_counts[index]}/{self.max_retry_count})"
            if self._retry_counts[index] > 0
            else ""
        )
        self.status_message.emit(f"[INFO] 处理文件 {index + 1}/{total_files}: {filename}{retry_info}")

        # 调用实际处理方法
        status = self._process_single_file(input_path, output_path, index)

        # 自动重试逻辑（递增延迟策略：1秒、2秒、4秒...）
        if status == ProcessingStatus.FAILED and self.auto_retry_failed:
            while self._retry_counts[index] < self.max_retry_count and not self.should_stop:
                self._retry_counts[index] += 1
                # 递增延迟：2^(retry_count-1) 秒，即 1, 2, 4, 8...
                delay = 2 ** (self._retry_counts[index] - 1)
                self.status_message.emit(
                    f"[WARNING] 文件处理失败，{delay}秒后重试 "
                    f"({self._retry_counts[index]}/{self.max_retry_count}): {filename}"
                )

                # 递增延迟等待（可中断）
                remaining = float(delay)
                while remaining > 0 and not self.should_stop:
                    time.sleep(min(0.1, remaining))
                    remaining -= 0.1

                if self.should_stop:
                    break

                status = self._process_single_file(input_path, output_path, index)
                if status == ProcessingStatus.COMPLETED:
                    self.status_message.emit(f"[SUCCESS] 重试成功: {filename}")
                    break

        result_path = output_path if status == ProcessingStatus.COMPLETED else ""
        return (result_path, status)

    def _process_single_file(  # noqa: C901
        self, input_path: str, output_path: str, file_index: int
    ) -> ProcessingStatus:
        """
        处理单个文件（使用 VideoProcessorThread）

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            file_index: 文件索引

        Returns:
            ProcessingStatus: 单文件处理结果状态
        """
        try:
            if self.should_stop:
                return ProcessingStatus.CANCELLED

            # 检查输入文件是否存在
            if not os.path.exists(input_path):
                self.logger.error(f"输入文件不存在: {input_path}")
                return ProcessingStatus.FAILED

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
            def on_progress(progress: int) -> None:
                if self.should_stop:
                    return
                self.file_progress.emit(progress, file_index)

            processor.progress.connect(on_progress)

            # 创建事件循环标志
            processing_success = False
            processing_error = None

            def on_finished(result_path):
                nonlocal processing_success
                processing_success = bool(result_path)

            def on_error(error_msg):
                nonlocal processing_error
                processing_error = error_msg

            # 连接完成和错误信号
            processor.finished.connect(on_finished)
            processor.error.connect(on_error)

            with self._lock:
                self._active_processors[file_index] = processor

            try:
                # 同步运行处理（在当前线程中）
                if self.should_stop:
                    processor.stop()
                    return ProcessingStatus.CANCELLED
                processor.run()
            finally:
                with self._lock:
                    self._active_processors.pop(file_index, None)

            # 检查处理结果
            if processing_error:
                self.logger.error(f"文件处理失败: {input_path} - {processing_error}")
                return ProcessingStatus.FAILED

            if processing_success and os.path.exists(output_path):
                self.logger.info(f"文件处理完成: {input_path} -> {output_path}")
                return ProcessingStatus.COMPLETED

            if self.should_stop:
                self.logger.info(f"文件处理已取消: {input_path}")
                return ProcessingStatus.CANCELLED

            self.logger.warning(f"文件处理未生成输出: {input_path}")
            return ProcessingStatus.FAILED

        except Exception as e:
            self.logger.error(f"处理单个文件时发生异常: {e}", exc_info=True)
            if self.should_stop:
                return ProcessingStatus.CANCELLED
            return ProcessingStatus.FAILED

    def stop(self):
        """停止处理"""
        if self.should_stop:
            return
        self.should_stop = True
        cancelled_count = self._cancel_pending_futures()
        self._stop_active_processors()
        self.status_message.emit("[INFO] 正在停止批量处理...")
        if cancelled_count > 0:
            self.status_message.emit(f"[INFO] 已取消 {cancelled_count} 个待执行任务")


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

    def get_processing_count(self) -> int:
        """获取正在处理的文件数量"""
        return sum(1 for item in self.queue if item["status"] == ProcessingStatus.PROCESSING)
