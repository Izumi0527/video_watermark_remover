"""视频处理线程主实现。"""

from __future__ import annotations

import logging
import multiprocessing
import os
import time
from configparser import ConfigParser
from multiprocessing.synchronize import Event as MpEvent
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QThread, QTimer, pyqtSignal

from ...utils import IMAGE_FILE_EXTENSIONS, VIDEO_FILE_EXTENSIONS
from ..exceptions import ModelLoadError, UnsupportedFormatError

AIHandler = None
FFmpegAudioProcessor = None

AI_HANDLER_REFRESH_KEYS = (
    "device",
    "use_gpu_inpainting",
    "requested_inpainting_backend",
    "opencv_inpainting_method",
    "inpainting_algorithm",
    "inpaint_radius",
    "quality_level",
    "min_area_pixels",
    "inpainting_model_path",
    "lama_model_path",
    "lama_model_dir",
)


def _resolve_ai_handler_class():
    global AIHandler
    if AIHandler is None:
        from ..ai.ai_handler import AIHandler as imported_ai_handler

        AIHandler = imported_ai_handler
    return AIHandler


def _resolve_ffmpeg_audio_processor_class():
    global FFmpegAudioProcessor
    if FFmpegAudioProcessor is None:
        from ..audio.ffmpeg_audio_processor import (
            FFmpegAudioProcessor as imported_ffmpeg_audio_processor,
        )

        FFmpegAudioProcessor = imported_ffmpeg_audio_processor
    return FFmpegAudioProcessor


def _get_optional_config_value(
    config: Optional[ConfigParser], option: str, sections: tuple[str, ...]
) -> Optional[str]:
    if config is None:
        return None

    for section in sections:
        try:
            if config.has_option(section, option):
                value = config.get(section, option).strip()
                return value or None
        except Exception as exc:
            logging.getLogger(__name__).debug(
                "读取配置项失败: section=%s option=%s error=%s",
                section,
                option,
                exc,
            )
    return None


def _inject_inpainting_model_path(
    ai_params: Optional[Dict[str, Any]],
    config: Optional[ConfigParser],
) -> Dict[str, Any]:
    """将配置中的 GPU 修复权重路径注入 ai_params，便于单/多进程链路共用。"""
    merged_params = dict(ai_params or {})
    if merged_params.get("inpainting_model_path"):
        return merged_params

    model_path = _get_optional_config_value(config, "inpainting_model_path", ("Models", "models"))
    if model_path:
        merged_params["inpainting_model_path"] = model_path

    if not merged_params.get("lama_model_path"):
        lama_model_path = _get_optional_config_value(config, "lama_model_path", ("Models", "models"))
        if lama_model_path:
            merged_params["lama_model_path"] = lama_model_path

    if not merged_params.get("lama_model_dir"):
        lama_model_dir = _get_optional_config_value(config, "lama_model_dir", ("Models", "models"))
        if lama_model_dir:
            merged_params["lama_model_dir"] = lama_model_dir
    return merged_params


def _ai_handler_needs_refresh(ai_handler: Any, ai_params: Dict[str, Any]) -> bool:
    """判断预加载 AIHandler 是否需要因关键参数变化而重建。"""
    existing_params = getattr(ai_handler, "ai_params", {}) or {}
    return any(existing_params.get(key) != ai_params.get(key) for key in AI_HANDLER_REFRESH_KEYS)


def _process_image_impl(processor) -> None:
    from .image_processor import process_image

    process_image(processor)


def process_video_multiprocess(processor) -> None:
    from .modes.multiprocess import process_video_multiprocess as impl

    impl(processor)


def process_video_pipeline(processor) -> None:
    from .modes.pipeline import process_video_pipeline as impl

    impl(processor)


def process_video_singleprocess(processor) -> None:
    from .modes.single_process import process_video_singleprocess as impl

    impl(processor)


def process_video_chunk(*args, **kwargs):
    from .workers.chunk import process_video_chunk as impl

    return impl(*args, **kwargs)


def init_worker_ai_handler(*args, **kwargs):
    from .workers.frame_processor import init_worker_ai_handler as impl

    return impl(*args, **kwargs)


def frame_processor_worker(*args, **kwargs):
    from .workers.frame_processor import frame_processor_worker as impl

    return impl(*args, **kwargs)


def extract_video_first_frame(*args, **kwargs):
    from .workers.frame_reader import extract_video_first_frame as impl

    return impl(*args, **kwargs)


def extract_video_frame_at(*args, **kwargs):
    from .workers.frame_reader import extract_video_frame_at as impl

    return impl(*args, **kwargs)


def frame_reader_worker(*args, **kwargs):
    from .workers.frame_reader import frame_reader_worker as impl

    return impl(*args, **kwargs)


def frame_writer_worker(*args, **kwargs):
    from .workers.frame_writer import frame_writer_worker as impl

    return impl(*args, **kwargs)


