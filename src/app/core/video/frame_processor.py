"""兼容层：帧处理 worker 已迁移到 `app.core.video.workers.frame_processor`。"""

from multiprocessing import queues, synchronize
from typing import Optional

from .workers import frame_processor as _frame_processor

AIHandler = _frame_processor.AIHandler


def init_worker_ai_handler(ai_params: dict) -> None:
    _frame_processor.AIHandler = AIHandler
    _frame_processor.init_worker_ai_handler(ai_params)


def get_worker_ai_handler() -> Optional[AIHandler]:
    return _frame_processor.get_worker_ai_handler()


def frame_processor_worker(
    frame_queue: queues.Queue,
    result_queue: queues.Queue,
    ai_params: dict,
    config_dict: Optional[dict],
    stop_event: synchronize.Event,
    progress_queue: queues.Queue,
    worker_id: int,
) -> None:
    _frame_processor.AIHandler = AIHandler
    _frame_processor.frame_processor_worker(
        frame_queue=frame_queue,
        result_queue=result_queue,
        ai_params=ai_params,
        config_dict=config_dict,
        stop_event=stop_event,
        progress_queue=progress_queue,
        worker_id=worker_id,
    )


__all__ = ["AIHandler", "init_worker_ai_handler", "get_worker_ai_handler", "frame_processor_worker"]
