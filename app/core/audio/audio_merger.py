#!/usr/bin/env python3
"""
音频合并模块

提供音频与视频合并的功能：
1. 将音频轨道合并到视频文件
2. 支持音频替换和覆盖
3. 保持视频质量不变
4. 灵活的编码参数设置

从 ffmpeg_audio_processor.py 重构拆分
作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

from .ffmpeg_detector import FFmpegDetector


class AudioMerger:
    """音频合并器"""

    def __init__(self, ffmpeg_detector: FFmpegDetector):
        """
        初始化音频合并器

        Args:
            ffmpeg_detector: FFmpeg检测器实例
        """
        self.detector = ffmpeg_detector
        self.logger = logging.getLogger(__name__)

        # 默认合并参数
        self.default_params = {
            "video_codec": "copy",  # 不重新编码视频
            "audio_codec": "aac",  # 音频编码为AAC
            "audio_bitrate": None,  # 保持原始比特率
            "sync_mode": "shortest",  # 以最短流为准
        }

    def merge_audio_video(
        self, video_path: str, audio_path: str, output_path: str, **params
    ) -> bool:
        """
        将音频合并到视频文件

        Args:
            video_path: 输入视频文件路径（无音频或音频需要替换）
            audio_path: 音频文件路径
            output_path: 输出视频文件路径
            **params: 合并参数
                - video_codec: 视频编解码器（默认copy）
                - audio_codec: 音频编解码器（默认aac）
                - audio_bitrate: 音频比特率（可选）
                - sync_mode: 同步模式（默认shortest）

        Returns:
            是否成功
        """
        if not self.detector.is_available():
            self.logger.error("FFmpeg not available for audio-video merging")
            return False

        ffmpeg_path = self.detector.get_ffmpeg_path()
        if not ffmpeg_path:
            self.logger.error("FFmpeg path is None")
            return False

        try:
            # 构建FFmpeg命令
            cmd = self._build_merge_command(
                ffmpeg_path, video_path, audio_path, output_path, params
            )

            # 执行合并
            self.logger.info(f"Merging audio and video: {output_path}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0 and os.path.exists(output_path):
                self.logger.info(f"Audio-video merge successful: {output_path}")
                return True
            else:
                self.logger.error(f"Audio-video merge failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Audio-video merge timeout")
            return False
        except Exception as e:
            self.logger.error(f"Error merging audio and video: {e}")
            return False

    def _build_merge_command(
        self,
        ffmpeg_path: str,
        video_path: str,
        audio_path: str,
        output_path: str,
        params: Dict[str, Any],
    ) -> List[str]:
        """
        构建音频视频合并命令

        Args:
            ffmpeg_path: FFmpeg可执行文件路径
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            params: 合并参数

        Returns:
            命令参数列表
        """
        # 合并默认参数和用户参数
        merge_params = {**self.default_params, **params}

        cmd = [
            ffmpeg_path,
            "-i",
            video_path,  # 视频输入
            "-i",
            audio_path,  # 音频输入
        ]

        # 添加视频编码参数
        if merge_params.get("video_codec"):
            cmd.extend(["-c:v", merge_params["video_codec"]])

        # 添加音频编码参数
        if merge_params.get("audio_codec"):
            cmd.extend(["-c:a", merge_params["audio_codec"]])

        if merge_params.get("audio_bitrate"):
            cmd.extend(["-b:a", merge_params["audio_bitrate"]])

        # 添加流映射
        cmd.extend(
            [
                "-map",
                "0:v:0",  # 映射第一个输入的视频流
                "-map",
                "1:a:0",  # 映射第二个输入的音频流
            ]
        )

        # 添加同步选项
        if merge_params.get("sync_mode") == "shortest":
            cmd.append("-shortest")

        # 添加输出选项
        cmd.extend(
            [
                "-y",  # 覆盖输出文件
                output_path,
            ]
        )

        return cmd

    def replace_audio(
        self, video_path: str, new_audio_path: str, output_path: str, **params
    ) -> bool:
        """
        替换视频中的音频轨道

        Args:
            video_path: 输入视频文件路径
            new_audio_path: 新音频文件路径
            output_path: 输出视频文件路径
            **params: 替换参数

        Returns:
            是否成功
        """
        # 替换音频实际上就是合并操作
        return self.merge_audio_video(video_path, new_audio_path, output_path, **params)

    def merge_multiple_audio(
        self, video_path: str, audio_paths: List[str], output_path: str, **params
    ) -> bool:
        """
        将多个音频轨道合并到视频

        Args:
            video_path: 输入视频文件路径
            audio_paths: 音频文件路径列表
            output_path: 输出视频文件路径
            **params: 合并参数

        Returns:
            是否成功
        """
        if not audio_paths:
            self.logger.error("No audio paths provided")
            return False

        if not self.detector.is_available():
            self.logger.error("FFmpeg not available")
            return False

        ffmpeg_path = self.detector.get_ffmpeg_path()
        if not ffmpeg_path:
            return False

        try:
            # 构建多音频合并命令
            cmd = self._build_multi_audio_command(
                ffmpeg_path, video_path, audio_paths, output_path, params
            )

            # 执行合并
            self.logger.info(f"Merging video with {len(audio_paths)} audio tracks")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0 and os.path.exists(output_path):
                self.logger.info(f"Multi-audio merge successful: {output_path}")
                return True
            else:
                self.logger.error(f"Multi-audio merge failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error merging multiple audio tracks: {e}")
            return False

    def _build_multi_audio_command(
        self,
        ffmpeg_path: str,
        video_path: str,
        audio_paths: List[str],
        output_path: str,
        params: Dict[str, Any],
    ) -> List[str]:
        """构建多音频合并命令"""
        merge_params = {**self.default_params, **params}

        cmd = [ffmpeg_path, "-i", video_path]

        # 添加所有音频输入
        for audio_path in audio_paths:
            cmd.extend(["-i", audio_path])

        # 添加编码参数
        if merge_params.get("video_codec"):
            cmd.extend(["-c:v", merge_params["video_codec"]])

        if merge_params.get("audio_codec"):
            cmd.extend(["-c:a", merge_params["audio_codec"]])

        # 映射视频流
        cmd.extend(["-map", "0:v:0"])

        # 映射所有音频流
        for i in range(len(audio_paths)):
            cmd.extend(["-map", f"{i+1}:a:0"])

        # 添加输出选项
        if merge_params.get("sync_mode") == "shortest":
            cmd.append("-shortest")

        cmd.extend(["-y", output_path])

        return cmd

    def get_supported_video_codecs(self) -> List[str]:
        """
        获取支持的视频编解码器列表

        Returns:
            支持的编解码器列表
        """
        return ["copy", "libx264", "libx265", "libvpx", "libvpx-vp9"]

    def get_supported_audio_codecs(self) -> List[str]:
        """
        获取支持的音频编解码器列表

        Returns:
            支持的编解码器列表
        """
        return ["aac", "mp3", "ac3", "flac", "copy"]
