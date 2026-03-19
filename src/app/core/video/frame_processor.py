import logging
from multiprocessing import queues, synchronize
from typing import Optional

from ..ai.ai_handler import AIHandler

# ============================================================================
# 进程池级别的模型缓存
# 使用 initializer 模式：每个进程只加载一次模型，后续复用
# ============================================================================
_worker_ai_handler: Optional[AIHandler] = None
_worker_ai_params: Optional[dict] = None


def init_worker_ai_handler(ai_params: dict) -> None:
    """
    进程池初始化函数 - 每个工作进程只调用一次

    在 ProcessPoolExecutor 创建时通过 initializer 参数调用，
    避免每次处理任务都重新加载模型（节省约 500MB×N 内存）

    Args:
        ai_params: AI 参数字典
    """
    global _worker_ai_handler, _worker_ai_params
    logger = logging.getLogger(__name__)

    try:
        logger.info(
            f"Initializing AI handler for worker process (PID: {__import__('os').getpid()})"
        )
        _worker_ai_params = ai_params
        _worker_ai_handler = AIHandler(None, ai_params)

        if not _worker_ai_handler.load_models():
            logger.error("Worker process failed to load AI models during initialization")
            _worker_ai_handler = None
        else:
            logger.info("Worker process AI handler initialized successfully")

    except Exception as e:
        logger.error(f"Worker process initialization error: {e}")
        _worker_ai_handler = None


def get_worker_ai_handler() -> Optional[AIHandler]:
    """获取当前进程的 AI 处理器实例"""
    return _worker_ai_handler


def frame_processor_worker(  # noqa: C901
    frame_queue: queues.Queue,
    result_queue: queues.Queue,
    ai_params: dict,
    config_dict: Optional[dict],
    stop_event: synchronize.Event,
    progress_queue: queues.Queue,
    worker_id: int,
) -> None:
    """
    帧处理工作进程

    Args:
        frame_queue: 帧队列
        result_queue: 结果队列
        ai_params: AI 参数（备用，优先使用初始化时的模型）
        config_dict: 配置字典
        stop_event: 停止事件
        progress_queue: 进度队列
        worker_id: 工作进程ID
    """
    global _worker_ai_handler
    logger = logging.getLogger(__name__)

    try:
        # 优先使用进程池初始化时加载的模型
        ai_handler = _worker_ai_handler

        # 降级处理：如果初始化时未加载模型，则在此处加载（兼容旧调用方式）
        if ai_handler is None:
            logger.warning(f"Worker {worker_id}: AI handler not pre-initialized, loading now...")
            ai_handler = AIHandler(None, ai_params)
            if not ai_handler.load_models():
                logger.error(f"Worker {worker_id} failed to load AI models")
                return
            _worker_ai_handler = ai_handler  # 缓存供后续使用

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

                processing_params = {
                    "auto_detect": ai_params.get("auto_detect", True),
                    "detection_sensitivity": ai_params.get("detection_sensitivity", 0.5),
                    "user_mask": ai_params.get("user_mask", None),
                }

                processed_frame, _ = ai_handler.process_frame(frame, processing_params)
                result_queue.put((frame_index, processed_frame), timeout=10)

                processed_count += 1

                if processed_count % 10 == 0:
                    try:
                        progress_queue.put(
                            {
                                "worker_id": worker_id,
                                "processed": processed_count,
                            },
                            block=False,
                        )
                    except Exception:
                        pass

            except Exception as e:  # noqa: BLE001
                if "timeout" not in str(e).lower():
                    logger.warning(f"Worker {worker_id} processing error: {e}")
                continue

        logger.info(f"Worker {worker_id} completed: {processed_count} frames processed")

    except Exception as e:  # noqa: BLE001
        logger.error(f"Worker {worker_id} fatal error: {e}")
