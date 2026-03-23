#!/usr/bin/env python3
"""
图像预处理与后处理模块

提供水印去除流程中的图像增强功能：
1. 预处理：在检测前对图像进行优化
2. 后处理：在修复后对结果进行增强

所有函数设计为纯函数，便于测试和复用。
"""

import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# 预处理函数 (Preprocessing)
# ============================================================================


def preprocess_blur(
    frame: np.ndarray,
    kernel_size: int = 5,
    sigma: float = 0,
) -> np.ndarray:
    """
    高斯模糊预处理

    用于减少图像噪声，可能提高检测精度（特别是对于有噪点的视频）

    Args:
        frame: 输入帧 (BGR格式)
        kernel_size: 高斯核大小（必须为奇数）
        sigma: 高斯标准差，0表示自动计算

    Returns:
        模糊后的图像
    """
    # 确保核大小为奇数
    if kernel_size % 2 == 0:
        kernel_size += 1

    return cv2.GaussianBlur(frame, (kernel_size, kernel_size), sigma)


def preprocess_denoise(
    frame: np.ndarray,
    h: float = 10,
    h_color: float = 10,
    template_window_size: int = 7,
    search_window_size: int = 21,
) -> np.ndarray:
    """
    非局部均值降噪预处理

    使用 OpenCV 的 fastNlMeansDenoisingColored 算法去除噪声

    Args:
        frame: 输入帧 (BGR格式)
        h: 亮度分量滤波强度
        h_color: 颜色分量滤波强度
        template_window_size: 模板窗口大小（奇数）
        search_window_size: 搜索窗口大小（奇数）

    Returns:
        降噪后的图像
    """
    return cv2.fastNlMeansDenoisingColored(
        frame,
        None,
        h,
        h_color,
        template_window_size,
        search_window_size,
    )


def preprocess_sharpen(
    frame: np.ndarray,
    strength: float = 1.0,
) -> np.ndarray:
    """
    锐化预处理

    增强图像边缘，可能提高水印边界检测

    Args:
        frame: 输入帧 (BGR格式)
        strength: 锐化强度 (0.5-2.0)

    Returns:
        锐化后的图像
    """
    # 标准锐化核
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)

    # 调整锐化强度
    if strength != 1.0:
        # 将锐化效果与原图混合
        identity = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype=np.float32)
        kernel = identity + strength * (kernel - identity)

    sharpened = cv2.filter2D(frame, -1, kernel)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def apply_preprocessing(
    frame: np.ndarray,
    enable_blur: bool = False,
    enable_denoise: bool = False,
    enable_sharpen: bool = False,
    blur_kernel_size: int = 5,
    denoise_strength: float = 10,
    sharpen_strength: float = 1.0,
) -> np.ndarray:
    """
    应用预处理管道

    按顺序应用启用的预处理步骤：降噪 → 模糊 → 锐化

    Args:
        frame: 输入帧
        enable_blur: 是否启用模糊
        enable_denoise: 是否启用降噪
        enable_sharpen: 是否启用锐化
        blur_kernel_size: 模糊核大小
        denoise_strength: 降噪强度
        sharpen_strength: 锐化强度

    Returns:
        预处理后的图像
    """
    result = frame.copy()

    # 降噪（先做，可以减少后续处理的噪声传播）
    if enable_denoise:
        logger.debug("Applying denoise preprocessing")
        result = preprocess_denoise(result, h=denoise_strength)

    # 模糊
    if enable_blur:
        logger.debug("Applying blur preprocessing")
        result = preprocess_blur(result, kernel_size=blur_kernel_size)

    # 锐化（最后做，可以增强边缘）
    if enable_sharpen:
        logger.debug("Applying sharpen preprocessing")
        result = preprocess_sharpen(result, strength=sharpen_strength)

    return result


# ============================================================================
# 后处理函数 (Postprocessing)
# ============================================================================


def postprocess_smooth_edges(
    original: np.ndarray,
    processed: np.ndarray,
    mask: np.ndarray,
    blur_radius: int = 5,
    feather_amount: int = 3,
) -> np.ndarray:
    """
    修复区域边缘平滑处理

    在修复区域边缘创建平滑过渡，避免明显的修复痕迹

    Args:
        original: 原始图像 (BGR格式)
        processed: 修复后的图像 (BGR格式)
        mask: 修复区域掩码 (255=修复区域)
        blur_radius: 边缘模糊半径
        feather_amount: 羽化扩展量

    Returns:
        边缘平滑后的图像
    """
    if mask is None or not np.any(mask):
        return processed

    # 创建羽化掩码
    kernel = np.ones((feather_amount * 2 + 1, feather_amount * 2 + 1), np.uint8)
    dilated_mask = cv2.dilate(mask, kernel, iterations=1)
    # 对边缘区域应用高斯模糊
    blur_size = blur_radius * 2 + 1
    blurred_mask = cv2.GaussianBlur(dilated_mask.astype(np.float32), (blur_size, blur_size), 0)
    blurred_mask = blurred_mask / 255.0

    # 混合原图和修复图
    result = np.zeros_like(processed, dtype=np.float32)
    for c in range(3):
        result[:, :, c] = original[:, :, c] * (1 - blurred_mask) + processed[:, :, c] * blurred_mask

    return np.clip(result, 0, 255).astype(np.uint8)


