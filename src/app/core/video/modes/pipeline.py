from __future__ import annotations

import multiprocessing
import os
import tempfile
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from multiprocessing import queues as mp_queues
from multiprocessing import synchronize
from typing import Any, Optional, cast

import cv2
from PyQt6.QtCore import QTimer

from ..output_strategy import should_preserve_audio
from ..utils.backpressure import QueueBudget, calculate_runtime_queue_budget
from ..utils.path import build_temp_path
from ..workers.audio import async_audio_extractor
from ..workers.frame_processor import frame_processor_worker, init_worker_ai_handler
from ..workers.frame_reader import frame_reader_worker
from ..workers.frame_writer import frame_writer_worker


def _is_cancel_requested(processor) -> bool:
    """统一判断是否收到用户取消请求。"""
    if not getattr(processor, "_is_running", True):
        return True
    stop_event = getattr(processor, "_stop_event", None)
    return bool(stop_event and stop_event.is_set())


def _finalize_pipeline_cancel(processor, temp_output_path: Optional[str] = None) -> str:
    """统一处理流水线取消收尾，避免误回退到其他模式。"""
    processor.status.emit("⚠️ 处理已取消")
    if temp_output_path and os.path.exists(temp_output_path):
        try:
            os.remove(temp_output_path)
        except Exception as e:  # noqa: BLE001
            processor.logger.debug("取消后清理流水线临时文件失败: %s", e)
    processor.logger.info("Pipeline processing cancelled by user")
    return ""


def _create_manager_queue(manager: Any, maxsize: Optional[int] = None) -> mp_queues.Queue[Any]:
    queue_obj = manager.Queue(maxsize=maxsize) if maxsize is not None else manager.Queue()
    return cast(mp_queues.Queue[Any], queue_obj)


def _calculate_queue_budget(processor, frame_shape: tuple[int, int]) -> QueueBudget:
    enable_cache = bool(processor.ai_params.get("enable_cache", True))
    cache_size_mb = int(processor.ai_params.get("cache_size_mb", 512) or 512)
    queue_budget = calculate_runtime_queue_budget(
        enable_cache=enable_cache,
        cache_size_mb=cache_size_mb,
        frame_shape=frame_shape,
        requested_worker_count=processor.num_processes,
    )
    if (
        queue_budget.pipeline_viable
        and queue_budget.effective_worker_count != processor.num_processes
    ):
        processor.logger.warning(
            "Pipeline worker count capped by cache budget: requested=%s effective=%s "
            "estimated_memory=%.1fMB cache_size_mb=%s",
            processor.num_processes,
            queue_budget.effective_worker_count,
            queue_budget.estimated_total_memory_mb,
            cache_size_mb,
        )
        processor.num_processes = queue_budget.effective_worker_count
    processor.logger.info(
        "Pipeline queue budget resolved: enable_cache=%s cache_size_mb=%s "
        "requested_workers=%s effective_workers=%s viable=%s "
        "frame_queue=%s result_queue=%s writer_buffer=%s estimated_memory=%.1fMB",
        enable_cache,
        cache_size_mb,
        queue_budget.requested_worker_count,
        queue_budget.effective_worker_count,
        queue_budget.pipeline_viable,
        queue_budget.frame_queue_size,
        queue_budget.result_queue_size,
        queue_budget.writer_buffer_size,
        queue_budget.estimated_total_memory_mb,
    )
    return queue_budget


def _check_pipeline_progress(
    processor, progress_queue: mp_queues.Queue[Any], total_frames: int
) -> None:
    """检查流水线进度并发射详细进度信息"""
    try:
        latest_written = 0  # 跟踪最新写入帧数

        while not progress_queue.empty():
            progress_data = progress_queue.get_nowait()

            if "written_frames" in progress_data:
                written = progress_data["written_frames"]
                latest_written = max(latest_written, written)  # 更新最新写入帧数
                progress_pct = int((written / total_frames) * 95) + 5
                processor.progress.emit(progress_pct)
                processor.status.emit(f"💾 写入进度: {written}/{total_frames} 帧")

            elif "worker_id" in progress_data:
                pass

        # 发射详细进度信息（帧进度、处理速度、ETA等）
        if latest_written > 0:
            processor._emit_detailed_progress(
                phase="processing_frames",
                current_frame=latest_written,
                total_frames=total_frames,
                additional_info={
                    "mode": "pipeline",
                    "num_processes": processor.num_processes,
                },
            )

    except Exception as e:  # noqa: BLE001
        processor.logger.warning(f"Pipeline progress polling error: {e}")


def _wait_processor_futures(processor, processor_futures: list[Any]) -> None:
    """等待处理进程完成；若已收到取消请求则快速退出等待，避免 UI stop 超时。"""
    pending = list(processor_futures)
    while pending:
        next_pending: list[Any] = []
        for future in pending:
            try:
                future.result(timeout=0.2)
            except FuturesTimeoutError:
                if _is_cancel_requested(processor):
                    return
                next_pending.append(future)
        pending = next_pending


