# flake8: noqa
# mypy: ignore-errors
import logging
import multiprocessing
import os
from typing import Optional, Tuple

import cv2

from ..ai.ai_handler import AIHandler

# ============================================================================
# 进程池级别的模型缓存
# 使用 initializer 模式：每个进程只加载一次模型，后续复用
# ============================================================================
_chunk_worker_ai_handler: Optional[AIHandler] = None
_chunk_worker_ai_params: Optional[dict] = None


def init_chunk_worker_ai_handler(ai_params: dict) -> None:
    """
    进程池初始化函数 - 每个工作进程只调用一次

    在 ProcessPoolExecutor 创建时通过 initializer 参数调用，
    避免每次处理块都重新加载模型（节省约 500MB×N 内存）

    Args:
        ai_params: AI 参数字典
    """
    global _chunk_worker_ai_handler, _chunk_worker_ai_params
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Initializing AI handler for chunk worker process (PID: {os.getpid()})")
        _chunk_worker_ai_params = ai_params
        _chunk_worker_ai_handler = AIHandler(None, ai_params)

        if not _chunk_worker_ai_handler.load_models():
            logger.error("Chunk worker process failed to load AI models during initialization")
            _chunk_worker_ai_handler = None
        else:
            logger.info("Chunk worker process AI handler initialized successfully")

    except Exception as e:
        logger.error(f"Chunk worker process initialization error: {e}")
        _chunk_worker_ai_handler = None


def get_chunk_worker_ai_handler() -> Optional[AIHandler]:
    """获取当前进程的 AI 处理器实例"""
    return _chunk_worker_ai_handler


def process_video_chunk(
    video_path: str,
    start_frame: int,
    end_frame: int,
    output_path: str,
    ai_params: dict,
    config_dict: Optional[dict],
    progress_queue: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
    chunk_id: int,
) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    处理视频块（在子进程中运行）

    Args:
        video_path: 输入视频路径
        start_frame: 起始帧索引
        end_frame: 结束帧索引
        output_path: 输出临时文件路径
        ai_params: AI 参数字典
        config_dict: 配置字典（ConfigParser无法pickle，传递字典）
        progress_queue: 进度队列（发送进度信息到主线程）
        stop_event: 停止事件（主线程通知停止）
        chunk_id: 块ID（用于进度标识）

    Returns:
        (输出路径, 成功标志, 错误信息)
    """
    global _chunk_worker_ai_handler
    logger = logging.getLogger(__name__)

    try:
        # 优先使用进程池初始化时加载的模型
        ai_handler = _chunk_worker_ai_handler

        # 降级处理：如果初始化时未加载模型，则在此处加载（兼容旧调用方式）
        if ai_handler is None:
            logger.warning(f"Chunk {chunk_id}: AI handler not pre-initialized, loading now...")
            ai_handler = AIHandler(None, ai_params)
            if not ai_handler.load_models():
                return (None, False, "AI 模型加载失败")
            _chunk_worker_ai_handler = ai_handler  # 缓存供后续使用
        else:
            logger.info(f"Chunk {chunk_id}: Using pre-initialized AI handler")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return (None, False, "无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            logger.warning(f"Chunk {chunk_id}: mp4v codec failed, trying XVID")
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            if not out.isOpened():
                cap.release()
                return (
                    None,
                    False,
                    f"无法创建输出文件（尝试了 mp4v 和 XVID 编码器）: {output_path}",
                )

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        total_frames_in_chunk = end_frame - start_frame
        processed_count = 0

        for i in range(total_frames_in_chunk):
            if stop_event.is_set():
                logger.info(f"Chunk {chunk_id} stopped by user request")
                break

            ret, frame = cap.read()
            if not ret:
                break

            try:
                processing_params = {
                    "auto_detect": ai_params.get("auto_detect", True),
                    "detection_sensitivity": ai_params.get("detection_sensitivity", 0.5),
                    "user_mask": ai_params.get("user_mask", None),
                }
                processed_frame, _ = ai_handler.process_frame(frame, processing_params)
                out.write(processed_frame)
                processed_count += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Frame processing error in chunk {chunk_id}: {e}")
                out.write(frame)

            if i % 10 == 0:
                try:
                    progress_queue.put(
                        {
                            "chunk_id": chunk_id,
                            "current": i,
                            "total": total_frames_in_chunk,
                            "processed": processed_count,
                        },
                        block=False,
                    )
                except Exception:
                    pass

        cap.release()
        out.release()

        logger.info(f"Chunk {chunk_id} completed: {processed_count}/{total_frames_in_chunk} frames")
        return (output_path, True, None)

    except Exception as e:  # noqa: BLE001
        error_msg = f"Chunk {chunk_id} error: {str(e)}"
        logger.error(error_msg)
        return (None, False, error_msg)
