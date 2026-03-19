"""
视频处理核心模块（包入口）。

说明：
- `VideoProcessorThread` 依赖 PyQt6（QThread/信号），在无 GUI 依赖环境下直接导入会失败；
- 为了支持纯算法/工具模块（如 `path_utils`）在测试与脚本环境下使用，这里采用惰性导入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .thread import VideoProcessorThread

__all__ = ["VideoProcessorThread"]


def __getattr__(name: str) -> Any:  # noqa: ANN401
    if name == "VideoProcessorThread":
        from .thread import VideoProcessorThread  # 延迟导入

        return VideoProcessorThread

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
