# flake8: noqa
# mypy: ignore-errors
from __future__ import annotations

import logging
import multiprocessing
import os
from typing import Any, Optional, Tuple

import cv2

from ..output_strategy import create_video_writer

AIHandler = None


def _resolve_ai_handler_class():
    global AIHandler
    if AIHandler is None:
        from ...ai.ai_handler import AIHandler as imported_ai_handler

        AIHandler = imported_ai_handler
    return AIHandler


# ============================================================================
# 进程池级别的模型缓存
# 使用 initializer 模式：每个进程只加载一次模型，后续复用
# ============================================================================
_chunk_worker_ai_handler: Optional[Any] = None
_chunk_worker_ai_params: Optional[dict] = None


def init_chunk_worker_ai_handler(ai_params: dict) -> None:
    """进程池初始化函数 - 每个工作进程只调用一次。"""
    global _chunk_worker_ai_handler, _chunk_worker_ai_params
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Initializing AI handler for chunk worker process (PID: {os.getpid()})")
        _chunk_worker_ai_params = ai_params
        ai_handler_class = _resolve_ai_handler_class()
        _chunk_worker_ai_handler = ai_handler_class(None, ai_params)

        if not _chunk_worker_ai_handler.load_models():
            logger.error("Chunk worker process failed to load AI models during initialization")
            _chunk_worker_ai_handler = None
        else:
            logger.info("Chunk worker process AI handler initialized successfully")

    except Exception as e:
        logger.error(f"Chunk worker process initialization error: {e}")
        _chunk_worker_ai_handler = None


def get_chunk_worker_ai_handler() -> Optional[Any]:
    """获取当前进程的 AI 处理器实例。"""
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
    """处理视频块（在子进程中运行）。"""
    global _chunk_worker_ai_handler
    logger = logging.getLogger(__name__)

    try:
        ai_handler = _chunk_worker_ai_handler

        if ai_handler is None:
            logger.warning(f"Chunk {chunk_id}: AI handler not pre-initialized, loading now...")
            ai_handler_class = _resolve_ai_handler_class()
            ai_handler = ai_handler_class(None, ai_params)
            if not ai_handler.load_models():
                return (None, False, "AI 模型加载失败")
            _chunk_worker_ai_handler = ai_handler
        else:
            logger.info(f"Chunk {chunk_id}: Using pre-initialized AI handler")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return (None, False, "无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out, selected_codec = create_video_writer(
            output_path,
            fps,
            (width, height),
            cv2_module=cv2,
        )

        if out is None or not out.isOpened():
            cap.release()
            return (
                None,
                False,
                f"无法创建输出文件: {output_path}",
            )
        logger.info("Chunk %s: output codec=%s", chunk_id, selected_codec)

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
            except Exception as e:
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
                except Exception as exc:
                    logger.debug(
                        "Chunk %s progress report skipped: %s",
                        chunk_id,
                        exc,
                        exc_info=True,
                    )

        cap.release()
        out.release()

        logger.info(f"Chunk {chunk_id} completed: {processed_count}/{total_frames_in_chunk} frames")
        return (output_path, True, None)

    except Exception as e:
        error_msg = f"Chunk {chunk_id} error: {str(e)}"
        logger.error(error_msg)
        return (None, False, error_msg)
