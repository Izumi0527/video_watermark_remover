#!/usr/bin/env python3
"""
视频信息提取模块

提供视频文件信息获取功能：
1. 使用ffprobe获取详细视频信息
2. 解析音频和视频流信息
3. 检测编解码器和格式
4. 获取时长和质量参数

从 ffmpeg_audio_processor.py 重构拆分
作者: 
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import json
import logging
import subprocess
from typing import Any, Dict, Optional

from .ffmpeg_detector import FFmpegDetector


class VideoInfoExtractor:
    """视频信息提取器"""

    def __init__(self, ffmpeg_detector: FFmpegDetector):
        """
        初始化视频信息提取器

        Args:
            ffmpeg_detector: FFmpeg检测器实例
        """
        self.detector = ffmpeg_detector
        self.logger = logging.getLogger(__name__)

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频文件信息

        Args:
            video_path: 视频文件路径

        Returns:
            视频信息字典
        """
        if not self.detector.is_available():
            return {"error": "FFmpeg not available"}

        ffprobe_path = self.detector.get_ffprobe_path()
        if not ffprobe_path:
            return {"error": "ffprobe not available"}

        try:
            # 构建ffprobe命令
            cmd = self._build_ffprobe_command(ffprobe_path, video_path)

            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return self._parse_ffprobe_output(result.stdout)
            else:
                return {"error": f"ffprobe failed: {result.stderr}"}

        except subprocess.TimeoutExpired:
            return {"error": "ffprobe timeout"}
        except Exception as e:
            self.logger.error(f"Error getting video info: {e}")
            return {"error": str(e)}

    def _build_ffprobe_command(self, ffprobe_path: str, video_path: str) -> list:
        """
        构建ffprobe命令

        Args:
            ffprobe_path: ffprobe可执行文件路径
            video_path: 视频文件路径

        Returns:
            命令参数列表
        """
        return [
            ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]

    def _parse_ffprobe_output(self, output: str) -> Dict[str, Any]:
        """
        解析ffprobe输出

        Args:
            output: ffprobe的JSON输出

        Returns:
            解析后的视频信息
        """
        try:
            info = json.loads(output)

            # 初始化视频信息结构
            video_info = {
                "has_video": False,
                "has_audio": False,
                "duration": 0.0,
                "video_codec": None,
                "audio_codec": None,
                "audio_channels": 0,
                "audio_sample_rate": 0,
                "video_width": 0,
                "video_height": 0,
                "video_fps": 0.0,
                "bit_rate": 0,
                "file_size": 0,
            }

            # 解析流信息
            self._parse_streams(info.get("streams", []), video_info)

            # 解析格式信息
            self._parse_format(info.get("format", {}), video_info)

            return video_info

        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse ffprobe output: {e}"}

    def _parse_streams(self, streams: list, video_info: Dict[str, Any]) -> None:
        """
        解析流信息

        Args:
            streams: 流信息列表
            video_info: 视频信息字典
        """
        for stream in streams:
            codec_type = stream.get("codec_type")

            if codec_type == "video":
                self._parse_video_stream(stream, video_info)
            elif codec_type == "audio":
                self._parse_audio_stream(stream, video_info)

    def _parse_video_stream(self, stream: Dict[str, Any], video_info: Dict[str, Any]) -> None:
        """
        解析视频流信息

        Args:
            stream: 视频流信息
            video_info: 视频信息字典
        """
        video_info["has_video"] = True
        video_info["video_codec"] = stream.get("codec_name")
        video_info["video_width"] = int(stream.get("width", 0))
        video_info["video_height"] = int(stream.get("height", 0))

        # 解析帧率
        fps_str = stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            try:
                num, den = fps_str.split("/")
                if int(den) != 0:
                    video_info["video_fps"] = float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                pass

    def _parse_audio_stream(self, stream: Dict[str, Any], video_info: Dict[str, Any]) -> None:
        """
        解析音频流信息

        Args:
            stream: 音频流信息
            video_info: 视频信息字典
        """
        video_info["has_audio"] = True
        video_info["audio_codec"] = stream.get("codec_name")
        video_info["audio_channels"] = int(stream.get("channels", 0))
        video_info["audio_sample_rate"] = int(stream.get("sample_rate", 0))

    def _parse_format(self, format_info: Dict[str, Any], video_info: Dict[str, Any]) -> None:
        """
        解析格式信息

        Args:
            format_info: 格式信息
            video_info: 视频信息字典
        """
        video_info["duration"] = float(format_info.get("duration", 0))
        video_info["bit_rate"] = int(format_info.get("bit_rate", 0))
        video_info["file_size"] = int(format_info.get("size", 0))

    def has_audio_stream(self, video_path: str) -> bool:
        """
        快速检测视频是否包含音频流

        Args:
            video_path: 视频文件路径

        Returns:
            是否包含音频
        """
        info = self.get_video_info(video_path)
        return info.get("has_audio", False) and not info.get("error")

    def get_duration(self, video_path: str) -> float:
        """
        获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            视频时长（秒）
        """
        info = self.get_video_info(video_path)
        return info.get("duration", 0.0)

    def get_audio_codec(self, video_path: str) -> Optional[str]:
        """
        获取音频编解码器

        Args:
            video_path: 视频文件路径

        Returns:
            音频编解码器名称
        """
        info = self.get_video_info(video_path)
        return info.get("audio_codec")

    def get_video_codec(self, video_path: str) -> Optional[str]:
        """
        获取视频编解码器

        Args:
            video_path: 视频文件路径

        Returns:
            视频编解码器名称
        """
        info = self.get_video_info(video_path)
        return info.get("video_codec")
