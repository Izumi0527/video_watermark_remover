"""兼容层：音频 worker 已迁移到 `app.core.video.workers.audio`。"""

from .workers.audio import async_audio_extractor

__all__ = ["async_audio_extractor"]
