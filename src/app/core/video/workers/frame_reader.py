import logging
import queue
from multiprocessing import queues, synchronize
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray


def _put_frame_with_stop_awareness(
    frame_queue: queues.Queue,
    frame_index: int,
    frame: NDArray[np.uint8],
    stop_event: synchronize.Event,
    logger: logging.Logger,
) -> bool:
    """在背压场景下快速响应取消请求，避免 stop 时长时间阻塞。"""
    while not stop_event.is_set():
        try:
            frame_queue.put((frame_index, frame), timeout=0.2)
            return True
        except queue.Full:
            continue
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to put frame %s into queue: %r", frame_index, exc)
            return False
    return False


def _put_end_signal(frame_queue: queues.Queue, logger: logging.Logger) -> None:
    """发送读取结束信号；失败仅记录调试信息。"""
    try:
        frame_queue.put(None, timeout=1)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Frame reader end signal skipped: %r", exc, exc_info=True)


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
            _put_end_signal(frame_queue, logger)
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

            if not _put_frame_with_stop_awareness(
                frame_queue, frame_index, frame, stop_event, logger
            ):
                if stop_event.is_set():
                    logger.info(
                        "Frame reader stopping while waiting queue slot at frame %s", frame_index
                    )
                else:
                    logger.error("Failed to put frame %s into queue", frame_index)
                break

            if frame_index % 100 == 0:
                logger.debug(f"Frame reader: {frame_index}/{total_frames} frames read")

        _put_end_signal(frame_queue, logger)
        logger.info("Frame reader completed")

    except Exception as e:  # noqa: BLE001
        logger.error(f"Frame reader error: {e!r}")
        _put_end_signal(frame_queue, logger)

    finally:
        if cap:
            cap.release()
