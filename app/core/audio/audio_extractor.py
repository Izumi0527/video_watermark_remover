#!/usr/bin/env python3
"""
音频提取模块

提供从视频文件提取音频的功能：
1. 使用FFmpeg从视频提取音频
2. 支持多种音频格式和质量设置
3. 临时文件管理
4. 提取参数自定义

从 ffmpeg_audio_processor.py 重构拆分
作者: Izumi0527
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from .ffmpeg_detector import FFmpegDetector


class AudioExtractor:
    """音频提取器"""

    def __init__(self, ffmpeg_detector: FFmpegDetector):
        """
        初始化音频提取器

        Args:
            ffmpeg_detector: FFmpeg检测器实例
        """
        self.detector = ffmpeg_detector
        self.logger = logging.getLogger(__name__)
        self.temp_files: List[str] = []

        # 默认提取参数
        self.default_params = {
            "audio_codec": "aac",
            "audio_bitrate": "128k",
            "audio_channels": None,  # 保持原始声道数
            "audio_sample_rate": None,  # 保持原始采样率
        }

    def extract_audio(
        self, video_path: str, output_path: Optional[str] = None, **params
    ) -> Optional[str]:
        """
        从视频文件提取音频

        Args:
            video_path: 输入视频文件路径
            output_path: 输出音频文件路径（可选）
            **params: 音频提取参数
                - audio_codec: 音频编解码器（默认aac）
                - audio_bitrate: 音频比特率（默认128k）
                - audio_channels: 声道数（可选）
                - audio_sample_rate: 采样率（可选）

        Returns:
            音频文件路径，失败时返回None
        """
        if not self.detector.is_available():
            self.logger.error("FFmpeg not available for audio extraction")
            return None

        ffmpeg_path = self.detector.get_ffmpeg_path()
        if not ffmpeg_path:
            self.logger.error("FFmpeg path is None")
            return None

        try:
            # 生成输出路径
            if output_path is None:
                output_path = self._generate_temp_audio_path(params.get("audio_codec", "aac"))
                self.temp_files.append(output_path)

            # 构建FFmpeg命令
            cmd = self._build_extract_command(ffmpeg_path, video_path, output_path, params)

            # 执行提取
            self.logger.info(f"Extracting audio from {video_path}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0 and os.path.exists(output_path):
                self.logger.info(f"Audio extracted successfully: {output_path}")
                return output_path
            else:
                self.logger.error(f"Audio extraction failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            self.logger.error("Audio extraction timeout")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting audio: {e}")
            return None

    def _generate_temp_audio_path(self, codec: str) -> str:
        """
        生成临时音频文件路径

        Args:
            codec: 音频编解码器

        Returns:
            临时音频文件路径
        """
        temp_dir = tempfile.gettempdir()

        # 根据编解码器确定文件扩展名
        extension = self._get_audio_extension(codec)
        filename = f"temp_audio_{id(self)}.{extension}"

        return os.path.join(temp_dir, filename)

    def _get_audio_extension(self, codec: str) -> str:
        """
        根据编解码器获取文件扩展名

        Args:
            codec: 音频编解码器

        Returns:
            文件扩展名
        """
        codec_extensions = {
            "aac": "aac",
            "mp3": "mp3",
            "wav": "wav",
            "flac": "flac",
            "ogg": "ogg",
        }

        return codec_extensions.get(codec.lower(), "aac")

    def _build_extract_command(
        self, ffmpeg_path: str, video_path: str, output_path: str, params: Dict[str, Any]
    ) -> List[str]:
        """
        构建音频提取命令

        Args:
            ffmpeg_path: FFmpeg可执行文件路径
            video_path: 输入视频路径
            output_path: 输出音频路径
            params: 提取参数

        Returns:
            命令参数列表
        """
        # 合并默认参数和用户参数
        extract_params = {**self.default_params, **params}

        cmd = [
            ffmpeg_path,
            "-i",
            video_path,
            "-vn",  # 不包含视频
        ]

        # 添加音频编码参数
        if extract_params.get("audio_codec"):
            cmd.extend(["-acodec", extract_params["audio_codec"]])

        if extract_params.get("audio_bitrate"):
            cmd.extend(["-ab", extract_params["audio_bitrate"]])

        if extract_params.get("audio_channels"):
            cmd.extend(["-ac", str(extract_params["audio_channels"])])

        if extract_params.get("audio_sample_rate"):
            cmd.extend(["-ar", str(extract_params["audio_sample_rate"])])

        # 添加输出文件和选项
        cmd.extend(
            [
                "-y",  # 覆盖输出文件
                output_path,
            ]
        )

        return cmd

    def extract_audio_segment(
        self,
        video_path: str,
        start_time: float,
        duration: float,
        output_path: Optional[str] = None,
        **params,
    ) -> Optional[str]:
        """
        提取视频的音频片段

        Args:
            video_path: 输入视频文件路径
            start_time: 开始时间（秒）
            duration: 持续时间（秒）
            output_path: 输出音频文件路径（可选）
            **params: 音频提取参数

        Returns:
            音频文件路径，失败时返回None
        """
        if not self.detector.is_available():
            self.logger.error("FFmpeg not available for audio segment extraction")
            return None

        # 添加时间参数
        time_params = {
            **params,
            "start_time": start_time,
            "duration": duration,
        }

        return self.extract_audio(video_path, output_path, **time_params)

    def _build_segment_command(
        self, ffmpeg_path: str, video_path: str, output_path: str, params: Dict[str, Any]
    ) -> List[str]:
        """构建音频片段提取命令"""
        cmd = self._build_extract_command(ffmpeg_path, video_path, output_path, params)

        # 在输入文件后添加时间参数
        if params.get("start_time") is not None:
            # 找到输入文件参数位置
            input_index = cmd.index(video_path)
            # 在输入文件前添加起始时间
            cmd.insert(input_index, str(params["start_time"]))
            cmd.insert(input_index, "-ss")

        if params.get("duration") is not None:
            # 在输出文件前添加持续时间
            output_index = cmd.index(output_path)
            cmd.insert(output_index, str(params["duration"]))
            cmd.insert(output_index, "-t")

        return cmd

    def get_supported_codecs(self) -> List[str]:
        """
        获取支持的音频编解码器列表

        Returns:
            支持的编解码器列表
        """
        return ["aac", "mp3", "wav", "flac", "ogg"]

    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up {temp_file}: {e}")

        self.temp_files.clear()

    def __del__(self):
        """析构函数，清理临时文件"""
        self.cleanup_temp_files()
