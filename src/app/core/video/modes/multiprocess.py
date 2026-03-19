from __future__ import annotations

import multiprocessing
import os
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import queues as mp_queues
from multiprocessing import synchronize
from typing import Any, List, Optional, Tuple, cast

import cv2
from PyQt6.QtCore import QTimer

from ..workers.chunk import init_chunk_worker_ai_handler, process_video_chunk
from ..utils.path import build_temp_path


def _calculate_chunks(
    processor,
    total_frames: int,
    num_processes: int,
) -> List[Tuple[int, int, str]]:
    chunk_size = total_frames // num_processes
    chunks = []

    for i in range(num_processes):
        start = i * chunk_size
        end = total_frames if i == num_processes - 1 else (i + 1) * chunk_size
        temp_path = os.path.join(tempfile.gettempdir(), f"video_chunk_{i}_{os.getpid()}.mp4")
        chunks.append((start, end, temp_path))

    processor.logger.info(f"Calculated {num_processes} chunks for {total_frames} frames")
    return chunks


def _check_progress_queue(
    processor, progress_queue: mp_queues.Queue[Any], total_frames: int
) -> None:
    """检查进度队列并发射详细进度信息"""
    try:
        aggregated_current = 0  # 聚合当前已处理帧数
        chunk_size = total_frames // processor.num_processes if processor.num_processes > 0 else 0

        while not progress_queue.empty():
            progress_data = progress_queue.get_nowait()

            chunk_id = progress_data["chunk_id"]
            current = progress_data["current"]
            total = progress_data["total"]

            chunk_progress = (current / total) if total > 0 else 0
            overall_progress = (
                int(
                    (chunk_id / processor.num_processes + chunk_progress / processor.num_processes)
                    * 90
                )
                + 10
            )

            # 计算聚合的当前帧数（基于块ID和块内进度）
            aggregated_current = (chunk_id * chunk_size) + current

            processor.progress.emit(overall_progress)
            processor.status.emit(
                f"🎨 处理块 {chunk_id + 1}/{processor.num_processes}: {current}/{total} 帧"
            )

        # 发射详细进度信息（帧进度、处理速度、ETA等）
        if aggregated_current > 0:
            processor._emit_detailed_progress(
                phase="processing_frames",
                current_frame=aggregated_current,
                total_frames=total_frames,
                additional_info={
                    "mode": "multiprocess",
                    "num_processes": processor.num_processes,
                },
            )

    except Exception as e:  # noqa: BLE001
        processor.logger.warning(f"Progress polling error: {e}")


