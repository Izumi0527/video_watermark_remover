import logging
import multiprocessing
import os
import time
from configparser import ConfigParser
from multiprocessing.synchronize import Event as MpEvent
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QThread, QTimer, pyqtSignal

from ..ai.ai_handler import AIHandler
from ..audio.ffmpeg_audio_processor import FFmpegAudioProcessor
from ..exceptions import ModelLoadError, UnsupportedFormatError
from .image_processor import process_image
from .multiprocess_processor import process_video_multiprocess
from .pipeline_processor import process_video_pipeline
from .single_process_processor import process_video_singleprocess


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
        preloaded_ai_handler: Optional[AIHandler] = None,
        enable_multiprocess: bool = False,
        num_processes: Optional[int] = None,
        use_pipeline: bool = False,
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.ai_params = ai_params or {}
        self.config = config
        self.ai_handler: Optional[AIHandler] = preloaded_ai_handler
        self.ffmpeg_processor: Optional[FFmpegAudioProcessor] = FFmpegAudioProcessor(config)
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

    def run(self) -> None:
        try:
            self._start_time = time.time()
            self.status.emit(f"🚀 开始处理文件: {os.path.basename(self.input_path)}")

            if self.ai_handler is None:
                self._emit_detailed_progress("loading_models", 0, 1)
                self.status.emit("🔄 正在加载AI模型...")
                self.ai_handler = AIHandler(self.config, self.ai_params)
                if not self.ai_handler.load_models():
                    raise ModelLoadError("无法加载 AI 模型")
                self._emit_detailed_progress("loading_models", 1, 1)
                self.status.emit("🤖 AI 模型加载完成")
            else:
                self.status.emit("⚡ 使用预加载的AI模型，立即开始处理")

            file_ext = os.path.splitext(self.input_path)[1].lower()

            if file_ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                self._process_image()
            elif file_ext in [".mp4", ".avi", ".mkv", ".mov"]:
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
        process_image(self)

    def _process_video_multiprocess(self) -> None:
        process_video_multiprocess(self)

    def _process_video_pipeline(self) -> None:
        process_video_pipeline(self)

    def _process_video_singleprocess(self) -> None:
        process_video_singleprocess(self)

    def stop(self) -> None:
        self._is_running = False
        self.status.emit("⏹️ 正在停止处理...")
        self.logger.info("Stop signal received")
