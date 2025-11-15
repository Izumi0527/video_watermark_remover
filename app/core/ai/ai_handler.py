#!/usr/bin/env python3
"""
AI处理协调器 - 主模块

统一管理水印检测和图像修复功能：
1. 设备设置和初始化
2. 模型加载协调
3. 完整的处理流程管理
4. 检测器和修复器的集成

作者: Claude Code Assistant
创建时间: 2025-01-31
版本: v1.0 (重构版)
"""

import logging
import time
from typing import Optional, Tuple

import cv2
import numpy as np
import torch

from .image_inpainter import ImageInpainter

# 导入拆分出的检测和修复模块
from .watermark_detector import WatermarkDetector


class AIHandler:
    """
    AI处理协调器

    统一管理水印检测和图像修复功能，提供完整的处理流程
    """

    def __init__(self, config=None, ai_params=None):
        self.config = config
        self.ai_params = ai_params  # 选定的模型、置信度阈值等参数

        self.device = None

        # 初始化检测器和修复器
        self.watermark_detector = WatermarkDetector(config)
        self.image_inpainter = ImageInpainter(config)

        self.logger = logging.getLogger(__name__)

        self._setup_device()
        self.logger.info("AIHandler initialized with detector and inpainter modules")

    def _setup_device(self):
        """
        设置计算设备(CPU或GPU)
        """
        # Phase 2使用基于CPU的OpenCV处理
        # GPU支持将在后续阶段添加
        self.device = "cpu"

        # 检查CUDA是否可用，供未来使用
        cuda_available = torch.cuda.is_available() if "torch" in globals() else False
        if cuda_available:
            self.logger.info("CUDA is available but using CPU for Phase 2")
        else:
            self.logger.info("CUDA not available, using CPU processing")

        self.logger.info(f"AIHandler: Device set to '{self.device}'")

    def load_models(self) -> bool:
        """
        加载Phase 2轻量级模型
        使用基于OpenCV的传统图像处理方法

        Returns:
            bool: 加载是否成功
        """
        self.logger.info("Loading lightweight AI models for Phase 2...")

        # 加载检测器和修复器的模型
        detector_loaded = self.watermark_detector.load_model()
        inpainter_loaded = self.image_inpainter.load_model()

        if detector_loaded and inpainter_loaded:
            self.logger.info("All AI models loaded successfully:")
            self.logger.info("  - Watermark Detection: OpenCV traditional methods")
            self.logger.info("  - Image Inpainting: OpenCV interpolation-based repair")
            return True
        else:
            self.logger.error("Failed to load some AI models")
            return False

    def process_frame(
        self, frame: np.ndarray, watermark_selection_params: dict
    ) -> Tuple[np.ndarray, dict]:
        """
        完整的单帧处理流程：检测和修复水印

        Args:
            frame: 输入帧，numpy数组(BGR格式)
            watermark_selection_params: 水印检测/选择参数
                - 'auto_detect': bool, 是否使用自动检测
                - 'user_mask': np.ndarray, 用户提供的掩码(可选)
                - 'detection_sensitivity': float, 检测敏感度(0.1-1.0)

        Returns:
            Tuple of (processed_frame, processing_info)
        """
        if frame is None or frame.size == 0:
            self.logger.error("Invalid input frame")
            return frame, {"error": "Invalid input frame"}

        try:
            processing_info = {
                "original_shape": frame.shape,
                "detection_method": None,
                "inpainting_method": None,
                "watermark_areas_found": 0,
                "processing_time": 0,
            }

            start_time = time.time()
            mask = None

            # 步骤1: 确定水印区域
            if watermark_selection_params.get("user_mask") is not None:
                # 处理用户提供的掩码（可能是区域列表或实际掩码）
                user_mask_data = watermark_selection_params["user_mask"]

                if isinstance(user_mask_data, list) and len(user_mask_data) > 0:
                    # (x, y, width, height)矩形列表
                    mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
                    for region in user_mask_data:
                        if len(region) == 4:
                            x, y, w, h = region
                            # 确保坐标在图像边界内
                            x = max(0, min(x, frame.shape[1] - 1))
                            y = max(0, min(y, frame.shape[0] - 1))
                            w = max(1, min(w, frame.shape[1] - x))
                            h = max(1, min(h, frame.shape[0] - y))

                            # 在掩码上绘制矩形
                            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

                    processing_info["detection_method"] = "manual_selection"
                    processing_info["manual_regions_count"] = len(user_mask_data)
                    self.logger.info(f"Using manual selection with {len(user_mask_data)} regions")

                elif isinstance(user_mask_data, np.ndarray):
                    # 直接掩码数组
                    mask = user_mask_data.copy()
                    if len(mask.shape) == 3:
                        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
                    processing_info["detection_method"] = "user_provided_mask"
                    self.logger.info("Using user-provided mask array")
                else:
                    self.logger.warning("Invalid user_mask format")
                    return frame, {"error": "Invalid user_mask format"}

            elif watermark_selection_params.get("auto_detect", False):
                # 使用水印检测器进行自动检测
                _ = watermark_selection_params.get("detection_sensitivity", 0.5)
                mask = self.watermark_detector.detect_watermark(frame)
                processing_info["detection_method"] = "automatic_opencv"
                self.logger.info("Using automatic watermark detection")

            else:
                self.logger.info("No watermark detection method specified")
                return frame, processing_info

            # 步骤2: 验证和处理掩码
            if mask is not None and np.any(mask):
                # 计算水印区域数量
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                processing_info["watermark_areas_found"] = len(contours)

                # 使用图像修复器应用修复
                processed_frame = self.image_inpainter.inpaint_frame(frame, mask)

                # 确定使用的修复方法
                total_area = sum(cv2.contourArea(c) for c in contours)
                image_area = frame.shape[0] * frame.shape[1]
                area_ratio = total_area / image_area

                if area_ratio < 0.05:
                    processing_info["inpainting_method"] = "custom_interpolation"
                elif area_ratio < 0.15:
                    processing_info["inpainting_method"] = "telea"
                else:
                    processing_info["inpainting_method"] = "navier_stokes"

                processing_info["watermark_area_ratio"] = area_ratio

                self.logger.info(
                    f"Processed frame with {len(contours)} watermark areas "
                    f"({area_ratio*100:.1f}% of image)"
                )

            else:
                # 未检测到水印或掩码为空
                processed_frame = frame.copy()
                processing_info["watermark_areas_found"] = 0
                self.logger.info("No watermark areas detected")

            processing_info["processing_time"] = time.time() - start_time
            return processed_frame, processing_info

        except Exception as e:
            self.logger.error(f"Error in frame processing: {e}")
            return frame, {"error": str(e)}

    def detect_watermark(self, frame: np.ndarray, sensitivity: float = 0.5) -> Optional[np.ndarray]:
        """
        直接调用水印检测功能

        Args:
            frame: 输入图像，numpy数组(BGR格式)
            sensitivity: 检测敏感度 (0.1-1.0)

        Returns:
            二值掩码，255=水印区域，0=干净区域
        """
        if not hasattr(self, "watermark_detector") or self.watermark_detector is None:
            self.logger.error("WatermarkDetector not initialized")
            return None

        try:
            self.logger.debug("Direct watermark detection called")
            return self.watermark_detector.detect_watermark(frame)
        except Exception as e:
            self.logger.error(f"Error in direct watermark detection: {e}")
            return None

    def inpaint_frame(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        直接调用图像修复功能

        Args:
            frame: 输入图像，numpy数组(BGR格式)
            mask: 二值掩码，255=需要修复的区域，0=保持原始

        Returns:
            修复后的图像
        """
        if not hasattr(self, "image_inpainter") or self.image_inpainter is None:
            self.logger.error("ImageInpainter not initialized")
            return frame

        try:
            self.logger.debug("Direct image inpainting called")
            return self.image_inpainter.inpaint_frame(frame, mask)
        except Exception as e:
            self.logger.error(f"Error in direct image inpainting: {e}")
            return frame


# 测试代码
if __name__ == "__main__":
    print("AIHandler module loaded for testing purposes.")

    # 创建AI处理器实例
    ai_handler = AIHandler()
    ai_handler.load_models()

    # 创建测试帧和参数
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_params = {"auto_detect": True, "detection_sensitivity": 0.5}

    # 执行完整处理流程
    processed_frame, info = ai_handler.process_frame(test_frame, test_params)
    print(f"Processing completed. Frame shape: {processed_frame.shape}")
    print(f"Processing info: {info}")
