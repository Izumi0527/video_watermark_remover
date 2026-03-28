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
import uuid
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from ....config.advanced_params import ResolvedPerformanceConfig

# 导入视频处理线程
from ....core.video.output_strategy import resolve_output_path
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
    file_completed = pyqtSignal(int, str, object, str, object)  # 文件完成：索引，输出路径，处理状态，错误信息，处理详情
    batch_completed = pyqtSignal()  # 批量处理完成
    status_message = pyqtSignal(str)  # 状态消息

    def __init__(
        self,
        queue: Optional[List[Dict[str, Any]]] = None,
        ai_params: Optional[Dict[str, Any]] = None,
        file_ai_params_by_index: Optional[Dict[int, Dict[str, Any]]] = None,
        file_ai_params_by_file_id: Optional[Dict[str, Dict[str, Any]]] = None,
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
        self.file_ai_params_by_index: Dict[int, Dict[str, Any]] = {
            int(index): dict(params or {})
            for index, params in (file_ai_params_by_index or {}).items()
        }
        self.file_ai_params_by_file_id: Dict[str, Dict[str, Any]] = {
            str(file_id): dict(params or {})
            for file_id, params in (file_ai_params_by_file_id or {}).items()
            if file_id is not None
        }
        self.config = config
        self.max_concurrent_files = max_concurrent_files
        self.is_running = False
        self.should_stop = False
        self.logger = logging.getLogger(__name__)

        # 预加载 AIHandler 复用策略：
        # - 并发 > 1 时禁止复用同一实例，避免跨线程状态污染与竞态问题
        # - 并发 = 1 时允许复用，加速连续任务
        self._reuse_preloaded_ai_handler = bool(
            preloaded_ai_handler and self.max_concurrent_files <= 1
        )
        self.preloaded_ai_handler = (
            preloaded_ai_handler if self._reuse_preloaded_ai_handler else None
        )
        if preloaded_ai_handler and not self._reuse_preloaded_ai_handler:
            self.logger.warning("批处理并发数大于 1，为避免线程安全问题，已禁用预加载 AI 模型复用")

        # 自动重试配置
        self.auto_retry_failed = auto_retry_failed
        self.max_retry_count = max_retry_count
        # 重试计数器：{file_id: retry_count}
        self._retry_counts: Dict[str, int] = {}

        # 线程安全的锁（用于更新共享状态）
        self._lock = Lock()
        self._completed_count = 0
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: Dict[Future, int] = {}
        self._future_file_ids: Dict[Future, str] = {}
        self._active_processors: Dict[str, VideoProcessorThread] = {}
        self._started_file_ids: set[str] = set()
        self._removed_file_ids: set[str] = set()

        if self.preloaded_ai_handler:
            self.logger.info("批量处理将使用预加载的AI模型，性能将得到优化")
        self.logger.info(f"批量处理并发数：{max_concurrent_files}")
        if auto_retry_failed:
            self.logger.info(f"自动重试已启用，最大重试次数：{max_retry_count}")

    def set_queue(self, file_queue):
        """设置文件队列"""
        self.file_queue = file_queue or []
        for file_info in self.file_queue:
            self._ensure_queue_file_id(file_info)
        self.should_stop = False
        self._completed_count = 0
        self._retry_counts.clear()  # 重置重试计数器
        with self._lock:
            self._futures.clear()
            self._future_file_ids.clear()
            self._active_processors.clear()
            self._started_file_ids.clear()
            self._removed_file_ids.clear()
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
        future_to_file_id: Dict[Future, str] = {}
        pending_futures: set[Future] = set()

        try:
            # 提交所有任务到线程池
            for index, file_info in enumerate(self.file_queue):
                if self.should_stop:
                    break

                file_id = self._ensure_queue_file_id(file_info)
                input_path = file_info.get("input_path", "")
                output_path = file_info.get("output_path", "")

                if not input_path or not output_path:
                    self.logger.error(f"文件路径无效：{file_info}")
                    self.file_completed.emit(
                        index,
                        "",
                        ProcessingStatus.FAILED,
                        "文件路径无效",
                        None,
                    )
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
                future_to_file_id[future] = file_id
                pending_futures.add(future)
                with self._lock:
                    self._futures[future] = index
                    self._future_file_ids[future] = file_id

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
                        file_id = self._future_file_ids.pop(future, "")

                    file_index = future_to_index.get(future)
                    if file_index is None:
                        continue

                    if future.cancelled():
                        self.file_completed.emit(
                            file_index,
                            "",
                            ProcessingStatus.CANCELLED,
                            "已从队列移除",
                            None,
                        )
                        with self._lock:
                            self._completed_count += 1
                            overall_progress = int((self._completed_count / total_files) * 100)
                        self.overall_progress.emit(overall_progress)
                        continue

                    try:
                        output_path, status, error_message, processing_details = future.result()
                        self.file_completed.emit(
                            file_index,
                            output_path,
                            status,
                            error_message or "",
                            processing_details,
                        )
                    except Exception as e:  # noqa: BLE001
                        self.logger.error(f"处理文件 {file_index} 时发生异常: {e}")
                        self.file_completed.emit(
                            file_index,
                            "",
                            ProcessingStatus.FAILED,
                            str(e),
                            None,
                        )

                    with self._lock:
                        self._completed_count += 1
                        overall_progress = int((self._completed_count / total_files) * 100)
                    self.overall_progress.emit(overall_progress)

        finally:
            self.is_running = False
            self._executor = None
            with self._lock:
                self._futures.clear()
                self._future_file_ids.clear()
                self._started_file_ids.clear()

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

    def _process_single_file_wrapper(  # noqa: C901
        self, index: int, input_path: str, output_path: str, total_files: int
    ) -> tuple[str, ProcessingStatus, str, Optional[dict]]:
        """
        单文件处理包装器（用于线程池），支持递增延迟自动重试

        Args:
            index: 文件索引
            input_path: 输入文件路径
            output_path: 输出文件路径
            total_files: 总文件数

        Returns:
            (output_path, status, error_message, processing_details) 元组
        """
        if self.should_stop:
            return ("", ProcessingStatus.CANCELLED, "用户取消", None)

        file_id = self._resolve_queue_file_id(index, input_path)
        if self._is_file_removed(file_id):
            return ("", ProcessingStatus.CANCELLED, "已从队列移除", None)

        with self._lock:
            self._started_file_ids.add(file_id)

        # 初始化重试计数
        if file_id not in self._retry_counts:
            self._retry_counts[file_id] = 0

        # 更新当前处理文件（线程安全）
        filename = os.path.basename(input_path)
        self.current_file_changed.emit(index, filename)

        retry_info = (
            f" (重试 {self._retry_counts[file_id]}/{self.max_retry_count})"
            if self._retry_counts[file_id] > 0
            else ""
        )
        self.status_message.emit(f"[INFO] 处理文件 {index + 1}/{total_files}: {filename}{retry_info}")

        # 调用实际处理方法
        status, error_message, processing_details = self._process_single_file(
            input_path,
            output_path,
            index,
            file_id=file_id,
        )

        # 自动重试逻辑（递增延迟策略：1秒、2秒、4秒...）
        if status == ProcessingStatus.FAILED and self.auto_retry_failed:
            while self._retry_counts[file_id] < self.max_retry_count and not self.should_stop:
                self._retry_counts[file_id] += 1
                # 递增延迟：2^(retry_count-1) 秒，即 1, 2, 4, 8...
                delay = 2 ** (self._retry_counts[file_id] - 1)
                self.status_message.emit(
                    f"[WARNING] 文件处理失败，{delay}秒后重试 "
                    f"({self._retry_counts[file_id]}/{self.max_retry_count}): {filename}"
                )

                # 递增延迟等待（可中断）
                remaining = float(delay)
                while remaining > 0 and not self.should_stop:
                    time.sleep(min(0.1, remaining))
                    remaining -= 0.1

                if self.should_stop:
                    break
                if self._is_file_removed(file_id):
                    return ("", ProcessingStatus.CANCELLED, "已从队列移除", processing_details)

                status, error_message, processing_details = self._process_single_file(
                    input_path,
                    output_path,
                    index,
                    file_id=file_id,
                )
                if status == ProcessingStatus.COMPLETED:
                    self.status_message.emit(f"[SUCCESS] 重试成功: {filename}")
                    break

        if self.should_stop and status != ProcessingStatus.COMPLETED:
            return ("", ProcessingStatus.CANCELLED, "用户取消", processing_details)

        result_path = output_path if status == ProcessingStatus.COMPLETED else ""
        return (result_path, status, error_message or "", processing_details)

    @staticmethod
    def _pick_processing_info(processor: VideoProcessorThread) -> tuple[Optional[dict], str]:
        """优先选择“有效修复”的 processing_info，其次选择最后一次 processing_info。"""
        effective = getattr(processor, "last_effective_processing_info", None)
        if isinstance(effective, dict) and effective:
            return (effective, "last_effective_processing_info")

        last = getattr(processor, "last_processing_info", None)
        if isinstance(last, dict) and last:
            return (last, "last_processing_info")

        return (None, "none")

    def _build_processing_details(self, processor: VideoProcessorThread) -> dict:
        """提取用于批处理清单追溯的关键字段，避免导出过大。"""
        details: Dict[str, Any] = {}

        info, info_source = self._pick_processing_info(processor)
        if isinstance(info, dict):
            keep_keys = (
                "detection_method",
                "watermark_areas_found",
                "watermark_area_ratio",
                "inpainting_method",
                "inpainting_backend",
                "requested_inpainting_backend",
                "actual_inpainting_backend",
                "inpainting_fallback_reason",
                "quality_level",
                "requested_quality_level",
                "effective_quality_level",
                "effective_inpaint_radius",
                "preprocessing_applied",
                "postprocessing_applied",
                "gpu_inpainting_requested",
                "gpu_inpainting_fallback_reason",
                "gpu_inpainting_runtime_error",
                "configured_inpainting_asset_ref",
                "loaded_inpainting_asset_ref",
                "configured_inpainting_model_path",
                "loaded_inpainting_model_path",
                "gpu_inpainting_profile",
                "gpu_inpainting_retry",
                "gpu_inpainting_oom_retry_used",
                "gpu_inpainting_retry_count",
                "gpu_inpainting_retry_profile",
                "device",
            )
            for key in keep_keys:
                if key in info:
                    details[key] = info.get(key)
            if "quality_level" in details and "requested_quality_level" not in details:
                details["requested_quality_level"] = details.get("quality_level")
            if "effective_quality_level" not in details and "quality_level" in details:
                details["effective_quality_level"] = self._normalize_effective_quality_level(
                    details.get("quality_level")
                )
            details["processing_info_source"] = info_source

        handler = getattr(processor, "ai_handler", None)
        if handler is not None:
            # 不覆盖 processing_info 中已有的键，仅用于补齐观测字段。
            fallback_pairs = {
                "device": getattr(handler, "device", None),
                "requested_quality_level": getattr(handler, "quality_level", None),
                "effective_quality_level": getattr(handler, "last_effective_quality_level", None),
                "effective_inpaint_radius": getattr(handler, "last_effective_inpaint_radius", None),
                "requested_inpainting_backend": getattr(
                    handler, "requested_inpainting_backend", None
                ),
                "actual_inpainting_backend": getattr(handler, "last_inpainting_backend", None),
                "inpainting_fallback_reason": getattr(
                    handler, "gpu_inpainting_fallback_reason", None
                ),
                "gpu_inpainting_fallback_reason": getattr(
                    handler, "gpu_inpainting_fallback_reason", None
                ),
                "gpu_inpainting_runtime_error": getattr(
                    handler, "last_gpu_inpainting_runtime_error", None
                ),
                "configured_inpainting_asset_ref": getattr(
                    handler, "configured_inpainting_asset_ref", None
                ),
                "loaded_inpainting_asset_ref": getattr(
                    handler, "loaded_inpainting_asset_ref", None
                ),
                "configured_inpainting_model_path": getattr(
                    handler, "configured_inpainting_model_path", None
                ),
                "loaded_inpainting_model_path": getattr(
                    handler, "loaded_inpainting_model_path", None
                ),
            }
            for key, value in fallback_pairs.items():
                if key not in details and value is not None:
                    details[key] = value

        summary = getattr(processor, "last_processing_summary", None)
        if isinstance(summary, dict) and summary:
            details["summary"] = dict(summary)

        return details

    @staticmethod
    def _normalize_effective_quality_level(raw_quality_level: Any) -> Optional[int]:
        """兼容旧 processing_info，仅在缺少 effective 值时补位。"""
        if raw_quality_level is None:
            return None
        try:
            normalized = int(raw_quality_level)
        except (TypeError, ValueError):
            return None
        return max(1, min(5, normalized))

    def _get_file_ai_params(self, file_index: int, file_id: Optional[str] = None) -> Dict[str, Any]:
        """优先按 file_id 获取实际运行时参数，缺失时回退到索引和批次级默认值。"""
        normalized_file_id = str(file_id or "").strip()
        if not normalized_file_id:
            normalized_file_id = self._resolve_queue_file_id(file_index, "")

        if normalized_file_id:
            file_ai_params = self.file_ai_params_by_file_id.get(normalized_file_id)
            if isinstance(file_ai_params, dict) and file_ai_params:
                return file_ai_params

        if 0 <= file_index < len(self.file_queue):
            queue_item = self.file_queue[file_index]
            queue_item_ai_params = queue_item.get("ai_params")
            if isinstance(queue_item_ai_params, dict) and queue_item_ai_params:
                return queue_item_ai_params

        file_ai_params = self.file_ai_params_by_index.get(file_index)
        if isinstance(file_ai_params, dict) and file_ai_params:
            return file_ai_params

        return self.ai_params

    def _process_single_file(  # noqa: C901
        self, input_path: str, output_path: str, file_index: int, file_id: Optional[str] = None
    ) -> tuple[ProcessingStatus, str, Optional[dict]]:
        """
        处理单个文件（使用 VideoProcessorThread）

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            file_index: 文件索引

        Returns:
            (ProcessingStatus, error_message, processing_details) 元组
        """
        try:
            if self.should_stop:
                return (ProcessingStatus.CANCELLED, "用户取消", None)

            normalized_file_id = str(file_id or "").strip()
            if not normalized_file_id:
                normalized_file_id = self._resolve_queue_file_id(file_index, input_path)
            if self._is_file_removed(normalized_file_id):
                return (ProcessingStatus.CANCELLED, "已从队列移除", None)

            # 检查输入文件是否存在
            if not os.path.exists(input_path):
                self.logger.error(f"输入文件不存在: {input_path}")
                return (ProcessingStatus.FAILED, f"输入文件不存在: {input_path}", None)

            # 创建输出目录
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            file_ai_params = self._get_file_ai_params(
                file_index,
                file_id=normalized_file_id,
            )
            runtime_performance = {}
            if 0 <= file_index < len(self.file_queue):
                runtime_performance = dict(
                    self.file_queue[file_index].get("runtime_performance") or {}
                )
            if not runtime_performance:
                runtime_performance = ResolvedPerformanceConfig.from_runtime_sources(
                    ai_params=file_ai_params
                ).to_manifest_dict()

            # 创建 VideoProcessorThread 进行实际处理
            processor = VideoProcessorThread(
                input_path=input_path,
                output_path=output_path,
                ai_params=file_ai_params,
                config=self.config,
                preloaded_ai_handler=self.preloaded_ai_handler,  # 复用预加载的AI模型
                enable_multiprocess=bool(file_ai_params.get("enable_multiprocess", False)),
                num_processes=file_ai_params.get("num_processes"),
                use_pipeline=bool(file_ai_params.get("use_pipeline", False)),
                runtime_performance=runtime_performance,
            )

            # 连接进度信号
            def on_progress(progress: int) -> None:
                if self.should_stop:
                    return
                if self._is_file_removed(normalized_file_id):
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
                self._active_processors[normalized_file_id] = processor

            try:
                # 同步运行处理（在当前线程中）
                if self.should_stop:
                    processor.stop()
                    return (ProcessingStatus.CANCELLED, "用户取消", None)
                if self._is_file_removed(normalized_file_id):
                    return (ProcessingStatus.CANCELLED, "已从队列移除", None)
                processor.run()
            finally:
                with self._lock:
                    self._active_processors.pop(normalized_file_id, None)

            # 检查处理结果
            if processing_error:
                self.logger.error(f"文件处理失败: {input_path} - {processing_error}")
                return (
                    ProcessingStatus.FAILED,
                    str(processing_error),
                    self._build_processing_details(processor),
                )

            if processing_success and os.path.exists(output_path):
                self.logger.info(f"文件处理完成: {input_path} -> {output_path}")
                return (
                    ProcessingStatus.COMPLETED,
                    "",
                    self._build_processing_details(processor),
                )

            if self.should_stop:
                self.logger.info(f"文件处理已取消: {input_path}")
                return (
                    ProcessingStatus.CANCELLED,
                    "用户取消",
                    self._build_processing_details(processor),
                )

            self.logger.warning(f"文件处理未生成输出: {input_path}")
            return (
                ProcessingStatus.FAILED,
                "未生成输出文件",
                self._build_processing_details(processor),
            )

        except Exception as e:
            self.logger.error(f"处理单个文件时发生异常: {e}", exc_info=True)
            if self.should_stop:
                return (ProcessingStatus.CANCELLED, "用户取消", None)
            return (ProcessingStatus.FAILED, str(e), None)

    def _ensure_queue_file_id(self, file_info: Dict[str, Any]) -> str:
        """确保批处理线程内部队列项具备稳定 file_id。"""
        existing_file_id = str(file_info.get("file_id", "") or "").strip()
        if existing_file_id:
            return existing_file_id
        generated_file_id = f"file-{uuid.uuid4().hex}"
        file_info["file_id"] = generated_file_id
        return generated_file_id

    def _resolve_queue_file_id(self, index: int, input_path: str) -> str:
        """按索引解析 file_id，缺失时回退为稳定可重现标识。"""
        if 0 <= index < len(self.file_queue):
            file_info = self.file_queue[index]
            if isinstance(file_info, dict):
                return self._ensure_queue_file_id(file_info)
        normalized_input = str(input_path or "").strip() or f"index-{index}"
        return f"legacy-{index}-{normalized_input}"

    def _is_file_removed(self, file_id: str) -> bool:
        """判断文件是否已从运行中的批次队列移除。"""
        normalized = str(file_id or "").strip()
        if not normalized:
            return False
        with self._lock:
            return normalized in self._removed_file_ids

    def remove_pending_file(self, file_id: str) -> bool:
        """尝试从运行中的批次中安全移除等待项。"""
        normalized = str(file_id or "").strip()
        if not normalized:
            return False

        with self._lock:
            if normalized in self._started_file_ids:
                return False
            if normalized in self._active_processors:
                return False

            known_file_ids = {
                self._ensure_queue_file_id(item)
                for item in self.file_queue
                if isinstance(item, dict)
            }
            if normalized not in known_file_ids:
                return False

            matched_futures = [
                future
                for future, queued_file_id in self._future_file_ids.items()
                if queued_file_id == normalized
            ]
        if not matched_futures:
            return False

        cancelled_future = False
        for future in matched_futures:
            try:
                cancelled_future = future.cancel() or cancelled_future
            except Exception:  # noqa: BLE001
                self.logger.debug("取消等待中的 future 失败，继续处理后续 future", exc_info=True)

        if not cancelled_future:
            return False

        with self._lock:
            self._removed_file_ids.add(normalized)
        self.status_message.emit(f"[INFO] 已取消等待中的队列项: {normalized}")
        return True

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

    @staticmethod
    def _build_file_id() -> str:
        return f"file-{uuid.uuid4().hex}"

    def _ensure_file_id(self, item: Dict[str, Any]) -> str:
        file_id = str(item.get("file_id", "") or "").strip()
        if file_id:
            return file_id
        generated = self._build_file_id()
        item["file_id"] = generated
        return generated

    def _get_index_by_file_id(self, file_id: str) -> Optional[int]:
        normalized = str(file_id or "").strip()
        if not normalized:
            return None
        for index, item in enumerate(self.queue):
            if self._ensure_file_id(item) == normalized:
                return index
        return None

    def add_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        runtime_performance: Optional[Dict[str, Any]] = None,
        ai_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """添加文件到队列"""
        if not output_path:
            output_path = resolve_output_path(input_path, ai_params)

        file_info = {
            "file_id": self._build_file_id(),
            "input_path": input_path,
            "output_path": output_path,
            "status": ProcessingStatus.WAITING,
            "progress": 0,
            "error_message": "",
            "processing_details": None,
            "runtime_performance": dict(runtime_performance or {}) or None,
            "output_config": None,
        }

        self.queue.append(file_info)
        return file_info

    def remove_file(self, index: int) -> bool:
        """从队列中移除文件"""
        if 0 <= index < len(self.queue):
            self.queue.pop(index)
            return True
        return False

    def remove_file_by_id(self, file_id: str) -> bool:
        """通过 file_id 移除文件。"""
        index = self._get_index_by_file_id(file_id)
        if index is None:
            return False
        self.queue.pop(index)
        return True

    def clear_queue(self):
        """清空队列"""
        self.queue.clear()

    def get_queue(self) -> List[Dict[str, Any]]:
        """获取队列"""
        for item in self.queue:
            self._ensure_file_id(item)
        return self.queue.copy()

    def get_index_by_file_id(self, file_id: str) -> Optional[int]:
        """通过 file_id 获取当前队列索引。"""
        return self._get_index_by_file_id(file_id)

    def update_file_status(
        self, index: int, status: ProcessingStatus, progress: int = 0, error_message: str = ""
    ):
        """更新文件状态"""
        if 0 <= index < len(self.queue):
            self._ensure_file_id(self.queue[index])
            self.queue[index]["status"] = status
            self.queue[index]["progress"] = progress
            self.queue[index]["error_message"] = error_message

    def update_file_status_by_id(
        self, file_id: str, status: ProcessingStatus, progress: int = 0, error_message: str = ""
    ) -> bool:
        """通过 file_id 更新文件状态。"""
        index = self._get_index_by_file_id(file_id)
        if index is None:
            return False
        self.update_file_status(index, status, progress, error_message)
        return True

    def update_file_processing_details(self, index: int, processing_details: Any) -> None:
        """更新文件的处理详情（用于清单导出追溯）。"""
        if 0 <= index < len(self.queue):
            self._ensure_file_id(self.queue[index])
            self.queue[index]["processing_details"] = processing_details

    def update_file_processing_details_by_id(self, file_id: str, processing_details: Any) -> bool:
        """通过 file_id 更新处理详情。"""
        index = self._get_index_by_file_id(file_id)
        if index is None:
            return False
        self.update_file_processing_details(index, processing_details)
        return True

    def update_file_runtime_performance(self, index: int, runtime_performance: Any) -> None:
        """更新文件的运行时性能快照（用于 manifest 追溯）。"""
        if 0 <= index < len(self.queue):
            self._ensure_file_id(self.queue[index])
            self.queue[index]["runtime_performance"] = runtime_performance

    def update_file_runtime_performance_by_id(self, file_id: str, runtime_performance: Any) -> bool:
        """通过 file_id 更新运行时性能快照。"""
        index = self._get_index_by_file_id(file_id)
        if index is None:
            return False
        self.update_file_runtime_performance(index, runtime_performance)
        return True

    def update_file_ai_params(self, index: int, ai_params: Any) -> None:
        """更新文件级运行时 ai_params 快照。"""
        if 0 <= index < len(self.queue):
            self._ensure_file_id(self.queue[index])
            self.queue[index]["ai_params"] = dict(ai_params or {})

    def update_file_ai_params_by_id(self, file_id: str, ai_params: Any) -> bool:
        """通过 file_id 更新文件级运行时 ai_params 快照。"""
        index = self._get_index_by_file_id(file_id)
        if index is None:
            return False
        self.update_file_ai_params(index, ai_params)
        return True

    def update_file_output_path(self, index: int, output_path: str) -> None:
        """更新文件的输出路径。"""
        if 0 <= index < len(self.queue):
            self._ensure_file_id(self.queue[index])
            self.queue[index]["output_path"] = output_path

    def update_file_output_path_by_id(self, file_id: str, output_path: str) -> bool:
        """通过 file_id 更新输出路径。"""
        index = self._get_index_by_file_id(file_id)
        if index is None:
            return False
        self.update_file_output_path(index, output_path)
        return True

    def update_file_output_config(self, index: int, output_config: Any) -> None:
        """更新文件的输出参数快照（用于 manifest 追溯）。"""
        if 0 <= index < len(self.queue):
            self._ensure_file_id(self.queue[index])
            self.queue[index]["output_config"] = output_config

    def update_file_output_config_by_id(self, file_id: str, output_config: Any) -> bool:
        """通过 file_id 更新输出参数快照。"""
        index = self._get_index_by_file_id(file_id)
        if index is None:
            return False
        self.update_file_output_config(index, output_config)
        return True

    def get_file_info(self, index: int) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        if index < 0 or index >= len(self.queue):
            return None
        self._ensure_file_id(self.queue[index])
        return self.queue[index].copy()

    def get_file_info_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """通过 file_id 获取文件信息。"""
        index = self._get_index_by_file_id(file_id)
        if index is None:
            return None
        return self.get_file_info(index)

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
