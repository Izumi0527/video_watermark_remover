"""
Phase 4 Stage 2.2 流水线视频处理测试

测试 3 阶段流水线: 读取线程 → 处理进程池 → 写入线程
"""

import logging
import multiprocessing
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
pytest.importorskip("PyQt6")

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.video.workers import frame_processor as frame_processor_module
from app.core.video.workers.frame_processor import frame_processor_worker
from app.core.video.workers.frame_reader import frame_reader_worker
from app.core.video.workers.frame_writer import frame_writer_worker

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
RUNTIME_ROOT = Path(__file__).resolve().parents[2] / ".cache" / "tests" / "integration" / "pipeline"


class DummyAIHandler:
    """轻量级 AI 处理器，直接透传输入帧。"""

    def __init__(self, *_args, **_kwargs):
        pass

    def load_models(self):
        return True

    def process_frame(self, frame, params=None):
        return frame.copy(), {"watermark_areas_found": 0, "processing_time": 0.0}


frame_processor_module.AIHandler = DummyAIHandler


def create_runtime_dir() -> str:
    """创建项目内测试运行目录，避免系统临时目录权限问题。"""
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    runtime_dir = RUNTIME_ROOT / f"pipeline_video_{uuid.uuid4().hex}"
    runtime_dir.mkdir()
    return str(runtime_dir)


def create_test_video(output_path: str, num_frames: int = 100, fps: int = 30) -> None:
    """创建测试视频"""
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for i in range(num_frames):
        # 创建彩色帧
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        color = int(255 * i / num_frames)
        frame[:, :] = (color, 128, 255 - color)

        # 添加帧编号
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


def test_pipeline_workers():
    """测试流水线工作函数"""
    logger.info("=" * 60)
    logger.info("测试流水线工作函数")
    logger.info("=" * 60)

    # 1. 创建测试视频
    runtime_dir = create_runtime_dir()
    test_video = os.path.join(runtime_dir, "test_pipeline_video.mp4")
    num_frames = 100
    create_test_video(test_video, num_frames=num_frames)

    # 2. 准备参数
    output_video = os.path.join(runtime_dir, "test_pipeline_output.mp4")

    # 创建线程安全队列，避免 Windows Manager/named pipe 权限问题
    frame_queue = Queue(maxsize=20)
    result_queue = Queue(maxsize=20)
    progress_queue = Queue()
    stop_event = threading.Event()

    # 获取视频信息
    cap = cv2.VideoCapture(test_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    logger.info(f"Video: {width}x{height}, {fps} fps, {total_frames} frames")

    # 3. 启动读取线程
    logger.info("启动读取线程...")
    reader_thread = threading.Thread(
        target=frame_reader_worker,
        args=(test_video, frame_queue, total_frames, stop_event),
        daemon=True,
    )
    reader_thread.start()

    # 4. 启动处理进程 (2个进程)
    logger.info("启动处理进程...")
    num_processes = 2
    processor_pool = ThreadPoolExecutor(max_workers=num_processes)
    processor_futures = []

    for i in range(num_processes):
        future = processor_pool.submit(
            frame_processor_worker,
            frame_queue,
            result_queue,
            {},  # ai_params (空,不进行AI处理,只传递帧)
            None,  # config_dict
            stop_event,
            progress_queue,
            i,  # worker_id
        )
        processor_futures.append(future)

    # 5. 启动写入线程
    logger.info("启动写入线程...")
    video_params = {
        "fps": fps,
        "width": width,
        "height": height,
        "fourcc": fourcc,
    }

    writer_result = []

    def writer_wrapper():
        result = frame_writer_worker(
            result_queue,
            output_video,
            video_params,
            total_frames,
            stop_event,
            progress_queue,
        )
        writer_result.append(result)

    writer_thread = threading.Thread(target=writer_wrapper, daemon=True)
    writer_thread.start()

    # 6. 监控进度
    logger.info("等待流水线完成...")
    start_time = time.time()

    # 等待读取线程
    reader_thread.join()
    logger.info("✅ 读取线程完成")

    # 等待处理进程
    for future in processor_futures:
        future.result()
    logger.info("✅ 处理进程完成")

    # 等待写入线程
    writer_thread.join()
    logger.info("✅ 写入线程完成")

    elapsed_time = time.time() - start_time

    # 7. 验证结果
    logger.info("\n验证结果:")

    if not writer_result:
        if os.path.exists(runtime_dir):
            import shutil

            shutil.rmtree(runtime_dir, ignore_errors=True)
        pytest.fail("写入线程未返回结果")

    success, error_msg = writer_result[0]

    if not success:
        logger.error(f"❌ 写入失败: {error_msg}")
        if os.path.exists(runtime_dir):
            import shutil

            shutil.rmtree(runtime_dir, ignore_errors=True)
        pytest.fail(f"写入失败: {error_msg}")

    if error_msg:
        logger.warning(f"⚠️ 警告: {error_msg}")

    # 验证输出文件
    if not os.path.exists(output_video):
        if os.path.exists(runtime_dir):
            import shutil

            shutil.rmtree(runtime_dir, ignore_errors=True)
        pytest.fail("输出文件不存在")

    cap = cv2.VideoCapture(output_video)
    output_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    logger.info(f"输出文件: {output_video}")
    logger.info(f"输出帧数: {output_frames}/{total_frames}")
    logger.info(f"处理时间: {elapsed_time:.2f} 秒")
    logger.info(f"处理速度: {total_frames / elapsed_time:.2f} fps")

    # 清理
    for file in [test_video, output_video]:
        if os.path.exists(file):
            os.remove(file)

    # 检查帧数
    frame_count_matches = output_frames == total_frames
    if frame_count_matches:
        logger.info("✅ 帧数匹配!")
    else:
        logger.error(f"❌ 帧数不匹配: 期望 {total_frames}, 实际 {output_frames}")

    if os.path.exists(runtime_dir):
        import shutil

        shutil.rmtree(runtime_dir, ignore_errors=True)

    assert frame_count_matches, f"帧数不匹配: 期望 {total_frames}, 实际 {output_frames}"


if __name__ == "__main__":
    # Windows 多进程需要这个
    multiprocessing.freeze_support()

    logger.info("Phase 4 Stage 2.2 流水线视频处理测试\n")

    try:
        success = test_pipeline_workers()

        logger.info("\n" + "=" * 60)
        if success:
            logger.info("✅ 测试通过!")
        else:
            logger.error("❌ 测试失败!")
        logger.info("=" * 60)

        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"❌ 测试异常: {e}", exc_info=True)
        sys.exit(1)
