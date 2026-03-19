import os

import cv2

from ..exceptions import ModelLoadError, VideoReadError, VideoWriteError
from .path_utils import build_temp_path


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

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(processor.output_path, fourcc, fps, (frame_width, frame_height))

        if not out.isOpened():
            raise VideoWriteError("无法创建输出视频文件", details=f"输出路径: {processor.output_path}")

        processor.progress.emit(10)

        processing_params = {
            "auto_detect": processor.ai_params.get("auto_detect", True),
            "detection_sensitivity": processor.ai_params.get("detection_sensitivity", 0.5),
            "user_mask": processor.ai_params.get("user_mask", None),
        }

        current_frame = 0
        processed_frames = 0
        total_watermark_areas = 0
        last_preview_frame = None

        processor._emit_detailed_progress("processing_frames", 0, total_frames)

        while processor._is_running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_frame += 1

            if processor.ai_handler is None:
                raise ModelLoadError("AI handler not initialized")

            processed_frame, processing_info = processor.ai_handler.process_frame(
                frame, processing_params
            )
            last_preview_frame = processed_frame

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

        if processor.ffmpeg_processor and processor.ffmpeg_processor.is_available():
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
        processor.logger.info(
            f"Video processing completed: {processed_frames}/{current_frame} frames processed, "
            f"{total_watermark_areas} total watermark areas found"
        )

        audio_status = (
            "含音频"
            if (processor.ffmpeg_processor and processor.ffmpeg_processor.is_available())
            else "无音频"
        )
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
