import logging
import os
import time
from configparser import ConfigParser
from typing import Any, Dict, List, Optional, Tuple

import cv2
from PyQt6.QtCore import QThread, pyqtSignal

from ..ai.ai_handler import AIHandler
from ..audio.ffmpeg_audio_processor import FFmpegAudioProcessor
from ..exceptions import (
    FileReadError,
    FileSaveError,
    FrameProcessingError,
    ModelLoadError,
    UnsupportedFormatError,
    VideoReadError,
    VideoWriteError,
)


class VideoProcessorThread(QThread):
    """
    Handles video processing in a separate thread to avoid freezing the GUI.
    Emits signals for progress, status updates, and completion.

    Version: v1.1 (Phase 4 Stage 1.4 - Enhanced Progress Indicators)
    """

    progress = pyqtSignal(int)  # Percentage of completion
    status = pyqtSignal(str)  # Status messages
    finished = pyqtSignal(str)  # Path to the processed file
    error = pyqtSignal(str)  # Error messages
    preview_update = pyqtSignal(object)  # Processed frame for preview

    # 新增: 详细进度信号 (Phase 4 Stage 1.4)
    detailed_progress = pyqtSignal(dict)  # 详细进度信息字典

    def __init__(
        self,
        input_path: str,
        output_path: str,
        ai_params: Optional[Dict[str, Any]],
        config: Optional[ConfigParser] = None,
        preloaded_ai_handler: Optional[AIHandler] = None,
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.ai_params = ai_params or {}
        self.config = config
        self.ai_handler: Optional[AIHandler] = preloaded_ai_handler  # 使用预加载的AI处理器
        self.ffmpeg_processor: Optional[FFmpegAudioProcessor] = None
        self._is_running = True

        # 进度跟踪 (Phase 4 Stage 1.4)
        self._start_time = 0.0  # 处理开始时间
        self._last_frame_time = 0.0  # 上一帧处理时间
        self._processing_speeds: List[float] = []  # 处理速度历史记录 (用于平滑计算)
        self._current_phase = "idle"  # 当前处理阶段

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"VideoProcessorThread initialized for {input_path}")

        if preloaded_ai_handler:
            self.logger.info("使用预加载的AI模型，处理速度将得到优化")

        # Initialize FFmpeg processor
        self.ffmpeg_processor = FFmpegAudioProcessor(config)
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
        """
        发送详细进度信息

        Args:
            phase: 当前处理阶段 (loading_models, detecting_watermarks, processing_frames, merging_audio)
            current_frame: 当前处理的帧数
            total_frames: 总帧数
            additional_info: 额外信息字典
        """
        self._current_phase = phase

        # 计算时间信息
        current_time = time.time()
        time_elapsed = current_time - self._start_time if self._start_time > 0 else 0

        # 计算处理速度 (fps)
        processing_speed = 0.0
        eta = 0.0

        if current_frame > 0 and time_elapsed > 0:
            # 当前瞬时速度
            instant_speed = current_frame / time_elapsed

            # 添加到历史记录 (最多保留10个样本)
            self._processing_speeds.append(instant_speed)
            if len(self._processing_speeds) > 10:
                self._processing_speeds.pop(0)

            # 使用平滑后的速度 (移动平均)
            processing_speed = sum(self._processing_speeds) / len(self._processing_speeds)

            # 计算ETA
            if processing_speed > 0 and total_frames > 0:
                remaining_frames = total_frames - current_frame
                eta = remaining_frames / processing_speed

        # 构建详细进度字典
        progress_data = {
            "phase": phase,
            "current_frame": current_frame,
            "total_frames": total_frames,
            "processing_speed": processing_speed,  # fps
            "time_elapsed": time_elapsed,  # seconds
            "eta": eta,  # seconds
            "percentage": int((current_frame / total_frames) * 100) if total_frames > 0 else 0,
        }

        # 添加额外信息
        if additional_info:
            progress_data.update(additional_info)

        # 发送信号
        self.detailed_progress.emit(progress_data)

    def run(self) -> None:
        """
        Main processing loop for images and videos.
        Reads input file, applies AI processing, and writes output.
        """
        try:
            # 开始计时 (Phase 4 Stage 1.4)
            self._start_time = time.time()

            self.status.emit(f"🚀 开始处理文件: {os.path.basename(self.input_path)}")

            # Initialize AI handler (如果没有预加载，则现在加载)
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

            # Determine file type and process accordingly
            file_ext = os.path.splitext(self.input_path)[1].lower()

            if file_ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                self._process_image()
            elif file_ext in [".mp4", ".avi", ".mkv", ".mov"]:
                self._process_video()
            else:
                raise UnsupportedFormatError("不支持的文件格式", details=f"文件扩展名 '{file_ext}' 不在支持列表中")

        except Exception as e:
            self.logger.error(f"Processing error: {e}")
            self.error.emit(str(e))

    def _process_image(self) -> None:
        """
        Process a single image file.
        """
        try:
            # Read input image
            self.status.emit("🖼️ 读取图片文件...")
            image = cv2.imread(self.input_path)

            if image is None:
                raise FileReadError("无法读取图片文件", details=f"文件路径: {self.input_path}")

            self.logger.info(f"Image loaded: {image.shape}")
            self.progress.emit(20)

            # Setup processing parameters
            processing_params = {
                "auto_detect": self.ai_params.get("auto_detect", True),
                "detection_sensitivity": self.ai_params.get("detection_sensitivity", 0.5),
                "user_mask": self.ai_params.get("user_mask", None),
            }

            # Process image
            self.status.emit("🔍 检测水印区域...")
            self.progress.emit(40)

            if self.ai_handler is None:
                raise ModelLoadError("AI handler not initialized")

            processed_image, processing_info = self.ai_handler.process_frame(
                image, processing_params
            )

            if "error" in processing_info:
                raise FrameProcessingError("帧处理失败", details=processing_info["error"])

            self.progress.emit(80)
            self.status.emit("🎨 修复水印区域...")

            # Log processing results
            areas_found = processing_info.get("watermark_areas_found", 0)
            processing_time = processing_info.get("processing_time", 0)
            method = processing_info.get("inpainting_method", "none")

            self.logger.info(
                f"Processing completed: {areas_found} watermark areas found, "
                f"method: {method}, time: {processing_time:.2f}s"
            )

            # Save processed image
            self.status.emit("💾 保存处理后的图片...")

            if not cv2.imwrite(self.output_path, processed_image):
                raise FileSaveError("保存图片失败", details=f"输出路径: {self.output_path}")

            self.progress.emit(100)

            # Emit preview update
            self.preview_update.emit(processed_image)

            # Emit completion signal
            self.status.emit(f"✅ 处理完成! 发现 {areas_found} 个水印区域")
            self.finished.emit(self.output_path)

        except Exception as e:
            self.logger.error(f"Image processing error: {e}")
            self.error.emit(f"图片处理失败: {str(e)}")

    def _process_video(self) -> None:
        """
        Process a video file frame by frame.
        """
        cap = None
        out = None

        try:
            # Open input video
            self.status.emit("🎬 读取视频文件...")
            cap = cv2.VideoCapture(self.input_path)

            if not cap.isOpened():
                raise VideoReadError("无法打开视频文件", details=f"文件路径: {self.input_path}")

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            self.logger.info(
                f"Video properties: {frame_width}x{frame_height}, {fps} fps, {total_frames} frames"
            )

            # Setup output video writer
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(self.output_path, fourcc, fps, (frame_width, frame_height))

            if not out.isOpened():
                raise VideoWriteError("无法创建输出视频文件", details=f"输出路径: {self.output_path}")

            self.progress.emit(10)

            # Setup processing parameters
            processing_params = {
                "auto_detect": self.ai_params.get("auto_detect", True),
                "detection_sensitivity": self.ai_params.get("detection_sensitivity", 0.5),
                "user_mask": self.ai_params.get("user_mask", None),
            }

            # Process frames
            current_frame = 0
            processed_frames = 0
            total_watermark_areas = 0

            # 发送初始详细进度 (Phase 4 Stage 1.4)
            self._emit_detailed_progress("processing_frames", 0, total_frames)

            while self._is_running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                current_frame += 1

                # Process frame with AI
                if self.ai_handler is None:
                    raise ModelLoadError("AI handler not initialized")

                processed_frame, processing_info = self.ai_handler.process_frame(
                    frame, processing_params
                )

                if "error" in processing_info:
                    self.logger.warning(
                        f"Frame {current_frame} processing error: {processing_info['error']}"
                    )
                    processed_frame = frame  # Use original frame if processing fails
                else:
                    processed_frames += 1
                    total_watermark_areas += processing_info.get("watermark_areas_found", 0)

                # Write processed frame
                out.write(processed_frame)

                # Update progress
                if total_frames > 0:
                    progress_percentage = int((current_frame / total_frames) * 90) + 10  # 10-100%
                    self.progress.emit(progress_percentage)

                # Update status every second
                if current_frame % max(1, int(fps)) == 0:
                    self.status.emit(f"🎨 处理中: {current_frame}/{total_frames} 帧")

                # 发送详细进度 (Phase 4 Stage 1.4) - 每10帧或每秒更新一次
                if current_frame % max(1, int(fps / 10)) == 0:
                    self._emit_detailed_progress(
                        "processing_frames",
                        current_frame,
                        total_frames,
                        {
                            "processed_frames": processed_frames,
                            "total_watermark_areas": total_watermark_areas,
                        },
                    )

                # Emit preview update every 30 frames
                if current_frame % 30 == 0:
                    self.preview_update.emit(processed_frame)

            # Check if processing was cancelled
            if not self._is_running:
                self.status.emit("⚠️ 处理已取消")
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                self.finished.emit("")  # Empty string indicates cancellation
                return

            # Video processing completed, now handle audio
            temp_video_path = self.output_path
            final_output_path = self.output_path

            # If we have FFmpeg, try to preserve audio
            if self.ffmpeg_processor and self.ffmpeg_processor.is_available():
                # Create temporary path for video-only file
                temp_video_path = self.output_path.replace(".", "_temp_video.")

                # Rename current output to temp video
                if os.path.exists(self.output_path):
                    os.rename(self.output_path, temp_video_path)

                # 发送音频合并阶段进度 (Phase 4 Stage 1.4)
                self._emit_detailed_progress("merging_audio", 0, 1)
                self.status.emit("🎵 正在合并原始音频...")
                self.progress.emit(95)

                # Use FFmpeg to merge audio
                audio_success = self.ffmpeg_processor.process_video_with_audio_preservation(
                    original_video_path=self.input_path,
                    processed_video_path=temp_video_path,
                    final_output_path=final_output_path,
                )

                if audio_success:
                    self.logger.info("Audio merged successfully")
                    self._emit_detailed_progress("merging_audio", 1, 1)
                    self.status.emit("✅ 音频合并完成")
                else:
                    self.logger.warning("Audio merge failed, using video-only output")
                    self.status.emit("⚠️ 音频合并失败，使用无音频版本")
                    # Move temp video back to final output
                    if os.path.exists(temp_video_path):
                        if os.path.exists(final_output_path):
                            os.remove(final_output_path)
                        os.rename(temp_video_path, final_output_path)

                # Clean up temp video file
                if os.path.exists(temp_video_path) and temp_video_path != final_output_path:
                    try:
                        os.remove(temp_video_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to clean up temp file: {e}")

            # Processing completed successfully
            self.progress.emit(100)
            self.logger.info(
                f"Video processing completed: {processed_frames}/{current_frame} frames processed, "
                f"{total_watermark_areas} total watermark areas found"
            )

            audio_status = (
                "含音频" if (self.ffmpeg_processor and self.ffmpeg_processor.is_available()) else "无音频"
            )
            self.status.emit(f"✅ 视频处理完成! 处理了 {processed_frames} 帧 ({audio_status})")
            self.finished.emit(final_output_path)

        except Exception as e:
            self.logger.error(f"Video processing error: {e}")
            self.error.emit(f"视频处理失败: {str(e)}")

        finally:
            if cap:
                cap.release()
            if out:
                out.release()

    def merge_audio_if_needed(self, original_video_path: str, video_no_audio_path: str) -> bool:
        """
        Uses FFmpeg to copy audio from the original video to the processed video.
        现在通过FFmpegAudioProcessor实现。
        """
        if self.ffmpeg_processor and self.ffmpeg_processor.is_available():
            return self.ffmpeg_processor.process_video_with_audio_preservation(
                original_video_path=original_video_path,
                processed_video_path=video_no_audio_path,
                final_output_path=video_no_audio_path.replace("_temp_video.", "."),
            )
        else:
            self.logger.warning("FFmpeg not available, cannot merge audio")
            return False

    def stop(self) -> None:
        """
        Signal the processing loop to stop gracefully.
        """
        self._is_running = False
        self.status.emit("⏹️ 正在停止处理...")
        self.logger.info("Stop signal received")


if __name__ == "__main__":
    # Example usage for testing (without GUI)
    # config_for_test = {'Paths': {'ffmpeg_path': 'ffmpeg'}} # Dummy config
    # processor = VideoProcessorThread(
    #     input_path="test_input.mp4", # Replace with a real video for testing
    #     output_path="test_output.mp4",
    #     ai_params={},
    #     config=config_for_test
    # )
    # # Connect signals to simple print functions for testing
    # # processor.progress.connect(lambda p: print(f"Progress: {p}%"))
    # # processor.status.connect(lambda s: print(f"Status: {s}"))
    # # processor.finished.connect(lambda f: print(f"Finished: {f}"))
    # # processor.error.connect(lambda e: print(f"Error: {e}"))
    # processor.run() # Run directly for non-threaded test
    logger = logging.getLogger(__name__)
    logger.info("video_processor.py executed directly (for testing purposes).")
