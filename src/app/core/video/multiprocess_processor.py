"""兼容层：多进程模式已迁移到 `app.core.video.modes.multiprocess`。"""

from concurrent.futures import ProcessPoolExecutor

from PyQt6.QtCore import QTimer

from .chunk_worker import init_chunk_worker_ai_handler, process_video_chunk
from .modes import multiprocess as _multiprocess
from .path_utils import build_temp_path


def _sync_runtime_overrides() -> None:
    _multiprocess.ProcessPoolExecutor = ProcessPoolExecutor
    _multiprocess.QTimer = QTimer
    _multiprocess.init_chunk_worker_ai_handler = init_chunk_worker_ai_handler
    _multiprocess.process_video_chunk = process_video_chunk
    _multiprocess.build_temp_path = build_temp_path


def _calculate_chunks(processor, total_frames: int, num_processes: int):
    return _multiprocess._calculate_chunks(processor, total_frames, num_processes)


def _check_progress_queue(processor, progress_queue, total_frames: int) -> None:
    _multiprocess._check_progress_queue(processor, progress_queue, total_frames)


def _merge_video_chunks(processor, chunk_paths, output_path: str) -> None:
    _multiprocess._merge_video_chunks(processor, chunk_paths, output_path)


def process_video_multiprocess(processor) -> None:
    _sync_runtime_overrides()
    _multiprocess.process_video_multiprocess(processor)


__all__ = [
    "ProcessPoolExecutor",
    "QTimer",
    "_calculate_chunks",
    "_check_progress_queue",
    "_merge_video_chunks",
    "process_video_multiprocess",
]
