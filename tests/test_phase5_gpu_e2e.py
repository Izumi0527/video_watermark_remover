"""
Phase 5 GPU 加速端到端测试

测试完整的 GPU 加速视频处理流水线（多进程 + GPU）
"""

import logging
import os
import sys
import time

import pytest

pytest.importorskip("PyQt6")
pytest.importorskip("cv2")
pytest.importorskip("numpy")

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtCore import QCoreApplication  # noqa: E402

from app.core.video.video_processor import VideoProcessorThread  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    print("=" * 60)
    print("Phase 5 GPU 加速端到端测试")
    print("=" * 60)
    print()

    # 创建 Qt 应用 (VideoProcessorThread 需要)
    app = QCoreApplication(sys.argv)

    # 输入输出路径
    input_video = "test_media/sample_video.mp4"  # 需要提前准备测试视频
    output_cpu = "test_media/output_cpu_multiprocess.mp4"
    output_gpu = "test_media/output_gpu_multiprocess.mp4"

    # 检查测试视频是否存在
    if not os.path.exists(input_video):
        logger.error(f"测试视频不存在: {input_video}")
        logger.info("请在 test_media/ 目录下放置测试视频 sample_video.mp4")
        return

    # ========================================
    # 测试 1: CPU 多进程模式 (Phase 4 Baseline)
    # ========================================
    print("=" * 60)
    print("测试 1: CPU 多进程模式 (Phase 4 Baseline)")
    print("=" * 60)

    ai_params_cpu = {
        "use_gpu_inpainting": False,  # 使用 CPU OpenCV
        "auto_detect": True,
        "detection_sensitivity": 0.5,
    }

    logger.info("创建 CPU 多进程处理器...")
    cpu_processor = VideoProcessorThread(
        input_path=input_video,
        output_path=output_cpu,
        ai_params=ai_params_cpu,
        config=None,
        enable_multiprocess=True,  # 启用多进程
        num_processes=4,  # 4 个进程
        use_pipeline=True,  # 使用流水线
    )

    # 连接信号
    cpu_completed = False
    cpu_time = 0

    def on_cpu_finished(output_path):
        nonlocal cpu_completed
        cpu_completed = True
        logger.info(f"CPU 处理完成: {output_path}")

    def on_cpu_error(error_msg):
        logger.error(f"CPU 处理错误: {error_msg}")

    def on_cpu_progress(progress_data):
        if "processing_speed" in progress_data:
            logger.info(
                f"[CPU] 进度: {progress_data.get('percent', 0):.1f}%, "
                f"速度: {progress_data.get('processing_speed', 0):.2f} fps"
            )

    cpu_processor.finished.connect(on_cpu_finished)
    cpu_processor.error.connect(on_cpu_error)
    cpu_processor.detailed_progress.connect(on_cpu_progress)

    # 启动处理
    logger.info("启动 CPU 多进程处理...")
    start_cpu = time.time()
    cpu_processor.start()

    # 等待完成 (简单轮询)
    while not cpu_completed:
        app.processEvents()
        time.sleep(0.1)

    cpu_time = time.time() - start_cpu
    print(f"\nCPU 多进程处理完成: {cpu_time:.2f} 秒")
    print()

    # ========================================
    # 测试 2: GPU 多进程模式 (Phase 5)
    # ========================================
    print("=" * 60)
    print("测试 2: GPU 多进程模式 (Phase 5)")
    print("=" * 60)

    ai_params_gpu = {
        "use_gpu_inpainting": True,  # 启用 GPU 深度学习
        "auto_detect": True,
        "detection_sensitivity": 0.5,
    }

    logger.info("创建 GPU 多进程处理器...")
    gpu_processor = VideoProcessorThread(
        input_path=input_video,
        output_path=output_gpu,
        ai_params=ai_params_gpu,
        config=None,
        enable_multiprocess=True,  # 启用多进程
        num_processes=4,  # 4 个进程，每个进程独立加载 GPU 模型
        use_pipeline=True,  # 使用流水线
    )

    # 连接信号
    gpu_completed = False
    gpu_time = 0

    def on_gpu_finished(output_path):
        nonlocal gpu_completed
        gpu_completed = True
        logger.info(f"GPU 处理完成: {output_path}")

    def on_gpu_error(error_msg):
        logger.error(f"GPU 处理错误: {error_msg}")

    def on_gpu_progress(progress_data):
        if "processing_speed" in progress_data:
            logger.info(
                f"[GPU] 进度: {progress_data.get('percent', 0):.1f}%, "
                f"速度: {progress_data.get('processing_speed', 0):.2f} fps"
            )

    gpu_processor.finished.connect(on_gpu_finished)
    gpu_processor.error.connect(on_gpu_error)
    gpu_processor.detailed_progress.connect(on_gpu_progress)

    # 启动处理
    logger.info("启动 GPU 多进程处理...")
    start_gpu = time.time()
    gpu_processor.start()

    # 等待完成
    while not gpu_completed:
        app.processEvents()
        time.sleep(0.1)

    gpu_time = time.time() - start_gpu
    print(f"\nGPU 多进程处理完成: {gpu_time:.2f} 秒")
    print()

    # ========================================
    # 性能对比
    # ========================================
    print("=" * 60)
    print("性能对比")
    print("=" * 60)
    print(f"CPU 多进程 (Phase 4): {cpu_time:.2f} 秒")
    print(f"GPU 多进程 (Phase 5): {gpu_time:.2f} 秒")

    if gpu_time < cpu_time:
        speedup = cpu_time / gpu_time
        print(f"GPU 加速倍数: {speedup:.2f}x")
        improvement = ((cpu_time - gpu_time) / cpu_time) * 100
        print(f"性能提升: {improvement:.1f}%")
    else:
        slowdown = gpu_time / cpu_time
        print(f"GPU 减速: {slowdown:.2f}x")
        print("(可能原因: 小视频、数据传输开销、GPU 模型加载等)")

    print()
    print("=" * 60)
    print("[SUCCESS] 端到端测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
