import logging
from multiprocessing import queues, synchronize
from typing import Optional

from ..ai.ai_handler import AIHandler


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
        ai_params: AI 参数
        config_dict: 配置字典
        stop_event: 停止事件
        progress_queue: 进度队列
        worker_id: 工作进程ID
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Worker {worker_id} loading AI models...")
        ai_handler = AIHandler(None, ai_params)
        if not ai_handler.load_models():
            logger.error(f"Worker {worker_id} failed to load AI models")
            return

        logger.info(f"Worker {worker_id} started")
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
