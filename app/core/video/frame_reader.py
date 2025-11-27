import logging
import multiprocessing

import cv2


def frame_reader_worker(
    video_path: str,
    frame_queue: multiprocessing.Queue,
    total_frames: int,
    stop_event: multiprocessing.Event,
) -> None:
    """
    帧读取工作线程

    Args:
        video_path: 视频路径
        frame_queue: 帧队列
        total_frames: 总帧数
        stop_event: 停止事件
    """
    logger = logging.getLogger(__name__)

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            frame_queue.put(None)
            return

        logger.info(f"Frame reader started: {total_frames} frames to read")

        for frame_index in range(total_frames):
            if stop_event.is_set():
                logger.info("Frame reader stopped by user request")
                break

            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Failed to read frame {frame_index}")
                break

            try:
                frame_queue.put((frame_index, frame), timeout=10)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Failed to put frame {frame_index} into queue: {e}")
                break

            if frame_index % 100 == 0:
                logger.debug(f"Frame reader: {frame_index}/{total_frames} frames read")

        frame_queue.put(None)
        logger.info("Frame reader completed")

    except Exception as e:  # noqa: BLE001
        logger.error(f"Frame reader error: {e}")
        frame_queue.put(None)

    finally:
        if cap:
            cap.release()
