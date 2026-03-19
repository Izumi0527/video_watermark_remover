"""兼容层：背压控制工具已迁移到 `app.core.video.utils.backpressure`。"""

from .utils.backpressure import AdaptiveBackpressure, BackpressureController

__all__ = ["BackpressureController", "AdaptiveBackpressure"]
