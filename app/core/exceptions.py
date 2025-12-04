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

from typing import Any, Callable, Optional
import logging

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


# ==================== 全局异常处理器 ====================


class GlobalExceptionHandler:
    """
    全局异常处理器

    提供应用程序级别的异常捕获、日志记录和用户通知功能。
    支持 Qt 应用程序的异常钩子集成。

    Phase 6 新增: 统一的异常处理入口点

    Usage:
        handler = GlobalExceptionHandler()
        handler.install()  # 安装为全局处理器

        # 或者手动处理
        try:
            risky_operation()
        except Exception as e:
            handler.handle(e, context="视频处理")
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化全局异常处理器

        Args:
            logger: 可选的日志记录器，默认使用模块级别日志
        """
        self.logger = logger or logging.getLogger("GlobalExceptionHandler")
        self._original_excepthook: Optional[Callable[..., Any]] = None
        self._error_callbacks: list[Callable[..., Any]] = []

    def install(self) -> None:
        """
        安装为全局异常处理器

        替换 sys.excepthook 以捕获所有未处理的异常。
        """
        import sys

        self._original_excepthook = sys.excepthook
        sys.excepthook = self._excepthook

    def uninstall(self) -> None:
        """
        卸载全局异常处理器

        恢复原始的 sys.excepthook。
        """
        import sys

        if self._original_excepthook:
            sys.excepthook = self._original_excepthook
            self._original_excepthook = None

    def register_callback(self, callback: Callable[..., Any]) -> None:
        """
        注册错误回调

        当异常发生时，所有注册的回调都会被调用。

        Args:
            callback: 回调函数，签名为 (exc_type, exc_value, exc_tb, context)
        """
        self._error_callbacks.append(callback)

    def unregister_callback(self, callback: Callable[..., Any]) -> None:
        """移除已注册的回调"""
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)

    def _excepthook(self, exc_type: type, exc_value: Exception, exc_tb) -> None:
        """
        sys.excepthook 替代函数

        处理所有未捕获的异常。
        """
        self.handle(exc_value, exc_type=exc_type, exc_tb=exc_tb)

        # 调用原始钩子（如果存在）
        if self._original_excepthook:
            self._original_excepthook(exc_type, exc_value, exc_tb)

    def handle(
        self,
        exception: Exception,
        context: Optional[str] = None,
        exc_type: Optional[type] = None,
        exc_tb=None,
    ) -> dict:
        """
        处理异常

        记录日志、通知回调、返回结构化错误信息。

        Args:
            exception: 异常实例
            context: 异常发生的上下文描述
            exc_type: 异常类型（可选，默认从 exception 推断）
            exc_tb: 异常回溯（可选）

        Returns:
            包含错误信息的字典
        """
        import traceback

        exc_type = exc_type or type(exception)
        context = context or "未知上下文"

        # 构建错误信息
        error_info = {
            "type": exc_type.__name__,
            "message": str(exception),
            "context": context,
            "is_custom": isinstance(exception, VideoWatermarkRemoverError),
            "traceback": None,
        }

        # 提取详细信息（如果是自定义异常）
        if isinstance(exception, VideoWatermarkRemoverError):
            error_info["details"] = exception.details
            error_info["original_exception"] = (
                str(exception.original_exception)
                if exception.original_exception
                else None
            )

        # 获取堆栈跟踪
        if exc_tb:
            error_info["traceback"] = "".join(
                traceback.format_exception(exc_type, exception, exc_tb)
            )
        else:
            error_info["traceback"] = traceback.format_exc()

        # 记录日志
        self._log_exception(error_info)

        # 通知所有回调
        for callback in self._error_callbacks:
            try:
                callback(exc_type, exception, exc_tb, context)
            except Exception as callback_error:
                self.logger.warning(f"异常回调执行失败: {callback_error}")

        return error_info

    def _log_exception(self, error_info: dict) -> None:
        """记录异常到日志"""
        log_message = (
            f"[{error_info['context']}] {error_info['type']}: {error_info['message']}"
        )

        if error_info.get("details"):
            log_message += f" | 详情: {error_info['details']}"

        self.logger.error(log_message)

        if error_info.get("traceback"):
            self.logger.debug(f"堆栈跟踪:\n{error_info['traceback']}")

    def get_user_friendly_message(self, exception: Exception) -> str:
        """
        获取用户友好的错误消息

        将技术性错误转换为用户可理解的消息。

        Args:
            exception: 异常实例

        Returns:
            用户友好的错误消息字符串
        """
        # 自定义异常直接使用其消息
        if isinstance(exception, VideoWatermarkRemoverError):
            return exception.message

        # 标准异常映射
        user_messages = {
            FileNotFoundError: "找不到指定的文件",
            PermissionError: "没有足够的权限执行此操作",
            MemoryError: "内存不足，请关闭其他程序后重试",
            TimeoutError: "操作超时，请检查网络连接或稍后重试",
            ConnectionError: "网络连接失败，请检查网络设置",
            ValueError: "输入的值无效，请检查后重试",
            TypeError: "操作类型不匹配",
            KeyboardInterrupt: "操作已被用户取消",
        }

        exc_type = type(exception)
        if exc_type in user_messages:
            return user_messages[exc_type]

        # 默认消息
        return f"发生错误: {str(exception)}"

    def __enter__(self) -> "GlobalExceptionHandler":
        """上下文管理器入口"""
        self.install()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """上下文管理器退出"""
        self.uninstall()
        if exc_val:
            self.handle(exc_val, exc_type=exc_type, exc_tb=exc_tb)
        # 返回 None 表示不抑制异常


# 全局单例实例
_global_handler: Optional[GlobalExceptionHandler] = None


def get_global_exception_handler() -> GlobalExceptionHandler:
    """
    获取全局异常处理器单例

    Returns:
        GlobalExceptionHandler 实例
    """
    global _global_handler
    if _global_handler is None:
        _global_handler = GlobalExceptionHandler()
    return _global_handler


def install_global_exception_handler() -> GlobalExceptionHandler:
    """
    安装全局异常处理器

    便捷函数，用于快速安装全局处理器。

    Returns:
        已安装的 GlobalExceptionHandler 实例
    """
    handler = get_global_exception_handler()
    handler.install()
    return handler


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
