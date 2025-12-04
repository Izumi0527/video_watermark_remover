import gc
import heapq
import logging
import time
from multiprocessing import queues, synchronize
from typing import Any, List, Optional, Tuple

import cv2


def frame_writer_worker(  # noqa: C901
    result_queue: queues.Queue,
    output_path: str,
    video_params: dict,
    total_frames: int,
    stop_event: synchronize.Event,
    progress_queue: queues.Queue,
) -> Tuple[bool, Optional[str]]:
    """
    帧写入工作线程 (Phase 4 Stage 2.2, 优化 Phase 4 Stage 2.4, Phase 6 优先队列优化)

    使用优先队列（最小堆）保证帧顺序写入，具有以下优势：
    1. O(log n) 插入，O(1) 取最小元素
    2. 自适应背压控制，减少不必要的休眠
    3. 更清晰的有序性语义

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

    # 缓冲区配置
    MAX_BUFFER_SIZE = 50  # 最大缓冲帧数
    MIN_SLEEP_MS = 1  # 最小休眠时间
    MAX_SLEEP_MS = 20  # 最大休眠时间

    out = None
    # 使用最小堆存储 (frame_index, frame_data) 元组
    frame_heap: List[Tuple[int, Any]] = []
    next_frame_index = 0
    received_count = 0

    def _adaptive_sleep(buffer_fill_ratio: float) -> None:
        """自适应休眠，根据缓冲区填充率调整休眠时间"""
        # 填充率越高，休眠时间越长，给写入更多时间
        sleep_ms = MIN_SLEEP_MS + int((MAX_SLEEP_MS - MIN_SLEEP_MS) * buffer_fill_ratio)
        time.sleep(sleep_ms / 1000.0)

    def _write_sequential_frames() -> int:
        """从堆中写入所有可以顺序写入的帧，返回写入的帧数"""
        nonlocal next_frame_index
        written = 0

        while frame_heap and frame_heap[0][0] == next_frame_index:
            _, frame = heapq.heappop(frame_heap)
            out.write(frame)
            del frame
            next_frame_index += 1
            written += 1

        return written

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
                # 自适应背压控制
                buffer_size = len(frame_heap)
                if buffer_size >= MAX_BUFFER_SIZE:
                    # 先尝试写入可写的帧
                    _write_sequential_frames()

                    # 如果仍然满，使用自适应休眠
                    if len(frame_heap) >= MAX_BUFFER_SIZE:
                        fill_ratio = len(frame_heap) / MAX_BUFFER_SIZE
                        _adaptive_sleep(fill_ratio)
                        continue

                item = result_queue.get(timeout=1)

                if item is None:
                    logger.info("Frame writer received end signal")
                    break

                frame_index, processed_frame = item
                # 使用堆插入，保持有序性
                heapq.heappush(frame_heap, (frame_index, processed_frame))
                received_count += 1

                # 尝试写入所有可顺序写入的帧
                written = _write_sequential_frames()

                # 定期报告进度
                if written > 0 and next_frame_index % 10 == 0:
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

                # 定期GC
                if next_frame_index % 50 == 0:
                    gc.collect()

            except Exception as e:  # noqa: BLE001
                if "timeout" not in str(e).lower():
                    logger.warning(f"Frame writer error: {e}")
                continue

        # 写入剩余的帧
        while frame_heap and not stop_event.is_set():
            if frame_heap[0][0] == next_frame_index:
                _, frame = heapq.heappop(frame_heap)
                out.write(frame)
                del frame
                next_frame_index += 1
            else:
                # 有缺失的帧，等待或放弃
                break

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
        # 清理剩余缓冲区
        frame_heap.clear()