class VideoProcessorThread(QThread):
    """
    GUI 线程安全的视频/图片处理器，负责调度不同处理模式并转发进度信号。
    """

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    preview_update = pyqtSignal(object)
    detailed_progress = pyqtSignal(dict)

    def __init__(
        self,
        input_path: str,
        output_path: str,
        ai_params: Optional[Dict[str, Any]],
        config: Optional[ConfigParser] = None,
        preloaded_ai_handler: Optional[Any] = None,
        enable_multiprocess: bool = False,
        num_processes: Optional[int] = None,
        use_pipeline: bool = False,
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.ai_params = _inject_inpainting_model_path(ai_params, config)
        self.config = config
        self.ai_handler: Optional[Any] = preloaded_ai_handler
        ffmpeg_processor_class = _resolve_ffmpeg_audio_processor_class()
        self.ffmpeg_processor: Optional[Any] = ffmpeg_processor_class(config)
        self._is_running = True

        self.enable_multiprocess = enable_multiprocess
        self.num_processes = num_processes or min(multiprocessing.cpu_count(), 4)
        self.use_pipeline = use_pipeline
        self._progress_timer: Optional[QTimer] = None
        self._stop_event: Optional[MpEvent] = None

        self._reader_thread = None
        self._writer_thread = None
        self._processor_pool = None

        self._start_time = 0.0
        self._processing_speeds: List[float] = []
        self._current_phase = "idle"

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"VideoProcessorThread initialized for {input_path}")

        if preloaded_ai_handler:
            self.logger.info("使用预加载的AI模型，处理速度将得到优化")

        if self.ffmpeg_processor.is_available():
            self.logger.info("FFmpeg audio processor initialized successfully")
        else:
            self.logger.warning("FFmpeg not available, audio will not be preserved")

    def _emit_detailed_progress(
        self,
        phase: str,
        current_frame: int = 0,
        total_frames: int = 0,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._current_phase = phase
        current_time = time.time()
        time_elapsed = current_time - self._start_time if self._start_time > 0 else 0

        processing_speed = 0.0
        eta = 0.0

        if current_frame > 0 and time_elapsed > 0:
            instant_speed = current_frame / time_elapsed
            self._processing_speeds.append(instant_speed)
            if len(self._processing_speeds) > 10:
                self._processing_speeds.pop(0)

            processing_speed = sum(self._processing_speeds) / len(self._processing_speeds)
            if processing_speed > 0 and total_frames > 0:
                remaining_frames = total_frames - current_frame
                eta = remaining_frames / processing_speed

        progress_data = {
            "phase": phase,
            "current_frame": current_frame,
            "total_frames": total_frames,
            "processing_speed": processing_speed,
            "time_elapsed": time_elapsed,
            "eta": eta,
            "percentage": int((current_frame / total_frames) * 100) if total_frames > 0 else 0,
        }

        if additional_info:
            progress_data.update(additional_info)

        self.detailed_progress.emit(progress_data)

    def run(self) -> None:  # noqa: C901
        try:
            self._start_time = time.time()
            self.status.emit(f"🚀 开始处理文件: {os.path.basename(self.input_path)}")

            if self.ai_handler is None:
                self._emit_detailed_progress("loading_models", 0, 1)
                self.status.emit("🔄 正在加载AI模型...")
                ai_handler_class = _resolve_ai_handler_class()
                self.ai_handler = ai_handler_class(self.config, self.ai_params)
                if not self.ai_handler.load_models():
                    raise ModelLoadError("无法加载 AI 模型")
                self._emit_detailed_progress("loading_models", 1, 1)
                self.status.emit("🤖 AI 模型加载完成")
            else:
                if _ai_handler_needs_refresh(self.ai_handler, self.ai_params):
                    self.logger.info("预加载 AIHandler 参数已变化，重新加载以匹配当前任务")
                    self.status.emit("🔄 当前任务参数已变化，重新加载 AI 模型...")
                    ai_handler_class = _resolve_ai_handler_class()
                    self.ai_handler = ai_handler_class(self.config, self.ai_params)
                    if not self.ai_handler.load_models():
                        raise ModelLoadError("无法加载 AI 模型")
                    self.status.emit("🤖 AI 模型重新加载完成")
                else:
                    new_device = self.ai_params.get("device", "auto")
                    if new_device != self.ai_handler.device_preference:
                        self.logger.info(
                            f"Updating device from '{self.ai_handler.device_preference}' to '{new_device}'"
                        )
                        self.ai_handler.update_device(new_device)
                    self.status.emit("⚡ 使用预加载的AI模型，立即开始处理")

            file_ext = os.path.splitext(self.input_path)[1].lower()

            if file_ext in IMAGE_FILE_EXTENSIONS:
                self._process_image()
            elif file_ext in VIDEO_FILE_EXTENSIONS:
                if self.enable_multiprocess:
                    if self.use_pipeline:
                        self.logger.info(f"Using pipeline mode with {self.num_processes} processes")
                        self._process_video_pipeline()
                    else:
                        self.logger.info(f"Using chunk mode with {self.num_processes} processes")
                        self._process_video_multiprocess()
                else:
                    self.logger.info("Using single-process mode")
                    self._process_video_singleprocess()
            else:
                raise UnsupportedFormatError("不支持的文件格式", details=f"文件扩展名 '{file_ext}' 不在支持列表中")

        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Processing error: {e}")
            self.error.emit(str(e))

    def _process_image(self) -> None:
        _process_image_impl(self)

    def _process_video_multiprocess(self) -> None:
        process_video_multiprocess(self)

    def _process_video_pipeline(self) -> None:
        process_video_pipeline(self)

    def _process_video_singleprocess(self) -> None:
        process_video_singleprocess(self)

    def stop(self) -> None:
        self._is_running = False
        if self._stop_event:
            try:
                self._stop_event.set()
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"设置停止事件失败: {e}")
        self.status.emit("⏹️ 正在停止处理...")
        self.logger.info("Stop signal received")


__all__ = [
    "VideoProcessorThread",
    "process_video_singleprocess",
    "process_video_multiprocess",
    "process_video_pipeline",
    "process_video_chunk",
    "init_worker_ai_handler",
    "frame_processor_worker",
    "extract_video_first_frame",
    "extract_video_frame_at",
    "frame_reader_worker",
    "frame_writer_worker",
]
