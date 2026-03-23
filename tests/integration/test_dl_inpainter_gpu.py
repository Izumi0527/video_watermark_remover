"""
深度学习 Inpainter GPU 性能测试

测试轻量级 U-Net 模型的 GPU 加速效果
"""

import logging
import os
import subprocess
import sys
import time

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")


def _probe_torch_import() -> tuple[bool, str]:
    """在子进程中探测 torch 是否可导入，避免当前 pytest 进程被 DLL 错误拖崩。"""
    command = [sys.executable, "-c", "import torch"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return True, ""
    return False, (result.stderr or result.stdout or "torch import failed").strip()


import cv2
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_torch_runtime_probe():
    """探测当前环境是否具备运行 GPU 集成脚本所需的 torch 运行时。"""
    torch_available, torch_probe_error = _probe_torch_import()
    if not torch_available:
        pytest.skip(f"torch 不可用，跳过 GPU 集成测试：{torch_probe_error}")
    assert torch_available


def main():
    torch_available, torch_probe_error = _probe_torch_import()
    if not torch_available:
        raise RuntimeError(f"torch 不可用，无法执行 GPU 集成脚本：{torch_probe_error}")

    import torch

    from app.core.ai.dl_inpainter import DeepLearningInpainter

    print("=" * 60)
    print("深度学习 Inpainter GPU 性能测试")
    print("=" * 60)

    # 检查 CUDA
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    if cuda_available:
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
        print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    print()

    # 创建 inpainter (GPU)
    logger.info("创建 GPU inpainter...")
    gpu_inpainter = DeepLearningInpainter(device=torch.device("cuda" if cuda_available else "cpu"))

    if not gpu_inpainter.load_model():
        logger.error("GPU 模型加载失败")
        return

    # 创建测试数据
    logger.info("创建测试数据...")
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    test_mask = np.zeros((480, 640), dtype=np.uint8)
    cv2.rectangle(test_mask, (100, 100), (200, 200), 255, -1)
    print()

    # ========================================
    # 测试 1: 单帧推理 (GPU vs CPU)
    # ========================================
    print("=" * 60)
    print("测试 1: 单帧推理性能")
    print("=" * 60)

    # GPU 推理
    if cuda_available:
        logger.info("GPU 单帧推理 (预热)...")
        for _ in range(5):
            _ = gpu_inpainter.inpaint_frame(test_frame, test_mask)

        logger.info("GPU 单帧推理 (测试)...")
        gpu_times = []
        for _ in range(20):
            start = time.time()
            _ = gpu_inpainter.inpaint_frame(test_frame, test_mask)
            elapsed = (time.time() - start) * 1000
            gpu_times.append(elapsed)

        gpu_avg = np.mean(gpu_times)
        gpu_std = np.std(gpu_times)
        print(f"GPU 单帧推理: {gpu_avg:.2f} ± {gpu_std:.2f} ms")

    # CPU 推理 (对比)
    logger.info("创建 CPU inpainter...")
    cpu_inpainter = DeepLearningInpainter(device=torch.device("cpu"))
    if cpu_inpainter.load_model():
        logger.info("CPU 单帧推理 (预热)...")
        for _ in range(5):
            _ = cpu_inpainter.inpaint_frame(test_frame, test_mask)

        logger.info("CPU 单帧推理 (测试)...")
        cpu_times = []
        for _ in range(20):
            start = time.time()
            _ = cpu_inpainter.inpaint_frame(test_frame, test_mask)
            elapsed = (time.time() - start) * 1000
            cpu_times.append(elapsed)

        cpu_avg = np.mean(cpu_times)
        cpu_std = np.std(cpu_times)
        print(f"CPU 单帧推理: {cpu_avg:.2f} ± {cpu_std:.2f} ms")

        if cuda_available:
            speedup = cpu_avg / gpu_avg
            print(f"GPU 加速倍数: {speedup:.2f}x")

    print()

    # ========================================
    # 测试 2: 批处理推理 (GPU 优势)
    # ========================================
    print("=" * 60)
    print("测试 2: 批处理推理性能")
    print("=" * 60)

    if cuda_available:
        batch_sizes = [1, 2, 4, 8]

        for batch_size in batch_sizes:
            batch_frames = [test_frame] * batch_size
            batch_masks = [test_mask] * batch_size

            # 预热
            for _ in range(3):
                _ = gpu_inpainter.inpaint_batch(batch_frames, batch_masks)

            # 测试
            batch_times = []
            for _ in range(10):
                start = time.time()
                _ = gpu_inpainter.inpaint_batch(batch_frames, batch_masks)
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
    # 测试 3: GPU 内存占用
    # ========================================
    if cuda_available:
        print("=" * 60)
        print("测试 3: GPU 内存占用")
        print("=" * 60)

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        # 单帧推理
        _ = gpu_inpainter.inpaint_frame(test_frame, test_mask)
        mem_single = torch.cuda.max_memory_allocated() / 1e6

        # 批处理 (batch=8)
        torch.cuda.reset_peak_memory_stats()
        batch_frames = [test_frame] * 8
        batch_masks = [test_mask] * 8
        _ = gpu_inpainter.inpaint_batch(batch_frames, batch_masks)
        mem_batch8 = torch.cuda.max_memory_allocated() / 1e6

        print(f"单帧推理峰值内存: {mem_single:.2f} MB")
        print(f"批处理 (batch=8) 峰值内存: {mem_batch8:.2f} MB")
        print()

    # ========================================
    # 清理
    # ========================================
    logger.info("清理 GPU 内存...")
    gpu_inpainter.cleanup()

    print("=" * 60)
    print("[SUCCESS] 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
