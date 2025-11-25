import gc
import logging
import multiprocessing
import time
from typing import Optional, Tuple

import cv2


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
    MAX_BUFFER_SIZE = 50

    out = None
    frame_buffer = {}
    next_frame_index = 0
    received_count = 0

    try:
        fps = video_params["fps"]
        width = video_params["width"]
        height = video_params["height"]

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            logger.warning("mp4v codec failed, trying XVID")
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            if not out.isOpened():
                error_msg = f"Failed to create video writer (tried mp4v and XVID): {output_path}"
                logger.error(error_msg)
                return (False, error_msg)

        logger.info(f"Frame writer started: writing to {output_path}")

        while received_count < total_frames and not stop_event.is_set():
            try:
                while len(frame_buffer) >= MAX_BUFFER_SIZE and not stop_event.is_set():
                    time.sleep(0.01)

                item = result_queue.get(timeout=1)

                if item is None:
                    logger.info("Frame writer received end signal")
                    break

                frame_index, processed_frame = item
                frame_buffer[frame_index] = processed_frame
                received_count += 1

                while next_frame_index in frame_buffer:
                    frame = frame_buffer.pop(next_frame_index)
                    out.write(frame)
                    del frame
                    next_frame_index += 1

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

                    if next_frame_index % 50 == 0:
                        gc.collect()

            except Exception as e:  # noqa: BLE001
                if "timeout" not in str(e).lower():
                    logger.warning(f"Frame writer error: {e}")
                continue

        while next_frame_index < total_frames and next_frame_index in frame_buffer:
            frame = frame_buffer.pop(next_frame_index)
            out.write(frame)
            del frame
            next_frame_index += 1

        logger.info(f"Frame writer completed: {next_frame_index}/{total_frames} frames written")

        if next_frame_index < total_frames:
            warning_msg = f"Warning: Only {next_frame_index}/{total_frames} frames written"
            logger.warning(warning_msg)
            return (True, warning_msg)

        return (True, None)

    except Exception as e:  # noqa: BLE001
        error_msg = f"Frame writer fatal error: {str(e)}"
        logger.error(error_msg)
        return (False, error_msg)

    finally:
        if out:
            out.release()
