#!/usr/bin/env python3
"""
FFmpeg音频处理器 - 重构版

提供完整的音频处理工作流程，使用模块化架构：
- ffmpeg_detector: FFmpeg检测和管理
- video_info_extractor: 视频信息提取
- audio_extractor: 音频提取
- audio_merger: 音频视频合并

重构完成日期: 2025-09-06
作者: Claude Code Assistant
版本: v1.0 (重构版)
"""

import logging
import os
import shutil
from typing import Any, Dict, List, Optional

from .audio_extractor import AudioExtractor
from .audio_merger import AudioMerger
from .ffmpeg_detector import FFmpegDetector
from .video_info_extractor import VideoInfoExtractor


class FFmpegAudioProcessor:
    """
    FFmpeg音频处理器 - 重构版

    负责视频音频轨道的提取、合并和处理，使用模块化架构
    """

    def __init__(self, config=None):
        """
        初始化音频处理器

        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化模块化组件
        self.detector = FFmpegDetector(config)
        self.info_extractor = VideoInfoExtractor(self.detector)
        self.audio_extractor = AudioExtractor(self.detector)
        self.audio_merger = AudioMerger(self.detector)

        # 临时文件管理（来自各个模块）
        self.temp_files: List[str] = []

        self.logger.info(
            f"FFmpegAudioProcessor initialized (refactored) - FFmpeg: {self.detector.is_available()}"
        )

    def is_available(self) -> bool:
        """
        检查FFmpeg是否可用

        Returns:
            FFmpeg是否可用
        """
        return self.detector.is_available()

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频文件信息

        Args:
            video_path: 视频文件路径

        Returns:
            视频信息字典
        """
        return self.info_extractor.get_video_info(video_path)

    def extract_audio(
        self, video_path: str, output_path: Optional[str] = None, **params
    ) -> Optional[str]:
        """
        从视频文件提取音频

        Args:
            video_path: 输入视频文件路径
            output_path: 输出音频文件路径（可选）
            **params: 音频提取参数

        Returns:
            音频文件路径，失败时返回None
        """
        result = self.audio_extractor.extract_audio(video_path, output_path, **params)

        # 如果是临时文件，加入清理列表
        if result and output_path is None:
            self.temp_files.append(result)

        return result

    def merge_audio_video(
        self, video_path: str, audio_path: str, output_path: str, **params
    ) -> bool:
        """
        将音频合并到视频文件

        Args:
            video_path: 输入视频文件路径
            audio_path: 音频文件路径
            output_path: 输出视频文件路径
            **params: 合并参数

        Returns:
            是否成功
        """
        return self.audio_merger.merge_audio_video(video_path, audio_path, output_path, **params)

    def process_video_with_audio_preservation(
        self, original_video_path: str, processed_video_path: str, final_output_path: str
    ) -> bool:
        """
        处理视频并保持原始音频 - 主要工作流程

        这是主要的工作流程：
        1. 检查原视频是否有音频
        2. 从原视频提取音频
        3. 将音频合并到处理后的视频

        Args:
            original_video_path: 原始视频文件路径
            processed_video_path: 处理后的视频文件路径（无音频）
            final_output_path: 最终输出文件路径

        Returns:
            是否成功
        """
        if not self.is_available():
            return self._fallback_copy(
                processed_video_path,
                final_output_path,
                "FFmpeg not available, skipping audio preservation",
            )

        try:
            # 检查原视频是否有音频
            if not self._check_original_audio(original_video_path):
                return self._fallback_copy(
                    processed_video_path,
                    final_output_path,
                    "Original video has no audio, copying processed video directly",
                )

            # 步骤1：提取音频
            audio_path = self._extract_original_audio(original_video_path)
            if not audio_path:
                return self._fallback_copy(
                    processed_video_path, final_output_path, "Failed to extract audio"
                )

            # 步骤2：合并音频和处理后的视频
            success = self._merge_audio_to_processed_video(
                processed_video_path, audio_path, final_output_path
            )

            if not success:
                return self._fallback_copy(
                    processed_video_path, final_output_path, "Failed to merge audio and video"
                )

            self.logger.info("Audio preservation completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error in audio preservation workflow: {e}")
            return self._fallback_copy(
                processed_video_path, final_output_path, f"Error in workflow: {e}"
            )

    def _check_original_audio(self, original_video_path: str) -> bool:
        """检查原视频是否有音频"""
        video_info = self.info_extractor.get_video_info(original_video_path)
        return not video_info.get("error") and video_info.get("has_audio", False)

    def _extract_original_audio(self, original_video_path: str) -> Optional[str]:
        """从原视频提取音频"""
        self.logger.info("Step 1: Extracting audio from original video")
        return self.audio_extractor.extract_audio(original_video_path)

    def _merge_audio_to_processed_video(
        self, processed_video_path: str, audio_path: str, final_output_path: str
    ) -> bool:
        """将音频合并到处理后的视频，并重新编码为 H.264"""
        self.logger.info("Step 2: Merging audio with processed video and re-encoding to H.264")
        # 重新编码为 H.264 以确保最佳兼容性
        # OpenCV 使用 mp4v 编码器写入的视频兼容性较差，需要重新编码
        return self.audio_merger.merge_audio_video(
            processed_video_path,
            audio_path,
            final_output_path,
            video_codec="libx264",  # 使用 H.264 编码器
            audio_codec="aac",  # AAC 音频编码器
        )

    def _fallback_copy(self, source_path: str, dest_path: str, reason: str) -> bool:
        """回退方案：重新编码视频为 H.264（即使没有音频也要重新编码以确保兼容性）"""
        self.logger.info(f"{reason} - Re-encoding video to H.264 for compatibility")

        if not self.detector.is_available():
            # FFmpeg 不可用，只能直接复制
            self.logger.warning("FFmpeg not available, copying without re-encoding")
            try:
                shutil.copy2(source_path, dest_path)
                return True
            except Exception as e:
                self.logger.error(f"Error copying video: {e}")
                return False

        try:
            # 使用 FFmpeg 重新编码为 H.264
            ffmpeg_path = self.detector.get_ffmpeg_path()
            cmd = [
                ffmpeg_path,
                "-i",
                source_path,
                "-c:v",
                "libx264",  # H.264 视频编码器
                "-preset",
                "medium",  # 编码速度/质量平衡
                "-crf",
                "23",  # 质量参数 (18-28, 越小质量越高)
                "-c:a",
                "copy",  # 如果有音频，直接复制（虽然 fallback 通常是无音频的）
                "-y",  # 覆盖输出文件
                dest_path,
            ]

            self.logger.debug(f"Re-encoding command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace"
            )

            if result.returncode == 0:
                self.logger.info("Video re-encoded to H.264 successfully")
                return True
            else:
                self.logger.error(f"Re-encoding failed: {result.stderr}")
                # 重新编码失败，尝试直接复制
                self.logger.warning("Falling back to direct copy")
                shutil.copy2(source_path, dest_path)
                return True

        except subprocess.TimeoutExpired:
            self.logger.error("Re-encoding timeout")
            return False
        except Exception as e:
            self.logger.error(f"Error re-encoding video: {e}")
            try:
                shutil.copy2(source_path, dest_path)
                return True
            except Exception as copy_error:
                self.logger.error(f"Error copying video: {copy_error}")
                return False

    def cleanup_temp_files(self):
        """清理临时文件"""
        # 清理本类的临时文件
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up {temp_file}: {e}")

        self.temp_files.clear()

        # 清理模块的临时文件
        self.audio_extractor.cleanup_temp_files()

    def get_ffmpeg_version(self) -> Optional[str]:
        """获取FFmpeg版本信息"""
        return self.detector.get_version_info()

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的格式信息"""
        return {
            "audio_codecs": self.audio_extractor.get_supported_codecs(),
            "video_codecs": self.audio_merger.get_supported_video_codecs(),
            "merge_audio_codecs": self.audio_merger.get_supported_audio_codecs(),
        }

    def __del__(self):
        """析构函数，清理临时文件"""
        self.cleanup_temp_files()


if __name__ == "__main__":
    """测试代码"""
    # 创建测试实例
    processor = FFmpegAudioProcessor()

    print("=== FFmpeg音频处理器重构版测试 ===")
    print(f"FFmpeg available: {processor.is_available()}")

    if processor.is_available():
        version = processor.get_version_info()
        print(f"FFmpeg version: {version}")

        formats = processor.get_supported_formats()
        print(f"Supported audio codecs: {formats['audio_codecs']}")

        # 测试获取视频信息（如果有测试视频的话）
        test_video = "test_video.mp4"  # 替换为实际测试视频路径
        if os.path.exists(test_video):
            info = processor.get_video_info(test_video)
            print(f"Video info: {info}")

    print("\n模块化架构包含:")
    print("  - FFmpegDetector: FFmpeg检测和管理")
    print("  - VideoInfoExtractor: 视频信息提取")
    print("  - AudioExtractor: 音频提取功能")
    print("  - AudioMerger: 音频视频合并")
    print("✅ 重构版本测试完成")

    # 清理
    processor.cleanup_temp_files()