def process_video_pipeline(processor) -> None:  # noqa: C901
    """
    流水线视频处理
    使用流水线: 读取线程 → 处理进程池 → 写入线程
    """
    frame_queue: Optional[mp_queues.Queue[Any]] = None
    result_queue: Optional[mp_queues.Queue[Any]] = None
    progress_queue: Optional[mp_queues.Queue[Any]] = None
    audio_temp_path = None
    temp_output_path: Optional[str] = None
    cancel_requested = False
    fallback_error: Optional[Exception] = None
    completed_output_path: Optional[str] = None

    try:
        processor.status.emit("📊 分析视频信息...")
        cap = cv2.VideoCapture(processor.input_path)
        if not cap.isOpened():
            from ...exceptions import VideoReadError

            raise VideoReadError("无法打开视频文件", details=f"文件路径: {processor.input_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        cap.release()

        processor.logger.info(f"Video info: {width}x{height}, {fps} fps, {total_frames} frames")
        processor.status.emit(f"🚀 使用流水线模式处理 (读取 → {processor.num_processes}进程 → 写入)")

        # 发射初始详细进度（处理开始）
        processor._emit_detailed_progress("processing_frames", 0, total_frames)

        manager = multiprocessing.Manager()
        queue_budget = _calculate_queue_budget(processor, (height, width))
        if not queue_budget.pipeline_viable:
            processor.logger.warning(
                "Pipeline disabled by cache budget: cache_size_mb=%s estimated_minimum=%.1fMB frame=%sx%s",
                processor.ai_params.get("cache_size_mb", 512),
                queue_budget.minimum_viable_memory_mb,
                width,
                height,
            )
            processor.status.emit("⚠️ 缓存预算不足以运行流水线，切换到单进程模式")
            processor._process_video_singleprocess()
            return
        frame_queue = _create_manager_queue(manager, queue_budget.frame_queue_size)
        result_queue = _create_manager_queue(manager, queue_budget.result_queue_size)
        progress_queue = _create_manager_queue(manager)
        processor._stop_event = cast(synchronize.Event, manager.Event())

        temp_output_path = build_temp_path(processor.output_path, "temp_pipeline")

        audio_completion_event = None
        audio_thread = None
        if (
            should_preserve_audio(processor.ai_params)
            and processor.ffmpeg_processor
            and processor.ffmpeg_processor.is_available()
        ):
            with tempfile.NamedTemporaryFile(
                suffix=".aac", prefix="audio_temp_", delete=False
            ) as tmp:
                audio_temp_path = tmp.name
            audio_completion_event = threading.Event()

            audio_thread = threading.Thread(
                target=async_audio_extractor,
                args=(
                    processor.input_path,
                    audio_temp_path,
                    audio_completion_event,
                    processor._stop_event,
                    processor.logger,
                ),
                daemon=True,
            )
            audio_thread.start()
            processor.logger.info("Async audio extraction started")

        processor.status.emit("📖 启动帧读取线程...")
        processor._reader_thread = threading.Thread(
            target=frame_reader_worker,
            args=(
                processor.input_path,
                frame_queue,
                total_frames,
                processor._stop_event,
            ),
            daemon=True,
        )
        processor._reader_thread.start()
        processor.logger.info("Frame reader thread started")

        processor.status.emit(f"🎨 启动 {processor.num_processes} 个处理进程...")

        config_dict = None
        if processor.config:
            config_dict = {
                section: dict(processor.config[section]) for section in processor.config.sections()
            }

        # 使用 initializer 模式：进程池创建时预加载 AI 模型
        # 这样每个进程只加载一次模型，而不是每次处理任务都加载
        processor._processor_pool = ProcessPoolExecutor(
            max_workers=processor.num_processes,
            initializer=init_worker_ai_handler,
            initargs=(processor.ai_params,),
        )
        processor_futures = []

        for i in range(processor.num_processes):
            future = processor._processor_pool.submit(
                frame_processor_worker,
                frame_queue,
                result_queue,
                processor.ai_params,
                config_dict,
                processor._stop_event,
                progress_queue,
                i,
            )
            processor_futures.append(future)

        processor.logger.info(f"{processor.num_processes} processor workers started")

        processor.status.emit("💾 启动帧写入线程...")
        video_params = {
            "fps": fps,
            "width": width,
            "height": height,
            "fourcc": fourcc,
            "writer_buffer_size": queue_budget.writer_buffer_size,
        }

        writer_result = []

        def writer_wrapper():
            result = frame_writer_worker(
                result_queue,
                temp_output_path,
                video_params,
                total_frames,
                processor._stop_event,
                progress_queue,
            )
            writer_result.append(result)

        processor._writer_thread = threading.Thread(
            target=writer_wrapper,
            daemon=True,
        )
        processor._writer_thread.start()
        processor.logger.info("Frame writer thread started")

        processor._progress_timer = QTimer()
        processor._progress_timer.timeout.connect(
            lambda: _check_pipeline_progress(processor, progress_queue, total_frames)
        )
        processor._progress_timer.start(100)

        processor.status.emit("⏳ 流水线处理中...")
        processor._reader_thread.join()
        processor.logger.info("Frame reader completed")

        _wait_processor_futures(processor, processor_futures)
        processor.logger.info("All processor workers completed")

        processor._writer_thread.join()
        processor.logger.info("Frame writer completed")

        if _is_cancel_requested(processor):
            cancel_requested = True
        else:
            if not writer_result:
                raise Exception("Writer thread failed to return result")

            success, error_msg = writer_result[0]
            if not success:
                raise Exception(f"Frame writer failed: {error_msg}")

            if error_msg:
                processor.logger.warning(error_msg)

            if (
                should_preserve_audio(processor.ai_params)
                and processor.ffmpeg_processor
                and processor.ffmpeg_processor.is_available()
            ):
                processor.status.emit("🎵 正在合并原始音频...")
                processor.progress.emit(95)

                # 发射音频合并阶段进度
                processor._emit_detailed_progress("merging_audio", 0, 1)

                audio_timeout = max(10, total_frames / 100)
                audio_source = processor.input_path

                if audio_completion_event:
                    if audio_completion_event.wait(timeout=audio_timeout):
                        processor.logger.info(f"Using extracted audio: {audio_temp_path}")
                        audio_source = audio_temp_path
                    else:
                        processor.logger.warning(
                            f"Audio extraction incomplete (timeout={audio_timeout:.1f}s), using original video"
                        )

                audio_success = processor.ffmpeg_processor.process_video_with_audio_preservation(
                    original_video_path=audio_source,
                    processed_video_path=temp_output_path,
                    final_output_path=processor.output_path,
                )

                if audio_temp_path and os.path.exists(audio_temp_path):
                    try:
                        os.remove(audio_temp_path)
                        processor.logger.debug(f"Removed temp audio: {audio_temp_path}")
                    except Exception as e:  # noqa: BLE001
                        processor.logger.warning(f"Failed to remove temp audio: {e}")

                if audio_success:
                    processor.logger.info("Audio merged successfully")
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)
                else:
                    processor.logger.warning("Audio merge failed, using video-only output")
                    if os.path.exists(temp_output_path):
                        if os.path.exists(processor.output_path):
                            os.remove(processor.output_path)
                        os.replace(temp_output_path, processor.output_path)
            else:
                if os.path.exists(processor.output_path):
                    os.remove(processor.output_path)
                os.replace(temp_output_path, processor.output_path)

            processor.progress.emit(100)
            processor.status.emit(f"✅ 流水线处理完成! 处理了 {total_frames} 帧")

            # 发射完成阶段进度
            processor._emit_detailed_progress("completed", total_frames, total_frames)

            processor.logger.info(f"Pipeline video processing completed: {processor.output_path}")
            completed_output_path = processor.output_path

    except Exception as e:  # noqa: BLE001
        if _is_cancel_requested(processor):
            cancel_requested = True
        else:
            fallback_error = e

    finally:
        if processor._progress_timer:
            processor._progress_timer.stop()
            processor._progress_timer = None

        if processor._stop_event:
            processor._stop_event.set()
            processor._stop_event = None

        if processor._reader_thread and processor._reader_thread.is_alive():
            processor._reader_thread.join(timeout=2)

        if processor._writer_thread and processor._writer_thread.is_alive():
            processor._writer_thread.join(timeout=2)

        if processor._processor_pool:
            processor._processor_pool.shutdown(wait=False)
            processor._processor_pool = None

        for queue in [frame_queue, result_queue, progress_queue]:
            if queue:
                try:
                    while not queue.empty():
                        queue.get_nowait()
                except Exception as e:  # noqa: BLE001
                    processor.logger.debug(f"清空队列失败: {e}")

        if audio_temp_path and os.path.exists(audio_temp_path):
            try:
                os.remove(audio_temp_path)
                processor.logger.debug(f"Cleaned up temp audio in finally: {audio_temp_path}")
            except Exception as e:  # noqa: BLE001
                processor.logger.warning(f"Failed to clean up temp audio in finally: {e}")

    if cancel_requested:
        processor.finished.emit(
            _finalize_pipeline_cancel(processor, temp_output_path=temp_output_path)
        )
        return

    if fallback_error is not None:
        processor.logger.error(
            "Pipeline processing failed, falling back to chunk mode: %s", fallback_error
        )
        processor.status.emit("⚠️ 流水线失败，切换到分块模式")
        processor._process_video_multiprocess()
        return

    if completed_output_path is not None:
        processor.finished.emit(completed_output_path)
