"""兼容层：分块 worker 已迁移到 `app.core.video.workers.chunk`。"""

from typing import Optional, Tuple

import multiprocessing

from .workers import chunk as _chunk

AIHandler = _chunk.AIHandler


def init_chunk_worker_ai_handler(ai_params: dict) -> None:
    _chunk.AIHandler = AIHandler
    _chunk.init_chunk_worker_ai_handler(ai_params)


def get_chunk_worker_ai_handler():
    return _chunk.get_chunk_worker_ai_handler()


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
    _chunk.AIHandler = AIHandler
    return _chunk.process_video_chunk(
        video_path=video_path,
        start_frame=start_frame,
        end_frame=end_frame,
        output_path=output_path,
        ai_params=ai_params,
        config_dict=config_dict,
        progress_queue=progress_queue,
        stop_event=stop_event,
        chunk_id=chunk_id,
    )


__all__ = [
    "AIHandler",
    "init_chunk_worker_ai_handler",
    "get_chunk_worker_ai_handler",
    "process_video_chunk",
]
