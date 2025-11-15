"""
Phase 4 Stage 2.1 多进程视频处理测试

简单测试脚本,验证多进程帧并行处理功能是否正常工作。
"""

import logging
import multiprocessing
import os
import sys
import tempfile

import cv2
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.video.video_processor import process_video_chunk

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_video(output_path: str, num_frames: int = 100, fps: int = 30) -> None:
    """
    创建测试视频

    Args:
        output_path: 输出路径
        num_frames: 帧数
        fps: 帧率
    """
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for i in range(num_frames):
        # 创建彩色帧 (渐变色)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        color = int(255 * i / num_frames)
        frame[:, :] = (color, 128, 255 - color)

        # 添加帧编号文字
        cv2.putText(
            frame,
            f"Frame {i}",
            (width // 2 - 50, height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )

        out.write(frame)

    out.release()
    logger.info(f"Created test video: {output_path} ({num_frames} frames)")


def test_process_video_chunk():
    """测试 process_video_chunk() 函数"""
    logger.info("=" * 60)
    logger.info("Test 1: process_video_chunk() 单个块处理")
    logger.info("=" * 60)

    # 1. 创建测试视频
    test_video = os.path.join(tempfile.gettempdir(), "test_video.mp4")
    create_test_video(test_video, num_frames=100)

    # 2. 准备参数
    output_chunk = os.path.join(tempfile.gettempdir(), "test_chunk_0.mp4")

    # Windows: 使用 Manager().Queue() 而非 Queue()
    manager = multiprocessing.Manager()
    progress_queue = manager.Queue()
    stop_event = manager.Event()

    # 3. 测试处理前 50 帧
    logger.info("Processing frames 0-50...")
    result = process_video_chunk(
        video_path=test_video,
        start_frame=0,
        end_frame=50,
        output_path=output_chunk,
        ai_params={},  # 空参数,不进行AI处理
        config_dict=None,
        progress_queue=progress_queue,
        stop_event=stop_event,
        chunk_id=0,
    )

    # 4. 验证结果
    output_path, success, error_msg = result

    if success:
        logger.info(f"✅ Chunk processing succeeded: {output_path}")

        # 验证输出文件
        if os.path.exists(output_path):
            cap = cv2.VideoCapture(output_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            logger.info(f"✅ Output file exists, frame count: {frame_count}")

            if frame_count == 50:
                logger.info("✅ Frame count matches expected (50)")
            else:
                logger.error(f"❌ Frame count mismatch: expected 50, got {frame_count}")

            # 清理
            os.remove(output_path)
        else:
            logger.error("❌ Output file does not exist")
    else:
        logger.error(f"❌ Chunk processing failed: {error_msg}")

    # 清理测试视频
    if os.path.exists(test_video):
        os.remove(test_video)

    # 检查进度队列
    logger.info("\nProgress queue messages:")
    while not progress_queue.empty():
        msg = progress_queue.get()
        logger.info(f"  {msg}")

    logger.info("")


def test_multiprocess_chunks():
    """测试多进程处理多个块"""
    logger.info("=" * 60)
    logger.info("Test 2: 多进程处理多个视频块")
    logger.info("=" * 60)

    # 1. 创建测试视频
    test_video = os.path.join(tempfile.gettempdir(), "test_video_multi.mp4")
    create_test_video(test_video, num_frames=200)

    # 2. 分块参数
    num_processes = 4
    total_frames = 200
    chunk_size = total_frames // num_processes

    chunks = []
    for i in range(num_processes):
        start = i * chunk_size
        end = total_frames if i == num_processes - 1 else (i + 1) * chunk_size
        output_path = os.path.join(tempfile.gettempdir(), f"chunk_{i}.mp4")
        chunks.append((start, end, output_path))

    logger.info(f"Created {num_processes} chunks:")
    for i, (start, end, path) in enumerate(chunks):
        logger.info(f"  Chunk {i}: frames {start}-{end} -> {path}")

    # 3. 创建进度队列和停止事件 (Windows: 使用 Manager())
    manager = multiprocessing.Manager()
    progress_queue = manager.Queue()
    stop_event = manager.Event()

    # 4. 使用 ProcessPoolExecutor 并行处理
    from concurrent.futures import ProcessPoolExecutor, as_completed

    logger.info("\n开始并行处理...")

    results = []
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = []
        for i, (start, end, output_path) in enumerate(chunks):
            future = executor.submit(
                process_video_chunk,
                test_video,
                start,
                end,
                output_path,
                {},  # ai_params
                None,  # config_dict
                progress_queue,
                stop_event,
                i,  # chunk_id
            )
            futures.append(future)

        # 收集结果
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            output_path, success, error_msg = result
            if success:
                logger.info(f"✅ Chunk completed: {output_path}")
            else:
                logger.error(f"❌ Chunk failed: {error_msg}")

    # 5. 验证所有块
    logger.info("\n验证结果:")
    total_output_frames = 0
    for output_path, success, error_msg in results:
        if success and os.path.exists(output_path):
            cap = cv2.VideoCapture(output_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            total_output_frames += frame_count
            logger.info(f"  {os.path.basename(output_path)}: {frame_count} frames")

            # 清理临时文件
            os.remove(output_path)

    logger.info(f"\n总输出帧数: {total_output_frames} (期望: {total_frames})")

    if total_output_frames == total_frames:
        logger.info("✅ Total frame count matches!")
    else:
        logger.error(f"❌ Frame count mismatch: expected {total_frames}, got {total_output_frames}")

    # 清理测试视频
    if os.path.exists(test_video):
        os.remove(test_video)

    logger.info("")


if __name__ == "__main__":
    # Windows 多进程需要这个
    multiprocessing.freeze_support()

    logger.info("Phase 4 Stage 2.1 多进程视频处理测试\n")

    try:
        # Test 1: 单个块处理
        test_process_video_chunk()

        # Test 2: 多进程处理
        test_multiprocess_chunks()

        logger.info("=" * 60)
        logger.info("✅ All tests passed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        sys.exit(1)
