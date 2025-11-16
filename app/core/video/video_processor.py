import gc
import logging
import multiprocessing
import os
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from configparser import ConfigParser
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import QThread, QTimer, pyqtSignal

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

# ============================================================================
# Module-level function for multiprocessing (Phase 4 Stage 2.1)
# Must be at module level for pickle compatibility with multiprocessing
# ============================================================================


def process_video_chunk(
    video_path: str,
    start_frame: int,
    end_frame: int,
    output_path: str,
    ai_params: dict,
    config_dict: Optional[dict],
    progress_queue: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
    chunk_id: int,
) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    处理视频块（在子进程中运行）

    Args:
        video_path: 输入视频路径
        start_frame: 起始帧索引
        end_frame: 结束帧索引
        output_path: 输出临时文件路径
        ai_params: AI 参数字典
        config_dict: 配置字典（ConfigParser无法pickle，传递字典）
        progress_queue: 进度队列（发送进度信息到主线程）
        stop_event: 停止事件（主线程通知停止）
        chunk_id: 块ID（用于进度标识）

    Returns:
        (输出路径, 成功标志, 错误信息)
    """
    logger = logging.getLogger(__name__)

    try:
        # 1. 在子进程中加载 AI 模型
        ai_handler = AIHandler(None, ai_params)
        if not ai_handler.load_models():
            return (None, False, "AI 模型加载失败")

        # 2. 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return (None, False, "无法打开视频文件")

        # 3. 获取视频参数
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

        # 4. 创建视频写入器
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not out.isOpened():
            cap.release()
            return (None, False, f"无法创建输出文件: {output_path}")

        # 5. 定位到起始帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # 6. 逐帧处理
        total_frames_in_chunk = end_frame - start_frame
        processed_count = 0

        for i in range(total_frames_in_chunk):
            # 检查停止事件
            if stop_event.is_set():
                logger.info(f"Chunk {chunk_id} stopped by user request")
                break

            ret, frame = cap.read()
            if not ret:
                break

            # AI 处理
            try:
                # 准备处理参数 (Phase 4 Stage 2.1修复)
                processing_params = {
                    "auto_detect": ai_params.get("auto_detect", True),
                    "detection_sensitivity": ai_params.get("detection_sensitivity", 0.5),
                    "user_mask": ai_params.get("user_mask", None),
                }
                processed_frame, _ = ai_handler.process_frame(frame, processing_params)
                out.write(processed_frame)
                processed_count += 1
            except Exception as e:
                logger.warning(f"Frame processing error in chunk {chunk_id}: {e}")
                # 写入原始帧
                out.write(frame)

            # 发送进度（每10帧）
            if i % 10 == 0:
                try:
                    progress_queue.put(
                        {
                            "chunk_id": chunk_id,
                            "current": i,
                            "total": total_frames_in_chunk,
                            "processed": processed_count,
                        },
                        block=False,
                    )
                except Exception:
                    pass  # 队列满时忽略

        # 7. 释放资源
        cap.release()
        out.release()

        logger.info(f"Chunk {chunk_id} completed: {processed_count}/{total_frames_in_chunk} frames")
        return (output_path, True, None)

    except Exception as e:
        error_msg = f"Chunk {chunk_id} error: {str(e)}"
        logger.error(error_msg)
        return (None, False, error_msg)


# ============================================================================
# Pipeline workers for Stage 2.2 (I/O & Processing Pipeline)
# Must be at module level for pickle compatibility
# ============================================================================


def frame_reader_worker(
    video_path: str,
    frame_queue: multiprocessing.Queue,
    total_frames: int,
    stop_event: multiprocessing.Event,
) -> None:
    """
    帧读取工作线程 (Phase 4 Stage 2.2)

    Args:
        video_path: 视频路径
        frame_queue: 帧队列
        total_frames: 总帧数
        stop_event: 停止事件
    """
    logger = logging.getLogger(__name__)

    try:
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            frame_queue.put(None)  # 发送结束信号
            return

        logger.info(f"Frame reader started: {total_frames} frames to read")

        # 顺序读取所有帧
        for frame_index in range(total_frames):
            if stop_event.is_set():
                logger.info("Frame reader stopped by user request")
                break

            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Failed to read frame {frame_index}")
                break

            # 放入队列 (阻塞等待,如果队列满)
            try:
                frame_queue.put((frame_index, frame), timeout=10)
            except Exception as e:
                logger.error(f"Failed to put frame {frame_index} into queue: {e}")
                break

            # 每100帧输出日志
            if frame_index % 100 == 0:
                logger.debug(f"Frame reader: {frame_index}/{total_frames} frames read")

        # 发送结束信号
        frame_queue.put(None)
        logger.info("Frame reader completed")

    except Exception as e:
        logger.error(f"Frame reader error: {e}")
        frame_queue.put(None)  # 确保发送结束信号

    finally:
        if cap:
            cap.release()


def frame_processor_worker(
    frame_queue: multiprocessing.Queue,
    result_queue: multiprocessing.Queue,
    ai_params: dict,
    config_dict: Optional[dict],
    stop_event: multiprocessing.Event,
    progress_queue: multiprocessing.Queue,
    worker_id: int,
) -> None:
    """
    帧处理工作进程 (Phase 4 Stage 2.2)

    Args:
        frame_queue: 帧队列
        result_queue: 结果队列
        ai_params: AI 参数
        config_dict: 配置字典
        stop_event: 停止事件
        progress_queue: 进度队列
        worker_id: 工作进程ID
    """
    logger = logging.getLogger(__name__)

    try:
        # 加载 AI 模型
        logger.info(f"Worker {worker_id} loading AI models...")
        ai_handler = AIHandler(None, ai_params)
        if not ai_handler.load_models():
            logger.error(f"Worker {worker_id} failed to load AI models")
            return

        logger.info(f"Worker {worker_id} started")
        processed_count = 0

        while not stop_event.is_set():
            try:
                # 从队列取帧 (阻塞等待,如果队列空)
                item = frame_queue.get(timeout=1)

                # 检查结束信号
                if item is None:
                    # 传递给其他进程
                    frame_queue.put(None)
                    logger.info(f"Worker {worker_id} received end signal")
                    break

                frame_index, frame = item

                # AI 处理
                processing_params = {
                    "auto_detect": ai_params.get("auto_detect", True),
                    "detection_sensitivity": ai_params.get("detection_sensitivity", 0.5),
                    "user_mask": ai_params.get("user_mask", None),
                }

                processed_frame, _ = ai_handler.process_frame(frame, processing_params)

                # 放入结果队列
                result_queue.put((frame_index, processed_frame), timeout=10)

                processed_count += 1

                # 发送进度 (每10帧)
                if processed_count % 10 == 0:
                    try:
                        progress_queue.put(
                            {
                                "worker_id": worker_id,
                                "processed": processed_count,
                            },
                            block=False,
                        )
                    except Exception:
                        pass  # 队列满时忽略

            except Exception as e:
                if "timeout" not in str(e).lower():
                    logger.warning(f"Worker {worker_id} processing error: {e}")
                continue

        logger.info(f"Worker {worker_id} completed: {processed_count} frames processed")

    except Exception as e:
        logger.error(f"Worker {worker_id} fatal error: {e}")


def frame_writer_worker(
    result_queue: multiprocessing.Queue,
    output_path: str,
    video_params: dict,
    total_frames: int,
    stop_event: multiprocessing.Event,
    progress_queue: multiprocessing.Queue,
) -> Tuple[bool, Optional[str]]:
    """
    帧写入工作线程 (Phase 4 Stage 2.2, 优化 Phase 4 Stage 2.4)

    Args:
        result_queue: 结果队列
        output_path: 输出路径
        video_params: 视频参数 (fps, width, height, fourcc)
        total_frames: 总帧数
        stop_event: 停止事件
        progress_queue: 进度队列

    Returns:
        (success, error_message)
    """
    logger = logging.getLogger(__name__)

    # Phase 4 Stage 2.4: 限制缓冲区大小,避免内存占用过大
    MAX_BUFFER_SIZE = 50

    out = None
    frame_buffer = {}  # 乱序缓冲区: {frame_index: processed_frame}
    next_frame_index = 0
    received_count = 0

    try:
        # 创建视频写入器
        fps = video_params["fps"]
        width = video_params["width"]
        height = video_params["height"]
        fourcc = video_params["fourcc"]

        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not out.isOpened():
            error_msg = f"Failed to create video writer: {output_path}"
            logger.error(error_msg)
            return (False, error_msg)

        logger.info(f"Frame writer started: writing to {output_path}")

        # 循环处理结果
        while received_count < total_frames and not stop_event.is_set():
            try:
                # Phase 4 Stage 2.4: 如果缓冲区过大,等待写入进度
                while len(frame_buffer) >= MAX_BUFFER_SIZE and not stop_event.is_set():
                    time.sleep(0.01)  # 等待写入线程消化缓冲区

                # 从队列取结果 (阻塞等待)
                item = result_queue.get(timeout=1)

                if item is None:
                    logger.info("Frame writer received end signal")
                    break

                frame_index, processed_frame = item

                # 放入缓冲区
                frame_buffer[frame_index] = processed_frame
                received_count += 1

                # 按顺序写入
                while next_frame_index in frame_buffer:
                    frame = frame_buffer.pop(next_frame_index)  # Phase 4 Stage 2.4: 立即删除
                    out.write(frame)
                    del frame  # Phase 4 Stage 2.4: 显式删除引用
                    next_frame_index += 1

                    # 发送进度 (每10帧)
                    if next_frame_index % 10 == 0:
                        try:
                            progress_queue.put(
                                {
                                    "written_frames": next_frame_index,
                                    "total_frames": total_frames,
                                },
                                block=False,
                            )
                        except Exception:
                            pass

                    # Phase 4 Stage 2.4: 定期触发垃圾回收
                    if next_frame_index % 50 == 0:
                        gc.collect()

            except Exception as e:
                if "timeout" not in str(e).lower():
                    logger.warning(f"Frame writer error: {e}")
                continue

        # 写入剩余缓冲的帧
        while next_frame_index < total_frames and next_frame_index in frame_buffer:
            frame = frame_buffer.pop(next_frame_index)
            out.write(frame)
            del frame  # Phase 4 Stage 2.4: 显式删除引用
            next_frame_index += 1

        logger.info(f"Frame writer completed: {next_frame_index}/{total_frames} frames written")

        # 检查是否写入了所有帧
        if next_frame_index < total_frames:
            warning_msg = f"Warning: Only {next_frame_index}/{total_frames} frames written"
            logger.warning(warning_msg)
            return (True, warning_msg)  # 部分成功

        return (True, None)

    except Exception as e:
        error_msg = f"Frame writer fatal error: {str(e)}"
        logger.error(error_msg)
        return (False, error_msg)

    finally:
        if out:
            out.release()


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
        enable_multiprocess: bool = True,  # 新增: 是否启用多进程 (Phase 4 Stage 2.1)
        num_processes: Optional[int] = None,  # 新增: 进程数(None=自动检测)
        use_pipeline: bool = False,  # 新增: 是否使用流水线模式 (Phase 4 Stage 2.2)
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

        # 多进程配置 (Phase 4 Stage 2.1 & 2.2)
        self.enable_multiprocess = enable_multiprocess
        self.num_processes = num_processes or min(multiprocessing.cpu_count(), 4)
        self.use_pipeline = use_pipeline  # 流水线 vs 分块批处理
        self._progress_timer: Optional[QTimer] = None
        self._stop_event: Optional[multiprocessing.Event] = None

        # 流水线相关 (Phase 4 Stage 2.2)
        self._reader_thread: Optional[threading.Thread] = None
        self._writer_thread: Optional[threading.Thread] = None
        self._processor_pool: Optional[ProcessPoolExecutor] = None

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
                # 视频处理: 根据配置选择单/多进程模式 (Phase 4 Stage 2.1 & 2.2)
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

    # ============================================================================
    # 多进程处理辅助方法 (Phase 4 Stage 2.1)
    # ============================================================================

    def _calculate_chunks(
        self, total_frames: int, num_processes: int
    ) -> List[Tuple[int, int, str]]:
        """
        计算分块策略

        Args:
            total_frames: 总帧数
            num_processes: 进程数

        Returns:
            [(start_frame, end_frame, temp_output_path), ...]
        """
        chunk_size = total_frames // num_processes
        chunks = []

        for i in range(num_processes):
            start = i * chunk_size
            # 最后一个块包含剩余所有帧
            end = total_frames if i == num_processes - 1 else (i + 1) * chunk_size

            # 使用 tempfile 创建临时文件路径
            temp_path = os.path.join(tempfile.gettempdir(), f"video_chunk_{i}_{os.getpid()}.mp4")
            chunks.append((start, end, temp_path))

        self.logger.info(f"Calculated {num_processes} chunks for {total_frames} frames")
        return chunks

    def _check_progress_queue(
        self, progress_queue: multiprocessing.Queue, total_frames: int
    ) -> None:
        """
        检查进度队列并发送信号

        Args:
            progress_queue: 进度队列
            total_frames: 总帧数
        """
        try:
            while not progress_queue.empty():
                progress_data = progress_queue.get_nowait()

                chunk_id = progress_data["chunk_id"]
                current = progress_data["current"]
                total = progress_data["total"]

                # 计算总体进度 (假设所有块平均分配)
                chunk_progress = (current / total) if total > 0 else 0
                overall_progress = (
                    int((chunk_id / self.num_processes + chunk_progress / self.num_processes) * 90)
                    + 10
                )  # 10-100%

                # 发送 PyQt 信号
                self.progress.emit(overall_progress)
                self.status.emit(f"🎨 处理块 {chunk_id + 1}/{self.num_processes}: {current}/{total} 帧")

        except Exception as e:
            self.logger.warning(f"Progress polling error: {e}")

    def _merge_video_chunks(self, chunk_paths: List[str], output_path: str) -> None:
        """
        使用 FFmpeg 合并视频块

        Args:
            chunk_paths: 视频块路径列表
            output_path: 输出路径
        """
        concat_list_path = None

        try:
            # 1. 创建 concat 列表文件
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as f:
                concat_list_path = f.name
                for chunk_path in chunk_paths:
                    # FFmpeg concat demuxer 要求绝对路径
                    abs_path = os.path.abspath(chunk_path).replace("\\", "/")
                    f.write(f"file '{abs_path}'\n")

            self.logger.info(f"Created concat list: {concat_list_path}")

            # 2. 使用 FFmpeg concat demuxer 合并(无损、快速)
            ffmpeg_cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list_path,
                "-c",
                "copy",  # 复制编码,不重新编码
                output_path,
                "-y",  # 覆盖已存在文件
            ]

            self.logger.info(f"Running FFmpeg merge: {' '.join(ffmpeg_cmd)}")

            # 3. 执行 FFmpeg
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)

            # 4. 检查结果
            if result.returncode != 0:
                raise Exception(f"FFmpeg merge failed: {result.stderr}")

            self.logger.info(f"Video chunks merged successfully: {output_path}")

        finally:
            # 5. 删除 concat 列表文件
            if concat_list_path and os.path.exists(concat_list_path):
                try:
                    os.remove(concat_list_path)
                except Exception as e:
                    self.logger.warning(f"Failed to remove concat list: {e}")

    def _process_video_multiprocess(self) -> None:
        """
        多进程视频处理 (Phase 4 Stage 2.1)
        使用分块批处理策略,将视频分割成多个块并行处理
        """
        temp_files: List[str] = []

        try:
            # 1. 获取视频信息
            self.status.emit("📊 分析视频信息...")
            cap = cv2.VideoCapture(self.input_path)
            if not cap.isOpened():
                raise VideoReadError("无法打开视频文件", details=f"文件路径: {self.input_path}")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            self.logger.info(f"Video info: {width}x{height}, {fps} fps, {total_frames} frames")
            self.status.emit(f"🚀 使用 {self.num_processes} 个进程并行处理 {total_frames} 帧")

            # 2. 计算分块
            chunks = self._calculate_chunks(total_frames, self.num_processes)
            temp_files = [chunk[2] for chunk in chunks]

            # 3. 创建进度队列和停止事件 (Windows兼容)
            manager = multiprocessing.Manager()
            progress_queue: multiprocessing.Queue = manager.Queue()
            self._stop_event = manager.Event()

            # 4. 启动进度轮询
            self._progress_timer = QTimer()
            self._progress_timer.timeout.connect(
                lambda: self._check_progress_queue(progress_queue, total_frames)
            )
            self._progress_timer.start(100)  # 每100ms检查一次

            # 5. 将 ConfigParser 转换为字典 (ConfigParser 无法 pickle)
            config_dict = None
            if self.config:
                config_dict = {
                    section: dict(self.config[section]) for section in self.config.sections()
                }

            # 6. 并行处理
            self.status.emit("🎨 开始并行处理视频块...")
            results: List[Tuple[Optional[str], bool, Optional[str]]] = []

            with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
                futures = []
                for i, (start, end, temp_path) in enumerate(chunks):
                    future = executor.submit(
                        process_video_chunk,
                        self.input_path,
                        start,
                        end,
                        temp_path,
                        self.ai_params,
                        config_dict,
                        progress_queue,
                        self._stop_event,
                        i,  # chunk_id
                    )
                    futures.append(future)

                # 收集结果
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"Chunk completed: {result[0]}, success={result[1]}")

            # 7. 检查结果
            failed_chunks = [r for r in results if not r[1]]
            if failed_chunks:
                error_messages = [r[2] for r in failed_chunks if r[2]]
                raise Exception(f"{len(failed_chunks)} 个块处理失败: {'; '.join(error_messages)}")

            # 8. 合并视频块
            chunk_paths = [r[0] for r in results if r[0] is not None]
            chunk_paths.sort()  # 确保顺序正确

            self.status.emit("🔗 正在合并视频块...")
            self.progress.emit(95)

            # 创建临时合并文件
            temp_merged_path = self.output_path.replace(".", "_temp_merged.")
            self._merge_video_chunks(chunk_paths, temp_merged_path)

            # 9. 处理音频
            if self.ffmpeg_processor and self.ffmpeg_processor.is_available():
                self.status.emit("🎵 正在合并原始音频...")
                self.progress.emit(97)

                audio_success = self.ffmpeg_processor.process_video_with_audio_preservation(
                    original_video_path=self.input_path,
                    processed_video_path=temp_merged_path,
                    final_output_path=self.output_path,
                )

                if audio_success:
                    self.logger.info("Audio merged successfully")
                    # 删除临时合并文件
                    if os.path.exists(temp_merged_path):
                        os.remove(temp_merged_path)
                else:
                    self.logger.warning("Audio merge failed, using video-only output")
                    # 将临时文件重命名为最终输出
                    if os.path.exists(temp_merged_path):
                        if os.path.exists(self.output_path):
                            os.remove(self.output_path)
                        os.rename(temp_merged_path, self.output_path)
            else:
                # 没有音频处理,直接使用合并后的文件
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                os.rename(temp_merged_path, self.output_path)

            # 10. 完成
            self.progress.emit(100)
            self.status.emit(f"✅ 多进程处理完成! 处理了 {total_frames} 帧")
            self.logger.info(f"Multiprocess video processing completed: {self.output_path}")

        except Exception as e:
            self.logger.error(
                f"Multiprocess processing failed, falling back to single-process: {e}"
            )
            self.status.emit("⚠️ 多进程失败，切换到单进程模式")

            # 降级到单进程处理
            self._process_video_singleprocess()

        finally:
            # 11. 清理
            if self._progress_timer:
                self._progress_timer.stop()
                self._progress_timer = None

            if self._stop_event:
                self._stop_event.set()
                self._stop_event = None

            # 删除临时文件
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        self.logger.debug(f"Removed temp file: {temp_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to remove temp file {temp_file}: {e}")

    def _process_video_pipeline(self) -> None:
        """
        流水线视频处理 (Phase 4 Stage 2.2)
        使用 3 阶段流水线: 读取线程 → 处理进程池 → 写入线程
        """
        frame_queue = None
        result_queue = None
        progress_queue = None

        try:
            # 1. 获取视频信息
            self.status.emit("📊 分析视频信息...")
            cap = cv2.VideoCapture(self.input_path)
            if not cap.isOpened():
                raise VideoReadError("无法打开视频文件", details=f"文件路径: {self.input_path}")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            cap.release()

            self.logger.info(f"Video info: {width}x{height}, {fps} fps, {total_frames} frames")
            self.status.emit(f"🚀 使用流水线模式处理 (读取 → {self.num_processes}进程 → 写入)")

            # 2. 创建队列 (Windows兼容: 使用 Manager)
            manager = multiprocessing.Manager()

            # 动态计算队列大小 (Phase 4 Stage 2.4)
            frame_queue_size, result_queue_size = self._calculate_queue_sizes()

            # 帧队列: 缓冲待处理帧
            frame_queue = manager.Queue(maxsize=frame_queue_size)

            # 结果队列: 缓冲处理结果
            result_queue = manager.Queue(maxsize=result_queue_size)

            # 进度队列: 进度报告
            progress_queue = manager.Queue()

            # 停止事件
            self._stop_event = manager.Event()

            # 3. 创建临时输出路径
            temp_output_path = self.output_path.replace(".", "_temp_pipeline.")

            # 4. 启动读取线程
            self.status.emit("📖 启动帧读取线程...")
            self._reader_thread = threading.Thread(
                target=frame_reader_worker,
                args=(
                    self.input_path,
                    frame_queue,
                    total_frames,
                    self._stop_event,
                ),
                daemon=True,
            )
            self._reader_thread.start()
            self.logger.info("Frame reader thread started")

            # 5. 启动处理进程池
            self.status.emit(f"🎨 启动 {self.num_processes} 个处理进程...")

            # ConfigParser 转字典
            config_dict = None
            if self.config:
                config_dict = {
                    section: dict(self.config[section]) for section in self.config.sections()
                }

            # 启动处理进程
            self._processor_pool = ProcessPoolExecutor(max_workers=self.num_processes)
            processor_futures = []

            for i in range(self.num_processes):
                future = self._processor_pool.submit(
                    frame_processor_worker,
                    frame_queue,
                    result_queue,
                    self.ai_params,
                    config_dict,
                    self._stop_event,
                    progress_queue,
                    i,  # worker_id
                )
                processor_futures.append(future)

            self.logger.info(f"{self.num_processes} processor workers started")

            # 6. 启动写入线程
            self.status.emit("💾 启动帧写入线程...")

            video_params = {
                "fps": fps,
                "width": width,
                "height": height,
                "fourcc": fourcc,
            }

            # 使用共享的结果容器
            writer_result = []

            def writer_wrapper():
                """包装 frame_writer_worker 以捕获返回值"""
                result = frame_writer_worker(
                    result_queue,
                    temp_output_path,
                    video_params,
                    total_frames,
                    self._stop_event,
                    progress_queue,
                )
                writer_result.append(result)

            self._writer_thread = threading.Thread(
                target=writer_wrapper,
                daemon=True,
            )
            self._writer_thread.start()
            self.logger.info("Frame writer thread started")

            # 7. 启动进度轮询
            self._progress_timer = QTimer()
            self._progress_timer.timeout.connect(
                lambda: self._check_pipeline_progress(progress_queue, total_frames)
            )
            self._progress_timer.start(100)  # 每100ms检查一次

            # 8. 等待所有线程/进程完成
            self.status.emit("⏳ 流水线处理中...")

            # 等待读取线程
            self._reader_thread.join()
            self.logger.info("Frame reader completed")

            # 等待处理进程
            for i, future in enumerate(processor_futures):
                future.result()  # 等待进程完成
            self.logger.info("All processor workers completed")

            # 等待写入线程
            self._writer_thread.join()
            self.logger.info("Frame writer completed")

            # 9. 检查写入结果
            if not writer_result:
                raise Exception("Writer thread failed to return result")

            success, error_msg = writer_result[0]
            if not success:
                raise Exception(f"Frame writer failed: {error_msg}")

            if error_msg:
                self.logger.warning(error_msg)

            # 10. 处理音频
            if self.ffmpeg_processor and self.ffmpeg_processor.is_available():
                self.status.emit("🎵 正在合并原始音频...")
                self.progress.emit(95)

                audio_success = self.ffmpeg_processor.process_video_with_audio_preservation(
                    original_video_path=self.input_path,
                    processed_video_path=temp_output_path,
                    final_output_path=self.output_path,
                )

                if audio_success:
                    self.logger.info("Audio merged successfully")
                    # 删除临时文件
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)
                else:
                    self.logger.warning("Audio merge failed, using video-only output")
                    # 重命名临时文件
                    if os.path.exists(temp_output_path):
                        if os.path.exists(self.output_path):
                            os.remove(self.output_path)
                        os.rename(temp_output_path, self.output_path)
            else:
                # 没有音频处理,直接使用临时文件
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                os.rename(temp_output_path, self.output_path)

            # 11. 完成
            self.progress.emit(100)
            self.status.emit(f"✅ 流水线处理完成! 处理了 {total_frames} 帧")
            self.logger.info(f"Pipeline video processing completed: {self.output_path}")

        except Exception as e:
            self.logger.error(f"Pipeline processing failed, falling back to chunk mode: {e}")
            self.status.emit("⚠️ 流水线失败，切换到分块模式")

            # 降级到分块处理
            self._process_video_multiprocess()

        finally:
            # 12. 清理资源
            if self._progress_timer:
                self._progress_timer.stop()
                self._progress_timer = None

            if self._stop_event:
                self._stop_event.set()
                self._stop_event = None

            # 等待线程/进程清理
            if self._reader_thread and self._reader_thread.is_alive():
                self._reader_thread.join(timeout=2)

            if self._writer_thread and self._writer_thread.is_alive():
                self._writer_thread.join(timeout=2)

            if self._processor_pool:
                self._processor_pool.shutdown(wait=False)
                self._processor_pool = None

            # 清空队列 (避免死锁)
            for queue in [frame_queue, result_queue, progress_queue]:
                if queue:
                    try:
                        while not queue.empty():
                            queue.get_nowait()
                    except Exception:
                        pass

    def _check_pipeline_progress(
        self, progress_queue: multiprocessing.Queue, total_frames: int
    ) -> None:
        """
        检查流水线进度队列并发送信号 (Phase 4 Stage 2.2)

        Args:
            progress_queue: 进度队列
            total_frames: 总帧数
        """
        try:
            while not progress_queue.empty():
                progress_data = progress_queue.get_nowait()

                # 处理不同类型的进度数据
                if "written_frames" in progress_data:
                    # 写入线程的进度
                    written = progress_data["written_frames"]
                    progress_pct = int((written / total_frames) * 95) + 5  # 5-100%
                    self.progress.emit(progress_pct)
                    self.status.emit(f"💾 写入进度: {written}/{total_frames} 帧")

                elif "worker_id" in progress_data:
                    # 处理进程的进度 (可选: 用于详细监控)
                    pass

        except Exception as e:
            self.logger.warning(f"Pipeline progress polling error: {e}")

    def _calculate_queue_sizes(self) -> Tuple[int, int]:
        """
        根据系统可用内存动态计算队列大小 (Phase 4 Stage 2.4)

        Returns:
            (frame_queue_size, result_queue_size)
        """
        try:
            import psutil

            available_mb = psutil.virtual_memory().available / (1024 * 1024)

            if available_mb < 4096:
                # 低端设备: < 4GB 可用内存
                self.logger.info(
                    f"Low memory detected ({available_mb:.0f}MB), using small queues (20+40)"
                )
                return (20, 40)
            elif available_mb < 8192:
                # 中端设备: 4-8GB 可用内存 (默认)
                self.logger.info(
                    f"Medium memory detected ({available_mb:.0f}MB), using medium queues (30+50)"
                )
                return (30, 50)
            else:
                # 高端设备: > 8GB 可用内存
                self.logger.info(
                    f"High memory detected ({available_mb:.0f}MB), using large queues (50+100)"
                )
                return (50, 100)

        except ImportError:
            # psutil 不可用,使用中等配置
            self.logger.warning("psutil not available, using default queue sizes (30+50)")
            return (30, 50)

        except Exception as e:
            self.logger.warning(f"Failed to detect memory: {e}, using default queue sizes (30+50)")
            return (30, 50)

    def _process_video_singleprocess(self) -> None:
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
