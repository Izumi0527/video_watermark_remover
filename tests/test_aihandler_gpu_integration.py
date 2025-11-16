"""
AIHandler GPU 集成测试

测试 AIHandler 与深度学习 GPU inpainter 的集成
"""

import logging
import os
import sys
import time

import cv2
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.ai.ai_handler import AIHandler  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    print("=" * 60)
    print("AIHandler GPU 集成测试")
    print("=" * 60)
    print()

    # ========================================
    # 测试 1: OpenCV 模式 (Baseline)
    # ========================================
    print("=" * 60)
    print("测试 1: OpenCV 模式 (Baseline)")
    print("=" * 60)

    logger.info("创建 OpenCV AIHandler...")
    opencv_handler = AIHandler(ai_params={"use_gpu_inpainting": False})

    if not opencv_handler.load_models():
        logger.error("OpenCV 模型加载失败")
        return

    # 创建测试数据
    logger.info("创建测试数据...")
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    test_mask = np.zeros((480, 640), dtype=np.uint8)
    cv2.rectangle(test_mask, (100, 100), (200, 200), 255, -1)

    # OpenCV 推理
    logger.info("OpenCV 推理 (预热)...")
    for _ in range(5):
        _ = opencv_handler.inpaint_frame(test_frame, test_mask)

    logger.info("OpenCV 推理 (测试)...")
    opencv_times = []
    for _ in range(20):
        start = time.time()
        _ = opencv_handler.inpaint_frame(test_frame, test_mask)
        elapsed = (time.time() - start) * 1000
        opencv_times.append(elapsed)

    opencv_avg = np.mean(opencv_times)
    opencv_std = np.std(opencv_times)
    print(f"OpenCV 推理: {opencv_avg:.2f} +/- {opencv_std:.2f} ms")
    print()

    # ========================================
    # 测试 2: GPU 深度学习模式
    # ========================================
    print("=" * 60)
    print("测试 2: GPU 深度学习模式")
    print("=" * 60)

    logger.info("创建 GPU AIHandler...")
    gpu_handler = AIHandler(ai_params={"use_gpu_inpainting": True})

    if not gpu_handler.load_models():
        logger.error("GPU 模型加载失败")
        return

    # GPU 推理
    logger.info("GPU 推理 (预热)...")
    for _ in range(5):
        _ = gpu_handler.inpaint_frame(test_frame, test_mask)

    logger.info("GPU 推理 (测试)...")
    gpu_times = []
    for _ in range(20):
        start = time.time()
        _ = gpu_handler.inpaint_frame(test_frame, test_mask)
        elapsed = (time.time() - start) * 1000
        gpu_times.append(elapsed)

    gpu_avg = np.mean(gpu_times)
    gpu_std = np.std(gpu_times)
    print(f"GPU 深度学习推理: {gpu_avg:.2f} +/- {gpu_std:.2f} ms")
    print()

    # ========================================
    # 性能对比
    # ========================================
    print("=" * 60)
    print("性能对比")
    print("=" * 60)
    print(f"OpenCV 推理: {opencv_avg:.2f} +/- {opencv_std:.2f} ms")
    print(f"GPU DL 推理: {gpu_avg:.2f} +/- {gpu_std:.2f} ms")

    if gpu_avg < opencv_avg:
        speedup = opencv_avg / gpu_avg
        print(f"GPU 加速倍数: {speedup:.2f}x")
    else:
        slowdown = gpu_avg / opencv_avg
        print(f"GPU 减速: {slowdown:.2f}x (可能模型质量更高)")

    print()

    # ========================================
    # 完整处理流程测试
    # ========================================
    print("=" * 60)
    print("测试 3: 完整处理流程 (process_frame)")
    print("=" * 60)

    watermark_params = {
        "user_mask": [(100, 100, 100, 100)],  # 手动指定水印区域
    }

    # OpenCV 完整流程
    logger.info("OpenCV 完整处理流程...")
    start = time.time()
    opencv_result, opencv_info = opencv_handler.process_frame(test_frame, watermark_params)
    opencv_full_time = (time.time() - start) * 1000
    print(f"OpenCV 完整处理: {opencv_full_time:.2f} ms")
    print(f"  - 修复方法: {opencv_info.get('inpainting_method', 'N/A')}")

    # GPU 完整流程
    logger.info("GPU 完整处理流程...")
    start = time.time()
    gpu_result, gpu_info = gpu_handler.process_frame(test_frame, watermark_params)
    gpu_full_time = (time.time() - start) * 1000
    print(f"GPU 完整处理: {gpu_full_time:.2f} ms")
    print(f"  - 修复方法: {gpu_info.get('inpainting_method', 'N/A')}")

    print()

    # ========================================
    # 清理
    # ========================================
    if hasattr(gpu_handler, "dl_inpainter") and gpu_handler.dl_inpainter is not None:
        logger.info("清理 GPU 内存...")
        gpu_handler.dl_inpainter.cleanup()

    print("=" * 60)
    print("[SUCCESS] 集成测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
