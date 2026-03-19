import logging
from multiprocessing import queues, synchronize
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray


def extract_video_first_frame(video_path: str) -> Optional[NDArray[np.uint8]]:
    """
    提取视频第一帧

    Args:
        video_path: 视频文件路径

    Returns:
        RGB格式的第一帧图像，如果提取失败则返回None
    """
    logger = logging.getLogger(__name__)
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video file: {video_path}")
            return None

        ret, frame = cap.read()
        if not ret:
            logger.warning(f"Failed to read first frame from video: {video_path}")
            return None

        # OpenCV读取的是BGR格式，需要转换为RGB
        frame_rgb: NDArray[np.uint8] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        logger.info(f"Successfully extracted first frame from video: {video_path}")
        return frame_rgb

    except Exception as e:
        logger.error(f"Error extracting video first frame: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()


def extract_video_frame_at(video_path: str, frame_index: int) -> Optional[NDArray[np.uint8]]:
    """
    提取视频指定帧

    Args:
        video_path: 视频文件路径
        frame_index: 帧索引（从0开始）

    Returns:
        RGB格式的指定帧图像，如果提取失败则返回None
    """
    logger = logging.getLogger(__name__)
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video file: {video_path}")
            return None

        # 设置帧位置
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        ret, frame = cap.read()
        if not ret:
            logger.warning(f"Failed to read frame {frame_index} from video: {video_path}")
            return None

        # OpenCV读取的是BGR格式，需要转换为RGB
        frame_rgb: NDArray[np.uint8] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        logger.debug(f"Successfully extracted frame {frame_index} from video: {video_path}")
        return frame_rgb

    except Exception as e:
        logger.error(f"Error extracting video frame at {frame_index}: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()


def frame_reader_worker(
    video_path: str,
    frame_queue: queues.Queue,
    total_frames: int,
    stop_event: synchronize.Event,
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
