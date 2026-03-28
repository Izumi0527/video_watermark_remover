import os
import time

import cv2

from ....config.advanced_params import (
    build_processing_mode_runtime_hint,
    build_processing_mode_runtime_summary,
)
from ...exceptions import ModelLoadError, VideoReadError, VideoWriteError
from ..output_strategy import create_video_writer, should_preserve_audio
from ..utils.path import build_temp_path

_RUNTIME_HEARTBEAT_INTERVAL_SECONDS = 15.0


def _resolve_detection_batch_size(processor, processing_params: dict) -> int:
    """解析单进程自动检测场景下的小批量窗口大小。"""
    if not bool(processing_params.get("auto_detect", False)):
        return 1
    if processing_params.get("user_mask") is not None:
        return 1

    ai_handler = getattr(processor, "ai_handler", None)
    if ai_handler is None or not hasattr(ai_handler, "process_frames_batch"):
        return 1

    detector = getattr(ai_handler, "watermark_detector", None)
    if detector is None:
        return 1

    try:
        batch_size = int(getattr(detector, "batch_size", 1) or 1)
    except (TypeError, ValueError):
        return 1
    return max(1, batch_size)


def _read_frame_batch(cap, batch_size: int) -> list:
    """从视频流中读取一小批帧，保持原始顺序。"""
    frames = []
    for _ in range(max(1, batch_size)):
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    return frames


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _maybe_log_runtime_heartbeat(processor, *, current_frame: int, total_frames: int) -> None:
    now = time.time()
    last_log_at = float(getattr(processor, "_last_runtime_heartbeat_at", 0.0) or 0.0)
    if now - last_log_at < _RUNTIME_HEARTBEAT_INTERVAL_SECONDS:
        return

    setattr(processor, "_last_runtime_heartbeat_at", now)
    started_at = float(getattr(processor, "_start_time", 0.0) or 0.0)
    elapsed = max(0.0, now - started_at)
    speed = (current_frame / elapsed) if elapsed > 0 else 0.0
    eta = 0.0
    if speed > 0 and total_frames > current_frame:
        eta = (total_frames - current_frame) / speed

    runtime_summary = build_processing_mode_runtime_summary(
        requested_mode=getattr(processor, "requested_runtime_processing_mode", None),
        resolved_mode=getattr(processor, "runtime_processing_mode", None),
    )
    runtime_hint = build_processing_mode_runtime_hint(
        getattr(processor, "runtime_processing_guard_reason", None)
    )
    hint_suffix = f"；{runtime_hint}" if runtime_hint else ""
    progress_percentage = int((current_frame / total_frames) * 100) if total_frames > 0 else 0
    processor.logger.info(
        "单进程处理心跳: frame=%s/%s progress=%s%% speed=%.2f fps eta=%s %s%s",
        current_frame,
        total_frames,
        progress_percentage,
        speed,
        _format_duration(eta),
        runtime_summary,
        hint_suffix,
    )


