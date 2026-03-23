#!/usr/bin/env python3
"""
文件对话框过滤器常量

统一维护 UI 层常用的文件过滤器，避免不同入口行为不一致。
"""

from ...utils import IMAGE_FILE_EXTENSIONS, VIDEO_FILE_EXTENSIONS


def _build_filter_segment(label: str, extensions: tuple[str, ...]) -> str:
    pattern = " ".join(f"*{ext}" for ext in extensions)
    return f"{label} ({pattern})"


MEDIA_IMPORT_FILTER = (
    f"{_build_filter_segment('支持的文件', VIDEO_FILE_EXTENSIONS + IMAGE_FILE_EXTENSIONS)};;"
    f"{_build_filter_segment('视频文件', VIDEO_FILE_EXTENSIONS)};;"
    f"{_build_filter_segment('图片文件', IMAGE_FILE_EXTENSIONS)};;"
    "所有文件 (*)"
)

__all__ = ["MEDIA_IMPORT_FILTER"]
