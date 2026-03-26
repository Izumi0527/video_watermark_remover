from __future__ import annotations

import multiprocessing
import os
import tempfile
import threading
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import queues as mp_queues
from multiprocessing import synchronize
from typing import Any, Optional, Tuple, cast

import cv2
from PyQt6.QtCore import QTimer

from ..utils.path import build_temp_path
from ..workers.audio import async_audio_extractor
from ..workers.frame_processor import frame_processor_worker, init_worker_ai_handler
from ..workers.frame_reader import frame_reader_worker
from ..workers.frame_writer import frame_writer_worker


def _create_manager_queue(manager: Any, maxsize: Optional[int] = None) -> mp_queues.Queue[Any]:
    queue_obj = manager.Queue(maxsize=maxsize) if maxsize is not None else manager.Queue()
    return cast(mp_queues.Queue[Any], queue_obj)


def _calculate_queue_sizes(processor) -> Tuple[int, int]:
    try:
        import psutil  # type: ignore[import-untyped]

        available_mb = psutil.virtual_memory().available / (1024 * 1024)

        if available_mb < 4096:
            processor.logger.info(
                f"Low memory detected ({available_mb:.0f}MB), using small queues (20+40)"
            )
            return (20, 40)
        elif available_mb < 8192:
            processor.logger.info(
                f"Medium memory detected ({available_mb:.0f}MB), using medium queues (30+50)"
            )
            return (30, 50)
        else:
            processor.logger.info(
                f"High memory detected ({available_mb:.0f}MB), using large queues (50+100)"
            )
            return (50, 100)

    except ImportError:
        processor.logger.warning("psutil not available, using default queue sizes (30+50)")
        return (30, 50)

    except Exception as e:  # noqa: BLE001
        processor.logger.warning(f"Failed to detect memory: {e}, using default queue sizes (30+50)")
        return (30, 50)


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


def process_video_pipeline(processor) -> None:  # noqa: C901
    """
    流水线视频处理
    使用流水线: 读取线程 → 处理进程池 → 写入线程
    """
    frame_queue: Optional[mp_queues.Queue[Any]] = None
    result_queue: Optional[mp_queues.Queue[Any]] = None
    progress_queue: Optional[mp_queues.Queue[Any]] = None
    audio_temp_path = None

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
        frame_queue_size, result_queue_size = _calculate_queue_sizes(processor)
        frame_queue = _create_manager_queue(manager, frame_queue_size)
        result_queue = _create_manager_queue(manager, result_queue_size)
        progress_queue = _create_manager_queue(manager)
        processor._stop_event = cast(synchronize.Event, manager.Event())

        temp_output_path = build_temp_path(processor.output_path, "temp_pipeline")

        audio_completion_event = None
        audio_thread = None
        if processor.ffmpeg_processor and processor.ffmpeg_processor.is_available():
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

        for i, future in enumerate(processor_futures):
            future.result()
        processor.logger.info("All processor workers completed")

        processor._writer_thread.join()
        processor.logger.info("Frame writer completed")

        if not writer_result:
            raise Exception("Writer thread failed to return result")

        success, error_msg = writer_result[0]
        if not success:
            raise Exception(f"Frame writer failed: {error_msg}")

        if error_msg:
            processor.logger.warning(error_msg)

        if processor.ffmpeg_processor and processor.ffmpeg_processor.is_available():
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
        processor.finished.emit(processor.output_path)

    except Exception as e:  # noqa: BLE001
        processor.logger.error(f"Pipeline processing failed, falling back to chunk mode: {e}")
        processor.status.emit("⚠️ 流水线失败，切换到分块模式")
        processor._process_video_multiprocess()

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