def process_video_singleprocess(processor) -> None:  # noqa: C901
    """
    单进程逐帧处理视频。
    """
    cap = None
    out = None

    try:
        processor.status.emit("🎬 读取视频文件...")
        cap = cv2.VideoCapture(processor.input_path)

        if not cap.isOpened():
            raise VideoReadError("无法打开视频文件", details=f"文件路径: {processor.input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        processor.logger.info(
            f"Video properties: {frame_width}x{frame_height}, {fps} fps, {total_frames} frames"
        )

        out, selected_codec = create_video_writer(
            processor.output_path,
            fps,
            (frame_width, frame_height),
            cv2_module=cv2,
        )

        if out is None or not out.isOpened():
            raise VideoWriteError("无法创建输出视频文件", details=f"输出路径: {processor.output_path}")
        processor.logger.info("Video writer codec selected: %s", selected_codec)

        processor.progress.emit(10)

        processing_params = {
            "auto_detect": processor.ai_params.get("auto_detect", True),
            "detection_sensitivity": processor.ai_params.get("detection_sensitivity", 0.5),
            "user_mask": processor.ai_params.get("user_mask", None),
        }
        detection_batch_size = _resolve_detection_batch_size(processor, processing_params)

        current_frame = 0
        processed_frames = 0
        total_watermark_areas = 0
        last_preview_frame = None
        last_effective_processing_info = None

        processor._emit_detailed_progress("processing_frames", 0, total_frames)

        while processor._is_running and cap.isOpened():
            frame_batch = _read_frame_batch(cap, detection_batch_size)
            if not frame_batch:
                break

            if processor.ai_handler is None:
                raise ModelLoadError("AI handler not initialized")

            if detection_batch_size > 1 and hasattr(processor.ai_handler, "process_frames_batch"):
                batch_results = processor.ai_handler.process_frames_batch(
                    frame_batch, processing_params
                )
            else:
                batch_results = [
                    processor.ai_handler.process_frame(frame, processing_params)
                    for frame in frame_batch
                ]

            for frame, result in zip(frame_batch, batch_results):
                processed_frame, processing_info = result
                current_frame += 1
                last_preview_frame = processed_frame

                # 记录最后一次处理信息，便于批处理清单导出追溯
                processor.last_processing_info = processing_info
                if (
                    isinstance(processing_info, dict)
                    and "error" not in processing_info
                    and int(processing_info.get("watermark_areas_found", 0) or 0) > 0
                ):
                    last_effective_processing_info = processing_info
                    processor.last_effective_processing_info = processing_info

                if "error" in processing_info:
                    processor.logger.warning(
                        f"Frame {current_frame} processing error: {processing_info['error']}"
                    )
                    processed_frame = frame
                else:
                    processed_frames += 1
                    total_watermark_areas += processing_info.get("watermark_areas_found", 0)

                out.write(processed_frame)

                if total_frames > 0:
                    progress_percentage = int((current_frame / total_frames) * 90) + 10
                    processor.progress.emit(progress_percentage)

                if current_frame % max(1, int(fps)) == 0:
                    processor.status.emit(f"🎨 处理中: {current_frame}/{total_frames} 帧")

                if current_frame % max(1, int(fps / 10)) == 0:
                    processor._emit_detailed_progress(
                        "processing_frames",
                        current_frame,
                        total_frames,
                        {
                            "processed_frames": processed_frames,
                            "total_watermark_areas": total_watermark_areas,
                        },
                    )

                _maybe_log_runtime_heartbeat(
                    processor,
                    current_frame=current_frame,
                    total_frames=total_frames,
                )

                if current_frame == 1 or current_frame % 30 == 0 or current_frame == total_frames:
                    processor.preview_update.emit(processed_frame)

        if last_preview_frame is not None:
            processor.preview_update.emit(last_preview_frame)
        else:
            processor.preview_update.emit(None)

        if not processor._is_running:
            processor.status.emit("⚠️ 处理已取消")
            if out:
                out.release()
                out = None
            if os.path.exists(processor.output_path):
                try:
                    os.remove(processor.output_path)
                except Exception as e:  # noqa: BLE001
                    processor.logger.warning(f"取消处理时删除输出文件失败: {e}")
            processor.finished.emit("")
            return

        if out:
            out.release()
            out = None

        temp_video_path = processor.output_path
        final_output_path = processor.output_path

        audio_preservation_enabled = should_preserve_audio(processor.ai_params)
        audio_preserved = False
        if (
            audio_preservation_enabled
            and processor.ffmpeg_processor
            and processor.ffmpeg_processor.is_available()
        ):
            temp_video_path = build_temp_path(processor.output_path, "temp_video")

            if os.path.exists(processor.output_path):
                os.replace(processor.output_path, temp_video_path)

            processor._emit_detailed_progress("merging_audio", 0, 1)
            processor.status.emit("🎵 正在合并原始音频...")
            processor.progress.emit(95)

            audio_success = processor.ffmpeg_processor.process_video_with_audio_preservation(
                original_video_path=processor.input_path,
                processed_video_path=temp_video_path,
                final_output_path=final_output_path,
            )

            if audio_success:
                audio_preserved = True
                processor.logger.info("Audio merged successfully")
                processor._emit_detailed_progress("merging_audio", 1, 1)
                processor.status.emit("✅ 音频合并完成")
            else:
                processor.logger.warning("Audio merge failed, using video-only output")
                processor.status.emit("⚠️ 音频合并失败，使用无音频版本")
                if os.path.exists(temp_video_path):
                    if os.path.exists(final_output_path):
                        os.remove(final_output_path)
                    os.replace(temp_video_path, final_output_path)

            if os.path.exists(temp_video_path) and temp_video_path != final_output_path:
                try:
                    os.remove(temp_video_path)
                except Exception as e:  # noqa: BLE001
                    processor.logger.warning(f"Failed to clean up temp file: {e}")

        processor.progress.emit(100)
        if isinstance(last_effective_processing_info, dict) and last_effective_processing_info:
            processor.last_effective_processing_info = last_effective_processing_info

        processor.last_processing_summary = {
            "media_type": "video",
            "mode": "singleprocess",
            "frames_total": int(total_frames or 0),
            "frames_read": int(current_frame or 0),
            "frames_processed": int(processed_frames or 0),
            "total_watermark_areas": int(total_watermark_areas or 0),
        }
        processor.logger.info(
            f"Video processing completed: {processed_frames}/{current_frame} frames processed, "
            f"{total_watermark_areas} total watermark areas found"
        )

        audio_status = "含音频" if audio_preserved else "无音频"
        processor.status.emit(f"✅ 视频处理完成! 处理了 {processed_frames} 帧 ({audio_status})")
        processor.finished.emit(final_output_path)

    except Exception as e:  # noqa: BLE001
        processor.logger.error(f"Video processing error: {e}")
        processor.error.emit(f"视频处理失败: {str(e)}")

    finally:
        if cap:
            cap.release()
        if out:
            out.release()
