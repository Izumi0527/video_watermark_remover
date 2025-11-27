#!/usr/bin/env python3
"""
自定义异常类模块

定义项目中使用的所有自定义异常类，提供清晰的异常层次结构和错误分类。
遵循 Python 异常最佳实践，所有异常都继承自基础异常类。

异常层次结构：
    VideoWatermarkRemoverError (基类)
    ├── ConfigError (配置相关)
    │   ├── ConfigLoadError
    │   ├── ConfigSaveError
    │   └── ConfigValidationError
    ├── FileProcessingError (文件处理)
    │   ├── UnsupportedFormatError
    │   ├── FileReadError
    │   └── FileSaveError
    ├── AIModelError (AI 模型相关)
    │   ├── ModelLoadError
    │   ├── DetectionError
    │   └── InpaintingError
    ├── AudioProcessingError (音频处理)
    │   ├── AudioExtractionError
    │   ├── AudioMergingError
    │   └── FFmpegError
    ├── VideoProcessingError (视频处理)
    │   ├── VideoReadError
    │   ├── VideoWriteError
    │   └── FrameProcessingError
    └── UIError (UI 相关)
        ├── PreviewError
        └── SignalError

"""

from typing import Optional

# ==================== 基础异常类 ====================


class VideoWatermarkRemoverError(Exception):
    """
    视频水印去除工具基础异常类

    所有自定义异常都应该继承此类，提供统一的异常处理接口。

    Attributes:
        message: 错误消息
        details: 额外的错误详情（可选）
        original_exception: 原始异常对象（可选）
    """

    def __init__(
        self,
        message: str,
        details: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        self.message = message
        self.details = details
        self.original_exception = original_exception

        # 构建完整的错误消息
        full_message = message
        if details:
            full_message = f"{message}: {details}"
        if original_exception:
            full_message = f"{full_message} (原始错误: {str(original_exception)})"

        super().__init__(full_message)


# ==================== 配置相关异常 ====================


class ConfigError(VideoWatermarkRemoverError):
    """配置相关错误的基类"""

    pass


class ConfigLoadError(ConfigError):
    """
    配置加载失败

    当配置文件无法读取、解析失败或格式错误时抛出。

    Example:
        raise ConfigLoadError(
            "无法加载配置文件",
            details="config.ini 文件不存在"
        )
    """

    pass


class ConfigSaveError(ConfigError):
    """
    配置保存失败

    当配置无法写入文件时抛出（权限问题、磁盘空间等）。
    """

    pass


class ConfigValidationError(ConfigError):
    """
    配置验证失败

    当配置项的值不符合预期格式或范围时抛出。

    Example:
        raise ConfigValidationError(
            "检测灵敏度超出范围",
            details="灵敏度必须在 0.0-1.0 之间"
        )
    """

    pass


# ==================== 文件处理相关异常 ====================


class FileProcessingError(VideoWatermarkRemoverError):
    """文件处理错误的基类"""

    pass


class UnsupportedFormatError(FileProcessingError):
    """
    不支持的文件格式

    当输入文件格式不在支持列表中时抛出。

    Example:
        raise UnsupportedFormatError(
            "不支持的文件格式",
            details=f"格式 .{file_ext} 不在支持列表中"
        )
    """

    pass


class FileReadError(FileProcessingError):
    """
    文件读取失败

    当无法读取输入文件时抛出（文件不存在、权限不足、损坏等）。
    """

    pass


class FileSaveError(FileProcessingError):
    """
    文件保存失败

    当无法保存输出文件时抛出（权限不足、磁盘空间不足等）。
    """

    pass


# ==================== AI 模型相关异常 ====================


class AIModelError(VideoWatermarkRemoverError):
    """AI 模型相关错误的基类"""

    pass


class ModelLoadError(AIModelError):
    """
    模型加载失败

    当 AI 模型无法加载时抛出（文件缺失、格式错误、版本不兼容等）。

    Example:
        raise ModelLoadError(
            "无法加载水印检测模型",
            details="模型文件 yolov5.pt 不存在"
        )
    """

    pass


class DetectionError(AIModelError):
    """
    水印检测失败

    当水印检测过程中发生错误时抛出。
    """

    pass


class InpaintingError(AIModelError):
    """
    图像修复失败

    当图像修复过程中发生错误时抛出。
    """

    pass


# ==================== 音频处理相关异常 ====================


class AudioProcessingError(VideoWatermarkRemoverError):
    """音频处理错误的基类"""

    pass


class AudioExtractionError(AudioProcessingError):
    """
    音频提取失败

    当从视频中提取音频失败时抛出。
    """

    pass


class AudioMergingError(AudioProcessingError):
    """
    音频合并失败

    当将音频合并回视频失败时抛出。
    """

    pass


class FFmpegError(AudioProcessingError):
    """
    FFmpeg 执行错误

    当 FFmpeg 命令执行失败时抛出。

    Example:
        raise FFmpegError(
            "FFmpeg 命令执行失败",
            details=f"返回码: {returncode}, 错误: {stderr}"
        )
    """

    pass


# ==================== 视频处理相关异常 ====================


class VideoProcessingError(VideoWatermarkRemoverError):
    """视频处理错误的基类"""

    pass


class VideoReadError(VideoProcessingError):
    """
    视频读取失败

    当无法打开或读取视频文件时抛出。

    Example:
        raise VideoReadError(
            "无法打开视频文件",
            details=f"文件路径: {video_path}"
        )
    """

    pass


class VideoWriteError(VideoProcessingError):
    """
    视频写入失败

    当无法创建或写入视频文件时抛出。
    """

    pass


class FrameProcessingError(VideoProcessingError):
    """
    帧处理失败

    当处理视频帧时发生错误时抛出。
    """

    pass


# ==================== UI 相关异常 ====================


class UIError(VideoWatermarkRemoverError):
    """UI 相关错误的基类"""

    pass


class PreviewError(UIError):
    """
    预览显示失败

    当无法加载或显示预览图像时抛出。
    """

    pass


class SignalError(UIError):
    """
    信号处理失败

    当 Qt 信号处理发生错误时抛出。
    """

    pass


# ==================== 工具函数 ====================


def wrap_exception(
    exception_class: type[VideoWatermarkRemoverError], message: str, original_exception: Exception
) -> VideoWatermarkRemoverError:
    """
    包装原始异常为自定义异常

    用于在 except 块中将标准异常转换为自定义异常。

    Args:
        exception_class: 自定义异常类
        message: 错误消息
        original_exception: 原始异常对象

    Returns:
        包装后的自定义异常实例

    Example:
        try:
            config = ConfigParser()
            config.read("config.ini")
        except Exception as e:
            raise wrap_exception(
                ConfigLoadError,
                "无法加载配置文件",
                e
            )
    """
    return exception_class(message=message, original_exception=original_exception)


# ==================== 异常类型映射表 ====================

# 用于快速查找标准异常对应的自定义异常
EXCEPTION_MAPPING = {
    # 文件相关
    FileNotFoundError: FileReadError,
    PermissionError: FileProcessingError,
    IsADirectoryError: FileReadError,
    # 配置相关
    ValueError: ConfigValidationError,
    KeyError: ConfigValidationError,
    # 通用映射
    OSError: FileProcessingError,
    IOError: FileProcessingError,
}


def get_custom_exception(
    standard_exception: Exception,
    default_class: type[VideoWatermarkRemoverError] = VideoWatermarkRemoverError,
) -> type[VideoWatermarkRemoverError]:
    """
    根据标准异常获取对应的自定义异常类

    Args:
        standard_exception: 标准异常实例
        default_class: 默认异常类（如果找不到映射）

    Returns:
        自定义异常类

    Example:
        try:
            with open("file.txt") as f:
                content = f.read()
        except Exception as e:
            custom_exc_class = get_custom_exception(e, FileReadError)
            raise custom_exc_class(
                "文件读取失败",
                original_exception=e
            )
    """
    exc_type = type(standard_exception)
    return EXCEPTION_MAPPING.get(exc_type, default_class)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("Custom exceptions module loaded.")

    # 测试异常层次结构
    print("\n异常层次结构:")
    print("VideoWatermarkRemoverError")
    print("├── ConfigError")
    print("│   ├── ConfigLoadError")
    print("│   ├── ConfigSaveError")
    print("│   └── ConfigValidationError")
    print("├── FileProcessingError")
    print("│   ├── UnsupportedFormatError")
    print("│   ├── FileReadError")
    print("│   └── FileSaveError")
    print("├── AIModelError")
    print("│   ├── ModelLoadError")
    print("│   ├── DetectionError")
    print("│   └── InpaintingError")
    print("├── AudioProcessingError")
    print("│   ├── AudioExtractionError")
    print("│   ├── AudioMergingError")
    print("│   └── FFmpegError")
    print("├── VideoProcessingError")
    print("│   ├── VideoReadError")
    print("│   ├── VideoWriteError")
    print("│   └── FrameProcessingError")
    print("└── UIError")
    print("    ├── PreviewError")
    print("    └── SignalError")

    # 测试异常创建
    try:
        raise VideoReadError("无法打开视频文件", details="文件路径: /path/to/video.mp4")
    except VideoWatermarkRemoverError as e:
        print(f"\n捕获异常: {e}")
        print(f"消息: {e.message}")
        print(f"详情: {e.details}")

    # 测试异常包装
    try:
        raise FileNotFoundError("文件不存在")
    except Exception as e:
        wrapped = wrap_exception(FileReadError, "文件操作失败", e)
        print(f"\n包装异常: {wrapped}")
        print(f"原始异常: {wrapped.original_exception}")