def postprocess_blend(
    original: np.ndarray,
    processed: np.ndarray,
    mask: np.ndarray,
    blend_ratio: float = 0.8,
) -> np.ndarray:
    """
    修复结果与原图混合

    在修复区域内将修复结果与原图按比例混合，
    可以保留部分原始纹理，使结果更自然

    Args:
        original: 原始图像 (BGR格式)
        processed: 修复后的图像 (BGR格式)
        mask: 修复区域掩码 (255=修复区域)
        blend_ratio: 修复结果的混合比例 (0-1)

    Returns:
        混合后的图像
    """
    if mask is None or not np.any(mask):
        return processed

    result = processed.copy()

    # 仅在掩码区域内混合
    mask_bool = mask > 127
    mask_3c = np.stack([mask_bool] * 3, axis=-1)

    blended_region = (
        original.astype(np.float32) * (1 - blend_ratio) + processed.astype(np.float32) * blend_ratio
    )

    result[mask_3c] = blended_region[mask_3c]
    return np.clip(result, 0, 255).astype(np.uint8)


def postprocess_enhance(
    frame: np.ndarray,
    mask: Optional[np.ndarray] = None,
    contrast: float = 1.1,
    brightness: int = 5,
    saturation: float = 1.1,
) -> np.ndarray:
    """
    修复区域增强处理

    对修复区域进行对比度、亮度、饱和度调整，
    使修复区域与周围区域更好地融合

    Args:
        frame: 输入图像 (BGR格式)
        mask: 修复区域掩码 (可选，None表示全图处理)
        contrast: 对比度调整因子 (1.0=不变)
        brightness: 亮度调整值 (-100到100)
        saturation: 饱和度调整因子 (1.0=不变)

    Returns:
        增强后的图像
    """
    # 对比度和亮度调整
    enhanced = cv2.convertScaleAbs(frame, alpha=contrast, beta=brightness)

    # 饱和度调整
    if saturation != 1.0:
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
        enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 如果提供了掩码，仅增强掩码区域
    if mask is not None and np.any(mask):
        result = frame.copy()
        mask_bool = mask > 127
        mask_3c = np.stack([mask_bool] * 3, axis=-1)
        result[mask_3c] = enhanced[mask_3c]
        return result

    return enhanced


def apply_postprocessing(
    original: np.ndarray,
    processed: np.ndarray,
    mask: np.ndarray,
    enable_smooth: bool = False,
    enable_blend: bool = False,
    enable_enhance: bool = False,
    smooth_blur_radius: int = 5,
    smooth_feather_amount: int = 3,
    blend_ratio: float = 0.8,
    enhance_contrast: float = 1.1,
    enhance_brightness: int = 5,
    enhance_saturation: float = 1.1,
) -> np.ndarray:
    """
    应用后处理管道

    按顺序应用启用的后处理步骤：边缘平滑 → 混合 → 增强

    Args:
        original: 原始图像
        processed: 修复后的图像
        mask: 修复区域掩码
        enable_smooth: 是否启用边缘平滑
        enable_blend: 是否启用混合
        enable_enhance: 是否启用增强
        smooth_blur_radius: 边缘平滑模糊半径
        smooth_feather_amount: 边缘平滑羽化量
        blend_ratio: 混合比例
        enhance_contrast: 增强对比度
        enhance_brightness: 增强亮度
        enhance_saturation: 增强饱和度

    Returns:
        后处理后的图像
    """
    result = processed.copy()

    # 边缘平滑
    if enable_smooth:
        logger.debug("Applying edge smoothing postprocessing")
        result = postprocess_smooth_edges(
            original,
            result,
            mask,
            blur_radius=smooth_blur_radius,
            feather_amount=smooth_feather_amount,
        )

    # 混合
    if enable_blend:
        logger.debug("Applying blend postprocessing")
        result = postprocess_blend(original, result, mask, blend_ratio=blend_ratio)

    # 增强
    if enable_enhance:
        logger.debug("Applying enhancement postprocessing")
        result = postprocess_enhance(
            result,
            mask,
            contrast=enhance_contrast,
            brightness=enhance_brightness,
            saturation=enhance_saturation,
        )

    return result


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("Image Processor module loaded for testing.")

    # 创建测试图像
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    test_mask = np.zeros((480, 640), dtype=np.uint8)
    cv2.rectangle(test_mask, (100, 100), (200, 200), 255, -1)

    # 测试预处理
    preprocessed = apply_preprocessing(
        test_frame,
        enable_blur=True,
        enable_denoise=True,
        enable_sharpen=True,
    )
    print(f"Preprocessed frame shape: {preprocessed.shape}")

    # 测试后处理
    postprocessed = apply_postprocessing(
        test_frame,
        preprocessed,
        test_mask,
        enable_smooth=True,
        enable_blend=True,
        enable_enhance=True,
    )
    print(f"Postprocessed frame shape: {postprocessed.shape}")
