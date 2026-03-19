"""兼容层：流水线模式已迁移到 `app.core.video.modes.pipeline`。"""

from concurrent.futures import ProcessPoolExecutor

from PyQt6.QtCore import QTimer

from .audio_tasks import async_audio_extractor
from .frame_processor import frame_processor_worker, init_worker_ai_handler
from .frame_reader import frame_reader_worker
from .frame_writer import frame_writer_worker
from .modes import pipeline as _pipeline
from .path_utils import build_temp_path


def _sync_runtime_overrides() -> None:
    _pipeline.ProcessPoolExecutor = ProcessPoolExecutor
    _pipeline.QTimer = QTimer
    _pipeline.async_audio_extractor = async_audio_extractor
    _pipeline.frame_processor_worker = frame_processor_worker
    _pipeline.init_worker_ai_handler = init_worker_ai_handler
    _pipeline.frame_reader_worker = frame_reader_worker
    _pipeline.frame_writer_worker = frame_writer_worker
    _pipeline.build_temp_path = build_temp_path


def _create_manager_queue(manager, maxsize=None):
    return _pipeline._create_manager_queue(manager, maxsize=maxsize)


def _calculate_queue_sizes(processor):
    return _pipeline._calculate_queue_sizes(processor)


def _check_pipeline_progress(processor, progress_queue, total_frames: int) -> None:
    _pipeline._check_pipeline_progress(processor, progress_queue, total_frames)


def process_video_pipeline(processor) -> None:
    _sync_runtime_overrides()
    _pipeline.process_video_pipeline(processor)


__all__ = [
    "ProcessPoolExecutor",
    "QTimer",
    "_create_manager_queue",
    "_calculate_queue_sizes",
    "_check_pipeline_progress",
    "process_video_pipeline",
]
