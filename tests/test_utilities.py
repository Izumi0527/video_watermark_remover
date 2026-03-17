#!/usr/bin/env python3
"""
测试工具函数模块

提供测试中使用的辅助函数：
1. 测试图像生成
2. 测试结果保存
3. 测试数据创建
4. 通用测试实用工具

从 test_phase2.py 重构拆分
作者: Izumi0527
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import time
from typing import Optional, Tuple

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


def create_test_image_with_watermark(width: int = 400, height: int = 300) -> np.ndarray:
    """
    创建带水印的测试图片

    Args:
        width: 图像宽度，默认400
        height: 图像高度，默认300

    Returns:
        带水印的测试图像数组
    """
    # 创建测试图像 (蓝色背景)
    image = np.full((height, width, 3), (200, 150, 100), dtype=np.uint8)

    # 添加一些纹理
    for i in range(0, height, 20):
        cv2.line(image, (0, i), (width, i), (210, 160, 110), 1)
    for i in range(0, width, 20):
        cv2.line(image, (i, 0), (i, height), (210, 160, 110), 1)

    # 添加模拟水印 - 半透明白色文字
    overlay = image.copy()
    cv2.putText(overlay, "WATERMARK", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    cv2.putText(overlay, "TEST", (250, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)

    # 混合原图和水印
    alpha = 0.7
    image = cv2.addWeighted(image, alpha, overlay, 1 - alpha, 0)

    return image


def create_test_mask(image_shape: Tuple[int, int]) -> np.ndarray:
    """
    创建简单的测试掩码

    Args:
        image_shape: 图像形状 (height, width)

    Returns:
        测试掩码数组
    """
    height, width = image_shape
    mask = np.zeros((height, width), dtype=np.uint8)

    # 创建矩形掩码区域（模拟检测到的水印区域）
    cv2.rectangle(mask, (40, 80), (300, 120), 255, -1)  # WATERMARK 文字区域
    cv2.rectangle(mask, (240, 180), (320, 220), 255, -1)  # TEST 文字区域

    return mask


def save_test_results(
    test_image: np.ndarray,
    processed_image: np.ndarray,
    mask: Optional[np.ndarray] = None,
    prefix: str = "test",
) -> bool:
    """
    保存测试结果图片

    Args:
        test_image: 原始测试图像
        processed_image: 处理后的图像
        mask: 掩码图像（可选）
        prefix: 文件名前缀

    Returns:
        是否保存成功
    """
    try:
        timestamp = int(time.time())

        # 保存原图
        original_filename = f"{prefix}_original_{timestamp}.jpg"
        cv2.imwrite(original_filename, test_image)
        print(f"[保存] 原图已保存: {original_filename}")

        # 保存处理后的图片
        processed_filename = f"{prefix}_processed_{timestamp}.jpg"
        cv2.imwrite(processed_filename, processed_image)
        print(f"[保存] 处理图已保存: {processed_filename}")

        # 保存掩码（如果有）
        if mask is not None:
            mask_filename = f"{prefix}_mask_{timestamp}.jpg"
            cv2.imwrite(mask_filename, mask)
            print(f"[保存] 掩码已保存: {mask_filename}")

        return True

    except Exception as e:
        print(f"[ERROR] 保存测试结果失败: {e}")
        return False


def validate_image_properties(
    image: np.ndarray, expected_shape: Optional[Tuple[int, ...]] = None
) -> bool:
    """
    验证图像属性

    Args:
        image: 要验证的图像
        expected_shape: 期望的图像形状

    Returns:
        是否符合预期
    """
    try:
        if image is None:
            print("[ERROR] 图像为空")
            return False

        if not isinstance(image, np.ndarray):
            print("[ERROR] 图像不是numpy数组")
            return False

        if len(image.shape) not in [2, 3]:
            print(f"[ERROR] 图像维度异常: {len(image.shape)}")
            return False

        if expected_shape and image.shape != expected_shape:
            print(f"[ERROR] 图像尺寸不匹配: {image.shape} != {expected_shape}")
            return False

        return True

    except Exception as e:
        print(f"[ERROR] 验证图像属性失败: {e}")
        return False


def calculate_image_difference(image1: np.ndarray, image2: np.ndarray) -> float:
    """
    计算两个图像之间的差异

    Args:
        image1: 第一个图像
        image2: 第二个图像

    Returns:
        图像差异值
    """
    try:
        if image1.shape != image2.shape:
            print(f"[WARNING] 图像尺寸不匹配: {image1.shape} vs {image2.shape}")
            return float("inf")

        diff = cv2.absdiff(image1, image2)
        total_diff = np.sum(diff)

        return float(total_diff)

    except Exception as e:
        print(f"[ERROR] 计算图像差异失败: {e}")
        return float("inf")


def print_test_header(test_name: str) -> None:
    """
    打印测试标题

    Args:
        test_name: 测试名称
    """
    print(f"\n[测试] {test_name}...")


def print_test_result(test_name: str, success: bool, details: str = "") -> None:
    """
    打印测试结果

    Args:
        test_name: 测试名称
        success: 是否成功
        details: 详细信息
    """
    status = "[OK]" if success else "[ERROR]"
    message = f"{status} {test_name}"
    if details:
        message += f" - {details}"
    print(message)
