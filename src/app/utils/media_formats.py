#!/usr/bin/env python3
"""
媒体文件格式常量

统一维护当前真正支持处理的图片/视频扩展名，避免 UI 过滤器、
预览判断与处理内核出现漂移。
"""

IMAGE_FILE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")
VIDEO_FILE_EXTENSIONS = (".mp4", ".avi", ".mkv", ".mov")

__all__ = ["IMAGE_FILE_EXTENSIONS", "VIDEO_FILE_EXTENSIONS"]
