"""
自定义异常类单元测试

测试项目中所有自定义异常类的功能：
1. 异常创建和继承关系
2. 异常消息格式
3. 异常包装功能
4. 异常映射表

测试用例数量: 15个
覆盖率目标: 自定义异常模块100%
"""

import pytest

from app.core.exceptions import (  # 基础异常; 配置相关; 文件处理; AI模型相关; 音频处理; 视频处理; UI相关; 工具函数
    EXCEPTION_MAPPING,
    AIModelError,
    AudioExtractionError,
    AudioMergingError,
    AudioProcessingError,
    ConfigError,
    ConfigLoadError,
    ConfigSaveError,
    ConfigValidationError,
    DetectionError,
    FFmpegError,
    FileProcessingError,
    FileReadError,
    FileSaveError,
    FrameProcessingError,
    InpaintingError,
    ModelLoadError,
    PreviewError,
    SignalError,
    UIError,
    UnsupportedFormatError,
    VideoProcessingError,
    VideoReadError,
    VideoWatermarkRemoverError,
    VideoWriteError,
    get_custom_exception,
    wrap_exception,
)


class TestBaseException:
    """测试基础异常类"""

    def test_base_exception_creation(self):
        """测试创建基础异常"""
        exc = VideoWatermarkRemoverError("测试错误")
        assert str(exc) == "测试错误"
        assert exc.message == "测试错误"
        assert exc.details is None
        assert exc.original_exception is None

    def test_base_exception_with_details(self):
        """测试带详情的异常"""
        exc = VideoWatermarkRemoverError("测试错误", details="额外信息")
        assert "测试错误" in str(exc)
        assert "额外信息" in str(exc)
        assert exc.details == "额外信息"

    def test_base_exception_with_original(self):
        """测试包装原始异常"""
        original = ValueError("原始错误")
        exc = VideoWatermarkRemoverError("包装错误", original_exception=original)
        assert "包装错误" in str(exc)
        assert "原始错误" in str(exc)
        assert exc.original_exception is original


class TestConfigExceptions:
    """测试配置相关异常"""

    def test_config_error_inheritance(self):
        """测试ConfigError继承自基类"""
        exc = ConfigError("配置错误")
        assert isinstance(exc, VideoWatermarkRemoverError)
        assert isinstance(exc, Exception)

    def test_config_load_error(self):
        """测试配置加载错误"""
        exc = ConfigLoadError("无法加载配置", details="文件不存在")
        assert "无法加载配置" in str(exc)
        assert "文件不存在" in str(exc)

    def test_config_save_error(self):
        """测试配置保存错误"""
        exc = ConfigSaveError("无法保存配置")
        assert str(exc) == "无法保存配置"

    def test_config_validation_error(self):
        """测试配置验证错误"""
        exc = ConfigValidationError("验证失败", details="值超出范围")
        assert "验证失败" in str(exc)


class TestFileExceptions:
    """测试文件处理相关异常"""

    def test_unsupported_format_error(self):
        """测试不支持的文件格式错误"""
        exc = UnsupportedFormatError("格式不支持", details=".xyz 文件")
        assert isinstance(exc, FileProcessingError)
        assert ".xyz 文件" in str(exc)

    def test_file_read_error(self):
        """测试文件读取错误"""
        exc = FileReadError("读取失败", details="路径: /test/file.txt")
        assert "读取失败" in str(exc)
        assert "路径:" in str(exc)

    def test_file_save_error(self):
        """测试文件保存错误"""
        exc = FileSaveError("保存失败")
        assert str(exc) == "保存失败"


class TestAIExceptions:
    """测试AI模型相关异常"""

    def test_model_load_error(self):
        """测试模型加载错误"""
        exc = ModelLoadError("无法加载模型", details="文件缺失")
        assert isinstance(exc, AIModelError)
        assert "无法加载模型" in str(exc)

    def test_detection_error(self):
        """测试水印检测错误"""
        exc = DetectionError("检测失败")
        assert isinstance(exc, AIModelError)

    def test_inpainting_error(self):
        """测试图像修复错误"""
        exc = InpaintingError("修复失败")
        assert isinstance(exc, AIModelError)


class TestAudioExceptions:
    """测试音频处理相关异常"""

    def test_audio_extraction_error(self):
        """测试音频提取错误"""
        exc = AudioExtractionError("提取失败")
        assert isinstance(exc, AudioProcessingError)

    def test_audio_merging_error(self):
        """测试音频合并错误"""
        exc = AudioMergingError("合并失败")
        assert isinstance(exc, AudioProcessingError)

    def test_ffmpeg_error(self):
        """测试FFmpeg错误"""
        exc = FFmpegError("FFmpeg失败", details="返回码: 1")
        assert "返回码: 1" in str(exc)


