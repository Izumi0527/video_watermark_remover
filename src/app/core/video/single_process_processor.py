"""兼容层：单进程视频处理已迁移到 `app.core.video.modes.single_process`。"""

from .modes.single_process import process_video_singleprocess
from .utils.path import build_temp_path

__all__ = ["process_video_singleprocess", "build_temp_path"]
