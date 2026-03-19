"""兼容层：帧写入 worker 已迁移到 `app.core.video.workers.frame_writer`。"""

from .workers.frame_writer import frame_writer_worker

__all__ = ["frame_writer_worker"]
