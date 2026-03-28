from __future__ import annotations

import logging
from multiprocessing import queues, synchronize
from typing import Any, Optional

from ..runtime_guard import is_resource_exhaustion_error

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
_worker_ai_handler: Optional[Any] = None
_worker_ai_params: Optional[dict] = None


def init_worker_ai_handler(ai_params: dict) -> None:
    """进程池初始化函数 - 每个工作进程只调用一次。"""
    global _worker_ai_handler, _worker_ai_params
    logger = logging.getLogger(__name__)

    try:
        logger.info(
            f"Initializing AI handler for worker process (PID: {__import__('os').getpid()})"
        )
        _worker_ai_params = ai_params
        ai_handler_class = _resolve_ai_handler_class()
        _worker_ai_handler = ai_handler_class(None, ai_params)

        if not _worker_ai_handler.load_models():
            logger.error("Worker process failed to load AI models during initialization")
            _worker_ai_handler = None
        else:
            logger.info("Worker process AI handler initialized successfully")

    except Exception as e:
        logger.error(f"Worker process initialization error: {e}")
        _worker_ai_handler = None


def get_worker_ai_handler() -> Optional[Any]:
    """获取当前进程的 AI 处理器实例。"""
    return _worker_ai_handler


def _build_processing_params(ai_params: dict) -> dict:
    """构建帧处理参数。"""
    return {
        "auto_detect": ai_params.get("auto_detect", True),
        "detection_sensitivity": ai_params.get("detection_sensitivity", 0.5),
        "user_mask": ai_params.get("user_mask", None),
    }


def _is_timeout_error(error: Exception) -> bool:
    """判断异常是否为超时类错误。"""
    return "timeout" in str(error).lower()


def _report_progress_non_blocking(
    progress_queue: queues.Queue,
    worker_id: int,
    processed_count: int,
    logger: logging.Logger,
) -> None:
    """非阻塞上报进度，失败时降级为调试日志。"""
    if processed_count % 10 != 0:
        return

    try:
        progress_queue.put(
            {
                "worker_id": worker_id,
                "processed": processed_count,
            },
            block=False,
        )
    except Exception as exc:
        logger.debug("Worker %s progress report skipped: %s", worker_id, exc, exc_info=True)


def _get_or_init_worker_ai_handler(
    ai_params: dict,
    worker_id: int,
    logger: logging.Logger,
) -> Optional[Any]:
    """获取或初始化当前进程 AI 处理器。"""
    global _worker_ai_handler

    ai_handler = _worker_ai_handler
    if ai_handler is not None:
        return ai_handler

    logger.warning(f"Worker {worker_id}: AI handler not pre-initialized, loading now...")
    ai_handler_class = _resolve_ai_handler_class()
    ai_handler = ai_handler_class(None, ai_params)
    if not ai_handler.load_models():
        logger.error(f"Worker {worker_id} failed to load AI models")
        return None

    _worker_ai_handler = ai_handler
    return ai_handler


def frame_processor_worker(
    frame_queue: queues.Queue,
    result_queue: queues.Queue,
    ai_params: dict,
    config_dict: Optional[dict],
    stop_event: synchronize.Event,
    progress_queue: queues.Queue,
    worker_id: int,
) -> None:
    """帧处理工作进程。"""
    logger = logging.getLogger(__name__)

    try:
        ai_handler = _get_or_init_worker_ai_handler(ai_params, worker_id, logger)
        if ai_handler is None:
            return

        logger.info(
            f"Worker {worker_id} started (using {'pre-initialized' if _worker_ai_handler else 'newly loaded'} AI handler)"
        )
        processed_count = 0

        while not stop_event.is_set():
            try:
                item = frame_queue.get(timeout=1)

                if item is None:
                    frame_queue.put(None)
                    logger.info(f"Worker {worker_id} received end signal")
                    break

                frame_index, frame = item
                processed_frame, _ = ai_handler.process_frame(
                    frame, _build_processing_params(ai_params)
                )
                result_queue.put((frame_index, processed_frame), timeout=10)

                processed_count += 1
                _report_progress_non_blocking(progress_queue, worker_id, processed_count, logger)

            except Exception as e:
                if is_resource_exhaustion_error(e):
                    stop_event.set()
                    logger.error("Worker %s resource exhaustion: %r", worker_id, e)
                    break
                if not _is_timeout_error(e):
                    logger.warning(f"Worker {worker_id} processing error: {e}")
                continue

        logger.info(f"Worker {worker_id} completed: {processed_count} frames processed")

    except Exception as e:
        logger.error(f"Worker {worker_id} fatal error: {e}")