class TestVideoExceptions:
    """测试视频处理相关异常"""

    def test_video_read_error(self):
        """测试视频读取错误"""
        exc = VideoReadError("无法读取视频", details="文件路径: /test/video.mp4")
        assert isinstance(exc, VideoProcessingError)
        assert "文件路径:" in str(exc)

    def test_video_write_error(self):
        """测试视频写入错误"""
        exc = VideoWriteError("无法写入视频")
        assert isinstance(exc, VideoProcessingError)

    def test_frame_processing_error(self):
        """测试帧处理错误"""
        exc = FrameProcessingError("帧处理失败")
        assert isinstance(exc, VideoProcessingError)


class TestUIExceptions:
    """测试UI相关异常"""

    def test_preview_error(self):
        """测试预览错误"""
        exc = PreviewError("预览失败")
        assert isinstance(exc, UIError)

    def test_signal_error(self):
        """测试信号处理错误"""
        exc = SignalError("信号处理失败")
        assert isinstance(exc, UIError)


class TestExceptionUtils:
    """测试异常工具函数"""

    def test_wrap_exception(self):
        """测试wrap_exception函数"""
        original = ValueError("原始错误")
        wrapped = wrap_exception(FileReadError, "文件操作失败", original)

        assert isinstance(wrapped, FileReadError)
        assert wrapped.message == "文件操作失败"
        assert wrapped.original_exception is original
        assert "原始错误" in str(wrapped)

    def test_get_custom_exception_with_mapping(self):
        """测试get_custom_exception函数（有映射）"""
        standard_exc = FileNotFoundError("文件不存在")
        custom_exc_class = get_custom_exception(standard_exc)

        assert custom_exc_class is FileReadError

    def test_get_custom_exception_without_mapping(self):
        """测试get_custom_exception函数（无映射）"""
        standard_exc = RuntimeError("运行时错误")
        custom_exc_class = get_custom_exception(standard_exc, FileProcessingError)

        assert custom_exc_class is FileProcessingError

    def test_exception_mapping_completeness(self):
        """测试异常映射表的完整性"""
        assert FileNotFoundError in EXCEPTION_MAPPING
        assert PermissionError in EXCEPTION_MAPPING
        assert ValueError in EXCEPTION_MAPPING
        assert KeyError in EXCEPTION_MAPPING


class TestExceptionHierarchy:
    """测试异常层次结构的完整性"""

    def test_all_exceptions_inherit_from_base(self):
        """测试所有自定义异常都继承自基类"""
        exception_classes = [
            ConfigError,
            ConfigLoadError,
            ConfigSaveError,
            ConfigValidationError,
            FileProcessingError,
            UnsupportedFormatError,
            FileReadError,
            FileSaveError,
            AIModelError,
            ModelLoadError,
            DetectionError,
            InpaintingError,
            AudioProcessingError,
            AudioExtractionError,
            AudioMergingError,
            FFmpegError,
            VideoProcessingError,
            VideoReadError,
            VideoWriteError,
            FrameProcessingError,
            UIError,
            PreviewError,
            SignalError,
        ]

        for exc_class in exception_classes:
            assert issubclass(exc_class, VideoWatermarkRemoverError)
            assert issubclass(exc_class, Exception)

    def test_second_level_inheritance(self):
        """测试二级继承关系"""
        # ConfigError的子类
        assert issubclass(ConfigLoadError, ConfigError)
        assert issubclass(ConfigSaveError, ConfigError)

        # FileProcessingError的子类
        assert issubclass(FileReadError, FileProcessingError)
        assert issubclass(FileSaveError, FileProcessingError)

        # AIModelError的子类
        assert issubclass(ModelLoadError, AIModelError)
        assert issubclass(DetectionError, AIModelError)

        # AudioProcessingError的子类
        assert issubclass(AudioExtractionError, AudioProcessingError)
        assert issubclass(FFmpegError, AudioProcessingError)

        # VideoProcessingError的子类
        assert issubclass(VideoReadError, VideoProcessingError)
        assert issubclass(FrameProcessingError, VideoProcessingError)

        # UIError的子类
        assert issubclass(PreviewError, UIError)
        assert issubclass(SignalError, UIError)


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
