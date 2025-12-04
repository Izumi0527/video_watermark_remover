#!/usr/bin/env python3
"""
FFmpeg检测和管理模块

提供FFmpeg可执行文件的检测和管理功能：
1. 自动检测系统中的FFmpeg
2. 验证FFmpeg功能可用性
3. 跨平台路径管理
4. 配置文件支持

从 ffmpeg_audio_processor.py 重构拆分
作者:
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import logging
import os
import shutil
import subprocess
from typing import List, Optional


class FFmpegDetector:
    """FFmpeg检测和管理器"""

    def __init__(self, config=None):
        """
        初始化FFmpeg检测器

        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.ffmpeg_path: Optional[str] = None

        # 自动检测FFmpeg
        self._detect_ffmpeg()

    def _detect_ffmpeg(self) -> None:
        """检测FFmpeg可执行文件路径"""
        self.ffmpeg_path = self._find_ffmpeg_executable()

        if self.ffmpeg_path:
            self.logger.info(f"FFmpeg detected at: {self.ffmpeg_path}")
        else:
            self.logger.warning("FFmpeg not found in system")

    def _find_ffmpeg_executable(self) -> Optional[str]:
        """
        查找FFmpeg可执行文件

        Returns:
            FFmpeg可执行文件路径，如果未找到则返回None
        """
        # 1. 从配置文件检查
        config_path = self._get_config_ffmpeg_path()
        if config_path and self._test_ffmpeg_executable(config_path):
            return config_path

        # 2. 检查系统PATH中的ffmpeg
        system_path = self._check_system_path()
        if system_path:
            return system_path

        # 3. 检查常见安装路径
        common_path = self._check_common_paths()
        if common_path:
            return common_path

        self.logger.warning("FFmpeg not found in system PATH or common locations")
        return None

    def _get_config_ffmpeg_path(self) -> Optional[str]:
        """从配置文件获取FFmpeg路径"""
        if not self.config:
            return None

        try:
            config_path = self.config.get("Paths", "ffmpeg_path", fallback=None)
            if config_path and isinstance(config_path, str):
                return str(config_path)
        except Exception as e:
            self.logger.debug(f"Failed to read ffmpeg_path from config: {e}")

        return None

    def _check_system_path(self) -> Optional[str]:
        """检查系统PATH中的FFmpeg"""
        try:
            # Use shutil.which to find the full path (safer than partial path)
            ffmpeg_cmd = shutil.which("ffmpeg")
            if not ffmpeg_cmd:
                return None

            result = subprocess.run(
                [ffmpeg_cmd, "-version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return "ffmpeg"  # 系统PATH中可用
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        return None

    def _check_common_paths(self) -> Optional[str]:
        """检查常见安装路径"""
        common_paths = self._get_common_ffmpeg_paths()

        for path in common_paths:
            if self._test_ffmpeg_executable(path):
                return path

        return None

    def _get_common_ffmpeg_paths(self) -> List[str]:
        """获取常见FFmpeg安装路径列表"""
        return [
            # Windows常见路径
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            # Linux/macOS常见路径
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/ffmpeg/bin/ffmpeg",
            "/snap/bin/ffmpeg",  # Ubuntu snap
            # 当前目录
            "./ffmpeg",
            "./ffmpeg.exe",
        ]

    def _test_ffmpeg_executable(self, path: str) -> bool:
        """
        测试FFmpeg可执行文件是否可用

        Args:
            path: FFmpeg可执行文件路径

        Returns:
            是否可用
        """
        try:
            if not os.path.exists(path):
                return False

            result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0

        except Exception:
            return False

    def get_ffmpeg_path(self) -> Optional[str]:
        """
        获取FFmpeg可执行文件路径

        Returns:
            FFmpeg路径，如果不可用返回None
        """
        return self.ffmpeg_path

    def is_available(self) -> bool:
        """
        检查FFmpeg是否可用

        Returns:
            FFmpeg是否可用
        """
        return self.ffmpeg_path is not None

    def get_ffprobe_path(self) -> Optional[str]:
        """
        获取ffprobe可执行文件路径

        Returns:
            ffprobe路径，基于FFmpeg路径推导
        """
        if not self.ffmpeg_path:
            return None

        # 尝试推导ffprobe路径
        if "ffmpeg" in self.ffmpeg_path:
            ffprobe_path = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
            if self._test_executable(ffprobe_path, "ffprobe"):
                return ffprobe_path

        # 如果推导失败，尝试系统PATH
        try:
            # Use shutil.which to find the full path (safer than partial path)
            ffprobe_cmd = shutil.which("ffprobe")
            if not ffprobe_cmd:
                return None

            result = subprocess.run(
                [ffprobe_cmd, "-version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return "ffprobe"
        except Exception as e:
            self.logger.debug(f"ffprobe not found in system PATH: {e}")

        return None

    def _test_executable(self, path: str, exe_name: str) -> bool:
        """测试可执行文件是否可用"""
        try:
            result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def get_version_info(self) -> Optional[str]:
        """
        获取FFmpeg版本信息

        Returns:
            版本信息字符串
        """
        if not self.is_available() or not self.ffmpeg_path:
            return None

        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                # 提取第一行的版本信息
                lines = result.stdout.split("\n")
                if lines:
                    return lines[0].strip()

        except Exception as e:
            self.logger.debug(f"Failed to get version info for {self.ffmpeg_path}: {e}")

        return None
