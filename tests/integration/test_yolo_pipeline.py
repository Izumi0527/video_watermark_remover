#!/usr/bin/env python3
"""
YOLO 检测 + 修复端到端测试

测试完整的水印去除 pipeline:
- YOLO 检测
- GPU/OpenCV 修复
- 批处理性能
"""

import logging
import os
import sys
import time

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")
pytest.importorskip("torch")

import cv2
import numpy as np
import torch

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.ai import AIHandler  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_test_frame_with_watermark(width=640, height=480):
    """创建带水印的测试帧"""
    # 生成随机背景
    frame = np.random.randint(50, 200, (height, width, 3), dtype=np.uint8)

    # 添加水印区域 (白色矩形 + 文字)
    watermark_x, watermark_y = 100, 100
    watermark_w, watermark_h = 200, 80

    # 半透明白色背景
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (watermark_x, watermark_y),
        (watermark_x + watermark_w, watermark_y + watermark_h),
        (255, 255, 255),
        -1,
    )
    frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

    # 添加文字
    cv2.putText(
        frame,
        "WATERMARK",
        (watermark_x + 20, watermark_y + 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 0),
        2,
    )

    return frame


def main():
    print("=" * 60)
    print("YOLO 检测 + 修复端到端测试")
    print("=" * 60)

    # 检查 CUDA
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    if cuda_available:
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
    print()

    # ========================================
    # 测试 1: AIHandler 初始化和模型加载
    # ========================================
    print("=" * 60)
    print("测试 1: AIHandler 初始化")
    print("=" * 60)

    # 测试 GPU inpainting
    logger.info("创建 AIHandler (GPU inpainting)...")
    ai_handler_gpu = AIHandler(ai_params={"use_gpu_inpainting": True})

    if ai_handler_gpu.load_models():
        print("✅ AIHandler (GPU) 模型加载成功")
    else:
        print("❌ AIHandler (GPU) 模型加载失败")
        return

    # 测试 OpenCV inpainting
    logger.info("创建 AIHandler (OpenCV inpainting)...")
    ai_handler_cpu = AIHandler(ai_params={"use_gpu_inpainting": False})

    if ai_handler_cpu.load_models():
        print("✅ AIHandler (OpenCV) 模型加载成功")
    else:
        print("❌ AIHandler (OpenCV) 模型加载失败")
        return

    print()

    # ========================================
    # 测试 2: 单帧端到端处理
    # ========================================
    print("=" * 60)
    print("测试 2: 单帧端到端处理")
    print("=" * 60)

    # 创建测试帧
    test_frame = create_test_frame_with_watermark()

    # GPU pipeline
    logger.info("GPU pipeline 预热...")
    for _ in range(3):
        _, _ = ai_handler_gpu.process_frame(test_frame, {"auto_detect": True})

    logger.info("GPU pipeline 测试...")
    gpu_times = []
    for _ in range(5):
        start = time.time()
        processed_frame, info = ai_handler_gpu.process_frame(test_frame, {"auto_detect": True})
        elapsed = (time.time() - start) * 1000
        gpu_times.append(elapsed)

    avg_gpu = np.mean(gpu_times)
    std_gpu = np.std(gpu_times)
    print(f"GPU pipeline: {avg_gpu:.2f} ± {std_gpu:.2f} ms")
    print(f"  - Detection method: {info.get('detection_method', 'N/A')}")
    print(f"  - Inpainting method: {info.get('inpainting_method', 'N/A')}")
    print(f"  - Watermark areas found: {info.get('watermark_areas_found', 0)}")

    # OpenCV pipeline
    logger.info("OpenCV pipeline 预热...")
    for _ in range(3):
        _, _ = ai_handler_cpu.process_frame(test_frame, {"auto_detect": True})

    logger.info("OpenCV pipeline 测试...")
    cpu_times = []
    for _ in range(5):
        start = time.time()
        processed_frame, info = ai_handler_cpu.process_frame(test_frame, {"auto_detect": True})
        elapsed = (time.time() - start) * 1000
        cpu_times.append(elapsed)

    avg_cpu = np.mean(cpu_times)
    std_cpu = np.std(cpu_times)
    print(f"OpenCV pipeline: {avg_cpu:.2f} ± {std_cpu:.2f} ms")
    print(f"  - Detection method: {info.get('detection_method', 'N/A')}")
    print(f"  - Inpainting method: {info.get('inpainting_method', 'N/A')}")

    # 对比
    speedup = avg_cpu / avg_gpu if avg_gpu > 0 else 0
    print(f"\nGPU speedup: {speedup:.2f}x")

    print()

    # ========================================
    # 测试 3: 批处理性能
    # ========================================
    print("=" * 60)
    print("测试 3: 批处理检测性能")
    print("=" * 60)

    batch_sizes = [1, 2, 4, 8]

    for batch_size in batch_sizes:
        batch_frames = [test_frame] * batch_size

        # GPU 批处理
        batch_times = []
        for _ in range(3):
            start = time.time()
            # 直接调用 YOLO 批处理
            masks = ai_handler_gpu.watermark_detector.detect_batch(batch_frames)
            elapsed = (time.time() - start) * 1000
            batch_times.append(elapsed)

        avg_time = np.mean(batch_times)
        per_frame_time = avg_time / batch_size
        fps = 1000 / per_frame_time

        print(
            f"Batch={batch_size}: {avg_time:.2f} ms 总计, "
            f"{per_frame_time:.2f} ms/帧, {fps:.2f} fps"
        )

    print()

    # ========================================
    # 测试 4: GPU 内存占用
    # ========================================
    if cuda_available:
        print("=" * 60)
        print("测试 4: GPU 内存占用")
        print("=" * 60)

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        # 单帧处理
        _, _ = ai_handler_gpu.process_frame(test_frame, {"auto_detect": True})
        mem_single = torch.cuda.max_memory_allocated() / 1e6

        # 批处理
        torch.cuda.reset_peak_memory_stats()
        batch_frames = [test_frame] * 8
        _ = ai_handler_gpu.watermark_detector.detect_batch(batch_frames)
        mem_batch = torch.cuda.max_memory_allocated() / 1e6

        print(f"单帧处理峰值内存: {mem_single:.2f} MB")
        print(f"批处理 (batch=8) 峰值内存: {mem_batch:.2f} MB")
        print()

    # ========================================
    # 清理
    # ========================================
    logger.info("清理 GPU 内存...")
    ai_handler_gpu.watermark_detector.cleanup()
    if ai_handler_gpu.deep_inpainting_backend is not None:
        ai_handler_gpu.deep_inpainting_backend.cleanup()

    print("=" * 60)
    print("[SUCCESS] 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
