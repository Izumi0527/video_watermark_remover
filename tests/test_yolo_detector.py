#!/usr/bin/env python3
"""
YOLO 水印检测器单元测试

测试 YOLOWatermarkDetector 的各项功能
"""

import logging
import os
import sys
import time

import cv2
import numpy as np
import torch

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    print("=" * 60)
    print("YOLO 水印检测器单元测试")
    print("=" * 60)

    # 检查 CUDA
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    if cuda_available:
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
    print()

    # ========================================
    # 测试 1: 模型加载
    # ========================================
    print("=" * 60)
    print("测试 1: 模型加载")
    print("=" * 60)

    logger.info("创建 YOLO 检测器...")
    detector = YOLOWatermarkDetector(
        model_path="models/yolo11s.pt",
        conf_threshold=0.5,
        iou_threshold=0.4,
    )

    if detector.load_model():
        print("✅ YOLO 模型加载成功")
    else:
        print("❌ YOLO 模型加载失败")
        return

    print()

    # ========================================
    # 测试 2: 单帧推理性能
    # ========================================
    print("=" * 60)
    print("测试 2: 单帧推理性能")
    print("=" * 60)

    # 创建测试图像
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    # 添加一个简单的"水印"（白色矩形）
    cv2.rectangle(test_frame, (100, 100), (200, 150), (255, 255, 255), -1)
    cv2.putText(test_frame, "WATERMARK", (110, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    logger.info("单帧推理 (预热)...")
    for _ in range(3):
        _ = detector.detect_watermark(test_frame)

    logger.info("单帧推理 (测试)...")
    times = []
    for _ in range(10):
        start = time.time()
        mask = detector.detect_watermark(test_frame)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)

    avg_time = np.mean(times)
    std_time = np.std(times)
    print(f"单帧推理: {avg_time:.2f} ± {std_time:.2f} ms")
    print(f"Mask shape: {mask.shape}")
    print(f"Detected pixels: {np.sum(mask > 0)}")

    print()

    # ========================================
    # 测试 3: 批处理性能
    # ========================================
    print("=" * 60)
    print("测试 3: 批处理性能")
    print("=" * 60)

    batch_sizes = [1, 2, 4, 8]

    for batch_size in batch_sizes:
        batch_frames = [test_frame] * batch_size

        # 预热
        for _ in range(2):
            _ = detector.detect_batch(batch_frames)

        # 测试
        batch_times = []
        for _ in range(5):
            start = time.time()
            masks = detector.detect_batch(batch_frames)
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

        # 单帧推理
        _ = detector.detect_watermark(test_frame)
        mem_single = torch.cuda.max_memory_allocated() / 1e6

        # 批处理
        torch.cuda.reset_peak_memory_stats()
        batch_frames = [test_frame] * 8
        _ = detector.detect_batch(batch_frames)
        mem_batch8 = torch.cuda.max_memory_allocated() / 1e6

        print(f"单帧推理峰值内存: {mem_single:.2f} MB")
        print(f"批处理 (batch=8) 峰值内存: {mem_batch8:.2f} MB")
        print()

    # ========================================
    # 清理
    # ========================================
    logger.info("清理 GPU 内存...")
    detector.cleanup()

    print("=" * 60)
    print("[SUCCESS] 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
