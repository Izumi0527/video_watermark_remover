"""
AI 核心模块（包入口）。

说明：
- `AIHandler`/`YOLOWatermarkDetector` 依赖 torch/YOLO 等重组件；
- 为避免测试收集或轻量脚本在导入 `app.core.ai` 包时立刻触发重依赖加载，
  这里采用惰性导入，仅在真正访问符号时再加载具体实现。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .ai_handler import AIHandler
    from .image_inpainter import ImageInpainter
    from .yolo_detector import YOLOWatermarkDetector

__all__ = ["AIHandler", "YOLOWatermarkDetector", "ImageInpainter"]


def __getattr__(name: str) -> Any:  # noqa: ANN401
    if name == "AIHandler":
        from .ai_handler import AIHandler

        return AIHandler
    if name == "YOLOWatermarkDetector":
        from .yolo_detector import YOLOWatermarkDetector

        return YOLOWatermarkDetector
    if name == "ImageInpainter":
        from .image_inpainter import ImageInpainter

        return ImageInpainter

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
