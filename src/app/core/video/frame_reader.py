"""兼容层：帧读取 worker 已迁移到 `app.core.video.workers.frame_reader`。"""

from .workers.frame_reader import (
    extract_video_first_frame,
    extract_video_frame_at,
    frame_reader_worker,
)

__all__ = ["extract_video_first_frame", "extract_video_frame_at", "frame_reader_worker"]
