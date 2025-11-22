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

from .dl_inpainter import DeepLearningInpainter
from .image_inpainter import ImageInpainter

# 导入拆分出的检测和修复模块
from .yolo_detector import YOLOWatermarkDetector


class AIHandler:
    """
    AI处理协调器

    统一管理水印检测和图像修复功能，提供完整的处理流程
    """

    def __init__(self, config=None, ai_params=None):
        self.config = config
        self.ai_params = ai_params or {}  # 默认空字典

        self.device = None
        self.torch_device = None

        # 从ai_params提取参数（使用默认值）
        self.use_gpu_inpainting = self.ai_params.get("use_gpu_inpainting", False)
        self.conf_threshold = self.ai_params.get("conf_threshold", 0.5)
        self.device_preference = self.ai_params.get("device", "auto")  # "cuda"/"cpu"/"auto"
        self.inpainting_algorithm = self.ai_params.get("inpainting_algorithm", "gpu_dl")
        self.inpaint_radius = self.ai_params.get("inpaint_radius", 3)

        # 预处理/后处理开关
        self.enable_blur_preprocess = self.ai_params.get("enable_blur_preprocess", False)
        self.enable_denoise_preprocess = self.ai_params.get("enable_denoise_preprocess", False)
        self.enable_sharp_preprocess = self.ai_params.get("enable_sharp_preprocess", False)
        self.enable_smooth_postprocess = self.ai_params.get("enable_smooth_postprocess", False)
        self.enable_blend_postprocess = self.ai_params.get("enable_blend_postprocess", False)
        self.enable_enhance_postprocess = self.ai_params.get("enable_enhance_postprocess", False)

        # 初始化检测器和修复器
        self.watermark_detector = None  # 延迟初始化,需要先设置 device
        self.image_inpainter = ImageInpainter(config)
        self.dl_inpainter = None  # 深度学习 inpainter (GPU 加速)

        self.logger = logging.getLogger(__name__)

        self._setup_device()

        # 初始化 YOLO 检测器(在设置 device 之后) - 使用ai_params中的参数
        # 从配置对象读取模型类型(默认: yolo11x-watermark)
        self.watermark_detector = YOLOWatermarkDetector(
            config=self.config,  # 使用配置对象驱动
            conf_threshold=self.conf_threshold,  # 使用参数而非硬编码
            iou_threshold=0.4,
            device=self.device,
        )

        inpaint_method = "GPU Deep Learning" if self.use_gpu_inpainting else "OpenCV"
        self.logger.info(f"AIHandler initialized - Inpainting method: {inpaint_method}")
        self.logger.info(
            f"AIHandler parameters: conf_threshold={self.conf_threshold}, device={self.device}"
        )

    def _setup_device(self):
        """
        设置计算设备(CPU或GPU)

        Phase 5: 支持 GPU 加速深度学习推理
        支持用户指定设备偏好：cuda/cpu/auto
        """
        # 检查 CUDA 是否可用
        cuda_available = torch.cuda.is_available()

        # 根据用户偏好和硬件情况决定设备
        if self.device_preference == "cuda":
            # 强制使用GPU
            if cuda_available:
                self.device = "cuda"
                self.torch_device = torch.device("cuda")
                gpu_name = torch.cuda.get_device_name(0)
                self.logger.info(f"GPU mode forced by user: {gpu_name}")
            else:
                self.logger.warning("GPU requested but CUDA not available, falling back to CPU")
                self.device = "cpu"
                self.torch_device = torch.device("cpu")
                self.use_gpu_inpainting = False  # 自动降级
        elif self.device_preference == "cpu":
            # 强制使用CPU
            self.device = "cpu"
            self.torch_device = torch.device("cpu")
            self.use_gpu_inpainting = False
            self.logger.info("CPU mode forced by user")
        else:
            # 自动模式：根据use_gpu_inpainting和硬件情况决定
            if self.use_gpu_inpainting and cuda_available:
                # 使用 GPU 深度学习
                self.device = "cuda"
                self.torch_device = torch.device("cuda")
                gpu_name = torch.cuda.get_device_name(0)
                self.logger.info(f"GPU acceleration enabled: {gpu_name}")
            else:
                # 使用 CPU
                self.device = "cpu"
                self.torch_device = torch.device("cpu")

                if self.use_gpu_inpainting and not cuda_available:
                    self.logger.warning("GPU inpainting requested but CUDA not available")
                    self.logger.warning("Falling back to OpenCV CPU inpainting")
                    self.use_gpu_inpainting = False  # 自动降级

        self.logger.info(
            f"AIHandler: Device set to '{self.device}' (preference: '{self.device_preference}')"
        )

    def load_models(self) -> bool:
        """
        加载 AI 模型

        Phase 5: 支持加载 GPU 加速深度学习模型

        Returns:
            bool: 加载是否成功
        """
        self.logger.info("Loading AI models...")

        # 1. 加载水印检测器
        detector_loaded = self.watermark_detector.load_model()

        # 2. 加载图像修复器
        if self.use_gpu_inpainting:
            # 加载深度学习 GPU inpainter
            try:
                self.logger.info("Loading GPU-accelerated deep learning inpainter...")
                self.dl_inpainter = DeepLearningInpainter(
                    config=self.config, device=self.torch_device
                )
                dl_loaded = self.dl_inpainter.load_model()

                if dl_loaded:
                    self.logger.info("All AI models loaded successfully:")
                    self.logger.info("  - Watermark Detection: YOLO v11s deep learning (GPU)")
                    self.logger.info("  - Image Inpainting: GPU Deep Learning (U-Net)")
                    return detector_loaded and dl_loaded
                else:
                    self.logger.error("Failed to load deep learning inpainter")
                    self.logger.warning("Falling back to OpenCV inpainter")
                    self.use_gpu_inpainting = False
                    # 继续使用 OpenCV inpainter
            except Exception as e:
                self.logger.error(f"Error loading DL inpainter: {e}")
                self.logger.warning("Falling back to OpenCV inpainter")
                self.use_gpu_inpainting = False

        # 3. 加载 OpenCV inpainter (作为默认或降级选项)
        if not self.use_gpu_inpainting:
            inpainter_loaded = self.image_inpainter.load_model()

            if detector_loaded and inpainter_loaded:
                self.logger.info("All AI models loaded successfully:")
                self.logger.info("  - Watermark Detection: YOLO v11s deep learning")
                self.logger.info("  - Image Inpainting: OpenCV interpolation-based repair")
                return True
            else:
                self.logger.error("Failed to load some AI models")
                return False

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
                processing_info["detection_method"] = "automatic_yolo"
                self.logger.info("Using automatic watermark detection (YOLO v11s)")

            else:
                self.logger.info("No watermark detection method specified")
                return frame, processing_info

            # 步骤2: 验证和处理掩码
            if mask is not None and np.any(mask):
                # 计算水印区域数量
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                processing_info["watermark_areas_found"] = len(contours)

                # 使用图像修复器应用修复 (自动选择 GPU DL 或 OpenCV)
                processed_frame = self.inpaint_frame(frame, mask)

                # 记录使用的修复方法
                if self.use_gpu_inpainting and self.dl_inpainter is not None:
                    processing_info["inpainting_method"] = "gpu_deep_learning_unet"
                else:
                    # OpenCV 方法：根据水印区域大小选择算法
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
                    f"({sum(cv2.contourArea(c) for c in contours) / (frame.shape[0] * frame.shape[1]) * 100:.1f}% of image)"
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

        Phase 5: 支持 GPU 深度学习修复或 OpenCV 修复

        Args:
            frame: 输入图像，numpy数组(BGR格式)
            mask: 二值掩码，255=需要修复的区域，0=保持原始

        Returns:
            修复后的图像
        """
        try:
            self.logger.debug("Direct image inpainting called")

            # 优先使用深度学习 inpainter (如果已启用)
            if self.use_gpu_inpainting and self.dl_inpainter is not None:
                return self.dl_inpainter.inpaint_frame(frame, mask)  # type: ignore[no-any-return]

            # 降级使用 OpenCV inpainter
            if hasattr(self, "image_inpainter") and self.image_inpainter is not None:
                return self.image_inpainter.inpaint_frame(frame, mask)

            self.logger.error("No inpainter available")
            return frame

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