def _merge_video_chunks(processor, chunk_paths: List[str], output_path: str) -> None:
    concat_list_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            concat_list_path = f.name
            for chunk_path in chunk_paths:
                abs_path = os.path.abspath(chunk_path).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")

        processor.logger.info(f"Created concat list: {concat_list_path}")

        ffmpeg_cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-c",
            "copy",
            output_path,
            "-y",
        ]

        processor.logger.info(f"Running FFmpeg merge: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise Exception(f"FFmpeg merge failed: {result.stderr}")

        processor.logger.info(f"Video chunks merged successfully: {output_path}")

    finally:
        if concat_list_path and os.path.exists(concat_list_path):
            try:
                os.remove(concat_list_path)
            except Exception as e:  # noqa: BLE001
                processor.logger.warning(f"Failed to remove concat list: {e}")


def process_video_multiprocess(processor) -> None:  # noqa: C901
    """
    多进程视频处理
    使用分块批处理策略,将视频分割成多个块并行处理
    """
    temp_files: List[str] = []
    progress_queue: Optional[mp_queues.Queue[Any]] = None

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
        cap.release()

        processor.logger.info(f"Video info: {width}x{height}, {fps} fps, {total_frames} frames")
        processor.status.emit(f"🚀 使用 {processor.num_processes} 个进程并行处理 {total_frames} 帧")

        # 发射初始详细进度（处理开始）
        processor._emit_detailed_progress("processing_frames", 0, total_frames)

        chunks = _calculate_chunks(processor, total_frames, processor.num_processes)
        temp_files = [chunk[2] for chunk in chunks]

        manager = multiprocessing.Manager()
        progress_queue = cast(mp_queues.Queue[Any], manager.Queue())
        processor._stop_event = cast(synchronize.Event, manager.Event())

        processor._progress_timer = QTimer()
        processor._progress_timer.timeout.connect(
            lambda: _check_progress_queue(processor, progress_queue, total_frames)
        )
        processor._progress_timer.start(100)

        config_dict = None
        if processor.config:
            config_dict = {
                section: dict(processor.config[section]) for section in processor.config.sections()
            }

        processor.status.emit("🎨 开始并行处理视频块...")
        results: List[Tuple[Optional[str], bool, Optional[str]]] = []

        # 使用 initializer 模式：进程池创建时预加载 AI 模型
        # 这样每个进程只加载一次模型，而不是每次处理块都加载
        with ProcessPoolExecutor(
            max_workers=processor.num_processes,
            initializer=init_chunk_worker_ai_handler,
            initargs=(processor.ai_params,),
        ) as executor:
            futures = []
            for i, (start, end, temp_path) in enumerate(chunks):
                future = executor.submit(
                    process_video_chunk,
                    processor.input_path,
                    start,
                    end,
                    temp_path,
                    processor.ai_params,
                    config_dict,
                    progress_queue,
                    processor._stop_event,
                    i,
                )
                futures.append(future)

            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                processor.logger.info(f"Chunk completed: {result[0]}, success={result[1]}")

        failed_chunks = [r for r in results if not r[1]]
        if failed_chunks:
            error_messages = [r[2] for r in failed_chunks if r[2]]
            raise Exception(f"{len(failed_chunks)} 个块处理失败: {'; '.join(error_messages)}")

        chunk_paths = [r[0] for r in results if r[0] is not None]
        chunk_paths.sort()

        processor.status.emit("🔗 正在合并视频块...")
        processor.progress.emit(95)

        # 发射合并视频块阶段进度
        processor._emit_detailed_progress("merging_audio", 0, 1, {"sub_phase": "merging_chunks"})

        temp_merged_path = build_temp_path(processor.output_path, "temp_merged")
        _merge_video_chunks(processor, chunk_paths, temp_merged_path)

        if processor.ffmpeg_processor and processor.ffmpeg_processor.is_available():
            processor.status.emit("🎵 正在合并原始音频...")
            processor.progress.emit(97)

            # 发射音频合并阶段进度
            processor._emit_detailed_progress("merging_audio", 0, 1, {"sub_phase": "merging_audio"})

            audio_success = processor.ffmpeg_processor.process_video_with_audio_preservation(
                original_video_path=processor.input_path,
                processed_video_path=temp_merged_path,
                final_output_path=processor.output_path,
            )

            if audio_success:
                processor.logger.info("Audio merged successfully")
                if os.path.exists(temp_merged_path):
                    os.remove(temp_merged_path)
            else:
                processor.logger.warning("Audio merge failed, using video-only output")
                if os.path.exists(temp_merged_path):
                    if os.path.exists(processor.output_path):
                        os.remove(processor.output_path)
                    os.replace(temp_merged_path, processor.output_path)
        else:
            if os.path.exists(processor.output_path):
                os.remove(processor.output_path)
            os.replace(temp_merged_path, processor.output_path)

        processor.progress.emit(100)
        processor.status.emit(f"✅ 多进程处理完成! 处理了 {total_frames} 帧")

        # 发射完成阶段进度
        processor._emit_detailed_progress("completed", total_frames, total_frames)

        processor.logger.info(f"Multiprocess video processing completed: {processor.output_path}")
        processor.finished.emit(processor.output_path)

    except Exception as e:  # noqa: BLE001
        processor.logger.error(
            f"Multiprocess processing failed, falling back to single-process: {e}"
        )
        processor.status.emit("⚠️ 多进程失败，切换到单进程模式")
        processor._process_video_singleprocess()

    finally:
        if processor._progress_timer:
            processor._progress_timer.stop()
            processor._progress_timer = None

        if processor._stop_event:
            processor._stop_event.set()
            processor._stop_event = None

        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    processor.logger.debug(f"Removed temp file: {temp_file}")
                except Exception as e:  # noqa: BLE001
                    processor.logger.warning(f"Failed to remove temp file {temp_file}: {e}")
