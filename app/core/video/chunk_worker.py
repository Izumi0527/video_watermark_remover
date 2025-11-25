# flake8: noqa
# mypy: ignore-errors
import logging
import multiprocessing
from typing import Optional, Tuple

import cv2

from ..ai.ai_handler import AIHandler


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
        ai_handler = AIHandler(None, ai_params)
        if not ai_handler.load_models():
            return (None, False, "AI 模型加载失败")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return (None, False, "无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            logger.warning(f"Chunk {chunk_id}: mp4v codec failed, trying XVID")
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            if not out.isOpened():
                cap.release()
                return (
                    None,
                    False,
                    f"无法创建输出文件（尝试了 mp4v 和 XVID 编码器）: {output_path}",
                )

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        total_frames_in_chunk = end_frame - start_frame
        processed_count = 0

        for i in range(total_frames_in_chunk):
            if stop_event.is_set():
                logger.info(f"Chunk {chunk_id} stopped by user request")
                break

            ret, frame = cap.read()
            if not ret:
                break

            try:
                processing_params = {
                    "auto_detect": ai_params.get("auto_detect", True),
                    "detection_sensitivity": ai_params.get("detection_sensitivity", 0.5),
                    "user_mask": ai_params.get("user_mask", None),
                }
                processed_frame, _ = ai_handler.process_frame(frame, processing_params)
                out.write(processed_frame)
                processed_count += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Frame processing error in chunk {chunk_id}: {e}")
                out.write(frame)

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
                    pass

        cap.release()
        out.release()

        logger.info(f"Chunk {chunk_id} completed: {processed_count}/{total_frames_in_chunk} frames")
        return (output_path, True, None)

    except Exception as e:  # noqa: BLE001
        error_msg = f"Chunk {chunk_id} error: {str(e)}"
        logger.error(error_msg)
        return (None, False, error_msg)
