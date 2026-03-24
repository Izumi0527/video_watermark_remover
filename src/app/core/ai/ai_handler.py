#!/usr/bin/env python3
"""
AI处理协调器 - 主模块

统一管理水印检测和图像修复功能：
1. 设备设置和初始化
2. 模型加载协调
3. 完整的处理流程管理
4. 检测器和修复器的集成
5. 预处理和后处理管道

"""

import logging
import time
from pathlib import Path
from typing import Optional, Tuple, cast

import cv2
import numpy as np
import torch

from .dl_inpainter import DeepLearningInpainter
from .image_inpainter import ImageInpainter
from .image_processor import apply_postprocessing, apply_preprocessing

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

        self.device: str = "cpu"  # 设备类型：'cuda'或'cpu'，初始化为cpu
        self.torch_device = None

        # 从ai_params提取参数（使用默认值）
        self.requested_gpu_inpainting = self.ai_params.get("use_gpu_inpainting", False)
        self.use_gpu_inpainting = self.requested_gpu_inpainting
        self.conf_threshold = self.ai_params.get("conf_threshold", 0.5)
        self.device_preference = self.ai_params.get("device", "auto")  # "cuda"/"cpu"/"auto"
        raw_min_area_pixels = self.ai_params.get("min_area_pixels")
        self.min_area_pixels = int(raw_min_area_pixels) if raw_min_area_pixels is not None else None
        self.inpainting_algorithm = self.ai_params.get("inpainting_algorithm", "gpu_dl")
        self.inpaint_radius = self.ai_params.get("inpaint_radius", 3)
        raw_quality_level = self.ai_params.get("quality_level", 3)
        self.quality_level = int(raw_quality_level) if raw_quality_level is not None else 3

        # 预处理/后处理开关
        self.enable_blur_preprocess = self.ai_params.get("enable_blur_preprocess", False)
        self.enable_denoise_preprocess = self.ai_params.get("enable_denoise_preprocess", False)
        self.enable_sharp_preprocess = self.ai_params.get("enable_sharp_preprocess", False)
        self.enable_smooth_postprocess = self.ai_params.get("enable_smooth_postprocess", False)
        self.enable_blend_postprocess = self.ai_params.get("enable_blend_postprocess", False)
        self.enable_enhance_postprocess = self.ai_params.get("enable_enhance_postprocess", False)

        # 初始化检测器和修复器
        self.watermark_detector: Optional[YOLOWatermarkDetector] = None  # 延迟初始化,需要先设置 device
        self.image_inpainter = ImageInpainter(config)
        self.dl_inpainter = None  # 深度学习 inpainter (GPU 加速)
        self.last_inpainting_method_used: Optional[str] = None
        self.last_inpainting_backend: Optional[str] = None
        self.last_gpu_inpainting_profile_used: Optional[dict] = None
        self.last_gpu_inpainting_retry_info: Optional[dict] = None
        self.last_gpu_inpainting_oom_retry_used: bool = False
        self.last_gpu_inpainting_retry_count: int = 0
        self.last_gpu_inpainting_retry_profile_used: Optional[dict] = None
        self.last_effective_quality_level: Optional[int] = None
        self.last_effective_inpaint_radius: Optional[int] = None
        self.last_gpu_inpainting_runtime_error: Optional[str] = None
        self.gpu_inpainting_fallback_reason: Optional[str] = None
        self.configured_inpainting_model_path = self._resolve_inpainting_model_path()
        self.loaded_inpainting_model_path: Optional[str] = None

        self.logger = logging.getLogger(__name__)

        self._setup_device()

        # 初始化 YOLO 检测器(在设置 device 之后) - 使用ai_params中的参数
        # 从配置对象读取模型类型(默认: yolo11x-watermark-corzent)
        self.watermark_detector = YOLOWatermarkDetector(
            config=self.config,  # 使用配置对象驱动
            conf_threshold=self.conf_threshold,  # 使用参数而非硬编码
            iou_threshold=0.4,
            device=self.device,
            min_area_pixels=self.min_area_pixels,
        )

        inpaint_method = "GPU Deep Learning" if self.use_gpu_inpainting else "OpenCV"
        self.logger.info(f"AIHandler initialized - Inpainting method: {inpaint_method}")
        self.logger.info(
            "AIHandler parameters: "
            f"conf_threshold={self.conf_threshold}, "
            f"device={self.device}, "
            f"min_area_pixels={self.min_area_pixels}, "
            f"inpainting_algorithm={self.inpainting_algorithm}, "
            f"inpaint_radius={self.inpaint_radius}, "
            f"quality_level={self.quality_level}, "
            f"configured_inpainting_model_path={self.configured_inpainting_model_path}"
        )

    def _setup_device(self):
        """
        设置计算设备(CPU或GPU)

        支持 GPU 加速深度学习推理
        支持用户指定设备偏好：cuda/cpu/auto
        """
        self.use_gpu_inpainting = self.requested_gpu_inpainting
        if self.gpu_inpainting_fallback_reason == "cuda_unavailable":
            self.gpu_inpainting_fallback_reason = None

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
                self._disable_gpu_inpainting("cuda_unavailable")
        elif self.device_preference == "cpu":
            # 强制使用CPU
            self.device = "cpu"
            self.torch_device = torch.device("cpu")
            self.use_gpu_inpainting = False
            self.logger.info("CPU mode forced by user")
        else:
            # 自动模式：优先使用GPU（如果可用）
            if cuda_available:
                # 检测到GPU，使用GPU加速
                self.device = "cuda"
                self.torch_device = torch.device("cuda")
                gpu_name = torch.cuda.get_device_name(0)
                self.logger.info(f"GPU acceleration enabled (auto mode): {gpu_name}")
            else:
                # 没有GPU，使用CPU
                self.device = "cpu"
                self.torch_device = torch.device("cpu")
                self.logger.info("CPU mode (auto mode, no GPU available)")

                # GPU不可用时，自动禁用GPU修复
                if self.use_gpu_inpainting:
                    self.logger.warning("GPU inpainting requested but CUDA not available")
                    self.logger.warning("Falling back to OpenCV CPU inpainting")
                    self._disable_gpu_inpainting("cuda_unavailable")

        self.logger.info(
            f"AIHandler: Device set to '{self.device}' (preference: '{self.device_preference}')"
        )

    def update_device(self, new_device: str) -> None:
        """
        动态更新设备设置（支持运行时切换GPU/CPU）

        Args:
            new_device: 新的设备偏好 ("cuda", "cpu", "auto")
        """
        if new_device == self.device_preference:
            self.logger.debug(f"Device preference unchanged: {new_device}")
            return

        old_device = self.device
        self.device_preference = new_device
        self._setup_device()

        # 同步更新检测器的设备
        if self.watermark_detector is not None:
            self.watermark_detector.device = self.device
            # 如果模型已加载，需要将模型移动到新设备
            if self.watermark_detector.model is not None:
                try:
                    self.watermark_detector.model.to(self.device)
                    self.logger.info(
                        f"✅ Device updated: {old_device} → {self.device} (YOLO model moved)"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to move YOLO model to {self.device}: {e}")
            else:
                self.logger.info(f"✅ Device updated: {old_device} → {self.device}")

        # 如果切换到GPU且启用GPU修复，需要重新加载深度学习修复器
        if self.device == "cuda" and self.requested_gpu_inpainting:
            if self.dl_inpainter is None:
                try:
                    self.logger.info("Loading GPU deep learning inpainter after device switch...")
                    self._load_gpu_inpainter_or_fallback()
                except Exception as e:
                    self.logger.error(f"Failed to load DL inpainter: {e}")
                    self._disable_gpu_inpainting("gpu_inpainter_reload_failed")

    def load_models(self) -> bool:
        """
        加载 AI 模型

        支持加载 GPU 加速深度学习模型

        Returns:
            bool: 加载是否成功
        """
        self.logger.info("Loading AI models...")

        # 1. 加载水印检测器
        if self.watermark_detector is None:
            self.logger.error("Watermark detector not initialized")
            return False

        detector_loaded = self.watermark_detector.load_model()

        # 2. 加载图像修复器
        if self.use_gpu_inpainting:
            # 加载深度学习 GPU inpainter
            try:
                self.logger.info("Loading GPU-accelerated deep learning inpainter...")
                dl_loaded = self._load_gpu_inpainter_or_fallback()

                if dl_loaded:
                    self.logger.info("All AI models loaded successfully:")
                    self.logger.info("  - Watermark Detection: YOLO v11s deep learning (GPU)")
                    self.logger.info("  - Image Inpainting: GPU Deep Learning (U-Net)")
                    return detector_loaded and dl_loaded
                else:
                    self.logger.error("Failed to load deep learning inpainter")
                    self.logger.warning("Falling back to OpenCV inpainter")
                    # 继续使用 OpenCV inpainter
            except Exception as e:
                self.logger.error(f"Error loading DL inpainter: {e}")
                self.logger.warning("Falling back to OpenCV inpainter")
                self._disable_gpu_inpainting("gpu_inpainter_load_exception")

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

    def process_frame(  # noqa: C901
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
            self.last_inpainting_method_used = None
            self.last_inpainting_backend = None
            self.last_gpu_inpainting_profile_used = None
            self.last_gpu_inpainting_retry_info = None
            self.last_gpu_inpainting_oom_retry_used = False
            self.last_gpu_inpainting_retry_count = 0
            self.last_gpu_inpainting_retry_profile_used = None
            processing_info = {
                "original_shape": frame.shape,
                "detection_method": None,
                "inpainting_method": None,
                "inpainting_backend": None,
                "watermark_areas_found": 0,
                "processing_time": 0,
                "preprocessing_applied": [],
                "postprocessing_applied": [],
                "gpu_inpainting_requested": bool(self.requested_gpu_inpainting),
                "gpu_inpainting_fallback_reason": self.gpu_inpainting_fallback_reason,
                "configured_inpainting_model_path": self.configured_inpainting_model_path,
                "loaded_inpainting_model_path": self.loaded_inpainting_model_path,
                "gpu_inpainting_profile": None,
                "gpu_inpainting_retry": None,
                "gpu_inpainting_oom_retry_used": False,
                "gpu_inpainting_retry_count": 0,
                "gpu_inpainting_retry_profile": None,
                "requested_quality_level": self.quality_level,
                "effective_quality_level": None,
                "effective_inpaint_radius": None,
                "gpu_inpainting_runtime_error": None,
                "device": self.device,
            }

            start_time = time.time()
            mask = None

            # 保存原始帧（用于后处理混合）
            original_frame = frame.copy()

            # ====================================================================
            # 步骤0: 预处理（在检测前应用）
            # ====================================================================
            if any(
                [
                    self.enable_blur_preprocess,
                    self.enable_denoise_preprocess,
                    self.enable_sharp_preprocess,
                ]
            ):
                frame = apply_preprocessing(
                    frame,
                    enable_blur=self.enable_blur_preprocess,
                    enable_denoise=self.enable_denoise_preprocess,
                    enable_sharpen=self.enable_sharp_preprocess,
                )
                if self.enable_blur_preprocess:
                    processing_info["preprocessing_applied"].append("blur")
                if self.enable_denoise_preprocess:
                    processing_info["preprocessing_applied"].append("denoise")
                if self.enable_sharp_preprocess:
                    processing_info["preprocessing_applied"].append("sharpen")
                self.logger.debug(
                    f"Applied preprocessing: {processing_info['preprocessing_applied']}"
                )

            # ====================================================================
            # 步骤1: 确定水印区域
            # ====================================================================
            auto_detect_enabled = bool(watermark_selection_params.get("auto_detect", False))
            user_mask_data = (
                None if auto_detect_enabled else watermark_selection_params.get("user_mask")
            )

            if auto_detect_enabled and watermark_selection_params.get("user_mask") is not None:
                self.logger.debug("自动检测模式已启用，忽略静态 user_mask 以支持动态水印逐帧跟随")

            if user_mask_data is not None:
                # 处理用户提供的掩码（可能是区域列表或实际掩码）
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

            elif auto_detect_enabled:
                # 使用水印检测器进行自动检测
                if self.watermark_detector is None:
                    self.logger.error("Watermark detector not initialized")
                    return frame, {"error": "Watermark detector not initialized"}

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
                total_area = sum(cv2.contourArea(c) for c in contours)
                image_area = frame.shape[0] * frame.shape[1]
                area_ratio = total_area / image_area if image_area else 0

                # 记录使用的修复方法
                processing_info["inpainting_method"] = (
                    self.last_inpainting_method_used or processing_info["inpainting_method"]
                )
                processing_info["inpainting_backend"] = (
                    self.last_inpainting_backend or processing_info["inpainting_backend"]
                )
                processing_info["watermark_area_ratio"] = area_ratio
                processing_info["quality_level"] = self.quality_level
                processing_info["requested_quality_level"] = self.quality_level
                processing_info["effective_quality_level"] = getattr(
                    self, "last_effective_quality_level", None
                )
                processing_info["effective_inpaint_radius"] = getattr(
                    self, "last_effective_inpaint_radius", None
                )
                processing_info[
                    "gpu_inpainting_fallback_reason"
                ] = self.gpu_inpainting_fallback_reason
                processing_info["gpu_inpainting_runtime_error"] = getattr(
                    self, "last_gpu_inpainting_runtime_error", None
                )
                processing_info["loaded_inpainting_model_path"] = self.loaded_inpainting_model_path
                processing_info["gpu_inpainting_profile"] = getattr(
                    self,
                    "last_gpu_inpainting_profile_used",
                    None,
                )
                processing_info["gpu_inpainting_retry"] = getattr(
                    self,
                    "last_gpu_inpainting_retry_info",
                    None,
                )
                processing_info["gpu_inpainting_oom_retry_used"] = getattr(
                    self,
                    "last_gpu_inpainting_oom_retry_used",
                    False,
                )
                processing_info["gpu_inpainting_retry_count"] = getattr(
                    self,
                    "last_gpu_inpainting_retry_count",
                    0,
                )
                processing_info["gpu_inpainting_retry_profile"] = getattr(
                    self,
                    "last_gpu_inpainting_retry_profile_used",
                    None,
                )

                self.logger.info(
                    f"Processed frame with {len(contours)} watermark areas "
                    f"({area_ratio * 100:.1f}% of image)"
                )

                # ================================================================
                # 步骤3: 后处理（在修复后应用）
                # ================================================================
                if any(
                    [
                        self.enable_smooth_postprocess,
                        self.enable_blend_postprocess,
                        self.enable_enhance_postprocess,
                    ]
                ):
                    processed_frame = apply_postprocessing(
                        original_frame,
                        processed_frame,
                        mask,
                        enable_smooth=self.enable_smooth_postprocess,
                        enable_blend=self.enable_blend_postprocess,
                        enable_enhance=self.enable_enhance_postprocess,
                        **self._build_postprocess_profile(),
                    )
                    if self.enable_smooth_postprocess:
                        processing_info["postprocessing_applied"].append("smooth")
                    if self.enable_blend_postprocess:
                        processing_info["postprocessing_applied"].append("blend")
                    if self.enable_enhance_postprocess:
                        processing_info["postprocessing_applied"].append("enhance")
                    self.logger.debug(
                        f"Applied postprocessing: {processing_info['postprocessing_applied']}"
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
            detector = self.watermark_detector
            return detector.detect_watermark(frame)
        except Exception as e:
            self.logger.error(f"Error in direct watermark detection: {e}")
            return None

    def inpaint_frame(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:  # noqa: C901
        """
        直接调用图像修复功能

        支持 GPU 深度学习修复或 OpenCV 修复

        Args:
            frame: 输入图像，numpy数组(BGR格式)
            mask: 二值掩码，255=需要修复的区域，0=保持原始

        Returns:
            修复后的图像
        """
        try:
            self.logger.debug("Direct image inpainting called")
            self.last_inpainting_method_used = None
            self.last_inpainting_backend = None
            self.last_gpu_inpainting_profile_used = None
            self.last_gpu_inpainting_retry_info = None
            self.last_gpu_inpainting_oom_retry_used = False
            self.last_gpu_inpainting_retry_count = 0
            self.last_gpu_inpainting_retry_profile_used = None
            self.last_effective_quality_level = None
            self.last_effective_inpaint_radius = None
            self.last_gpu_inpainting_runtime_error = None

            # 优先使用深度学习 inpainter (如果已启用)
            if self.use_gpu_inpainting and self.dl_inpainter is not None:
                try:
                    dl_result = cast(
                        np.ndarray,
                        self.dl_inpainter.inpaint_frame(
                            frame,
                            mask,
                            radius=self.inpaint_radius,
                            quality_level=self.quality_level,
                        ),
                    )
                    profile_used = getattr(self.dl_inpainter, "last_profile_used", None)
                    if isinstance(profile_used, dict):
                        self.last_gpu_inpainting_profile_used = dict(profile_used)
                    retry_info = getattr(self.dl_inpainter, "last_retry_info", None)
                    if isinstance(retry_info, dict):
                        self.last_gpu_inpainting_retry_info = dict(retry_info)
                    self.last_gpu_inpainting_oom_retry_used = bool(
                        getattr(self.dl_inpainter, "last_oom_retry_used", False)
                    )
                    self.last_gpu_inpainting_retry_count = int(
                        getattr(self.dl_inpainter, "last_oom_retry_count", 0)
                    )
                    retry_profile_used = getattr(self.dl_inpainter, "last_retry_profile_used", None)
                    if isinstance(retry_profile_used, dict):
                        self.last_gpu_inpainting_retry_profile_used = dict(retry_profile_used)
                    self._update_effective_inpainting_observation_from_gpu_profile(
                        self.last_gpu_inpainting_profile_used
                        or self.last_gpu_inpainting_retry_profile_used
                    )
                    self.last_inpainting_method_used = "gpu_deep_learning_unet"
                    self.last_inpainting_backend = "gpu_deep_learning_unet"
                    typed_result = np.asarray(dl_result)
                    return cast(np.ndarray, typed_result)
                except Exception as exc:
                    self.last_gpu_inpainting_runtime_error = str(exc)
                    self._disable_gpu_inpainting(
                        "gpu_runtime_exception",
                        clear_loaded_model_path=False,
                    )
                    self.logger.error(
                        "GPU inpainting failed at runtime, falling back to OpenCV: %s",
                        exc,
                    )

            # 降级使用 OpenCV inpainter
            if hasattr(self, "image_inpainter") and self.image_inpainter is not None:
                resolved_method = self._resolve_opencv_inpainting_method()
                result = self.image_inpainter.inpaint_frame(
                    frame,
                    mask,
                    method=resolved_method,
                    radius=self.inpaint_radius,
                    quality_level=self.quality_level,
                )
                if result is None:
                    self.logger.warning("Inpainting returned None, using original frame")
                    return frame
                self.last_inpainting_backend = "opencv"
                self.last_inpainting_method_used = (
                    getattr(self.image_inpainter, "last_method_used", None) or resolved_method
                )
                self._update_effective_inpainting_observation_from_opencv()
                return cast(np.ndarray, result)

            self.logger.error("No inpainter available")
            return frame

        except Exception as e:
            self.logger.error(f"Error in direct image inpainting: {e}")
            return frame

    def _resolve_inpainting_model_path(self) -> Optional[str]:
        """解析 GPU 深度学习修复权重路径，优先使用 ai_params，其次读取配置。"""
        raw_path = self.ai_params.get("inpainting_model_path")
        if raw_path is None and self.config is not None and hasattr(self.config, "has_option"):
            for section in ("Models", "models"):
                try:
                    if self.config.has_option(section, "inpainting_model_path"):
                        raw_path = self.config.get(section, "inpainting_model_path")
                        break
                except Exception as exc:
                    self.logger.debug(
                        "读取 GPU 修复权重路径失败: section=%s error=%s",
                        section,
                        exc,
                    )

        if raw_path is None:
            return None

        normalized_path = str(raw_path).strip()
        if not normalized_path:
            return None

        return str(Path(normalized_path).expanduser())

    def _disable_gpu_inpainting(self, reason: str, clear_loaded_model_path: bool = True) -> None:
        """禁用 GPU 修复，并记录明确的降级原因。"""
        self.use_gpu_inpainting = False
        self.dl_inpainter = None
        if clear_loaded_model_path:
            self.loaded_inpainting_model_path = None
        self.gpu_inpainting_fallback_reason = reason

    def _load_gpu_inpainter_or_fallback(self) -> bool:
        """尝试加载 GPU 深度学习修复器，失败时明确降级到 OpenCV。"""
        model_path = self.configured_inpainting_model_path
        if not model_path:
            self.logger.warning(
                "GPU inpainting requested but no inpainting model path is configured; "
                "falling back to OpenCV"
            )
            self._disable_gpu_inpainting("missing_inpainting_model_path")
            return False

        if not Path(model_path).exists():
            self.logger.warning(
                f"GPU inpainting model path not found: {model_path}; " "falling back to OpenCV"
            )
            self._disable_gpu_inpainting("inpainting_model_path_not_found")
            return False

        self.dl_inpainter = DeepLearningInpainter(config=self.config, device=self.torch_device)
        if self.dl_inpainter.load_model(model_path=model_path):
            self.use_gpu_inpainting = True
            self.loaded_inpainting_model_path = model_path
            self.gpu_inpainting_fallback_reason = None
            return True

        self.logger.warning(
            f"Failed to load GPU inpainting model from {model_path}; falling back to OpenCV"
        )
        self._disable_gpu_inpainting("inpainting_model_load_failed")
        return False

    def _resolve_opencv_inpainting_method(self) -> str:
        """
        解析当前 OpenCV 路径应使用的修复算法。

        说明：
        - UI 明确选了 OpenCV 算法时，尊重用户选择
        - 若当前配置为 GPU 深度学习，但实际走到 OpenCV（例如降级），则回退到 auto
        """
        algorithm = (self.inpainting_algorithm or "gpu_dl").lower()
        method_mapping = {
            "telea": "telea",
            "navier_stokes": "navier_stokes",
            "custom_interpolation": "custom_interpolation",
            "auto": "auto",
        }
        return method_mapping.get(algorithm, "auto")

    def _build_postprocess_profile(self) -> dict:
        """根据质量等级构建后处理强度档位。"""
        quality = min(5, max(1, int(self.quality_level)))
        return {
            1: {
                "smooth_blur_radius": 3,
                "smooth_feather_amount": 1,
                "blend_ratio": 0.65,
                "enhance_contrast": 1.02,
                "enhance_brightness": 1,
                "enhance_saturation": 1.02,
            },
            2: {
                "smooth_blur_radius": 4,
                "smooth_feather_amount": 2,
                "blend_ratio": 0.72,
                "enhance_contrast": 1.06,
                "enhance_brightness": 3,
                "enhance_saturation": 1.06,
            },
            3: {
                "smooth_blur_radius": 5,
                "smooth_feather_amount": 3,
                "blend_ratio": 0.80,
                "enhance_contrast": 1.10,
                "enhance_brightness": 5,
                "enhance_saturation": 1.10,
            },
            4: {
                "smooth_blur_radius": 6,
                "smooth_feather_amount": 4,
                "blend_ratio": 0.86,
                "enhance_contrast": 1.14,
                "enhance_brightness": 7,
                "enhance_saturation": 1.14,
            },
            5: {
                "smooth_blur_radius": 7,
                "smooth_feather_amount": 5,
                "blend_ratio": 0.92,
                "enhance_contrast": 1.18,
                "enhance_brightness": 9,
                "enhance_saturation": 1.18,
            },
        }[quality]

    def _normalize_effective_quality_level(self, quality_level: Optional[int]) -> Optional[int]:
        """将追溯用质量等级限制在 1-5 之间。"""
        if quality_level is None:
            return None
        try:
            normalized = int(quality_level)
        except (TypeError, ValueError):
            return None
        return max(1, min(5, normalized))

    def _normalize_effective_inpaint_radius(self, radius: Optional[int]) -> Optional[int]:
        """将追溯用半径归一为正整数。"""
        if radius is None:
            return None
        try:
            normalized = int(radius)
        except (TypeError, ValueError):
            return None
        return max(1, normalized)

    def _update_effective_inpainting_observation_from_gpu_profile(
        self, profile: Optional[dict]
    ) -> None:
        """从 GPU profile 提取最终实际生效的观测字段。"""
        if not isinstance(profile, dict):
            return
        self.last_effective_quality_level = self._normalize_effective_quality_level(
            profile.get("quality_level")
        )
        self.last_effective_inpaint_radius = self._normalize_effective_inpaint_radius(
            profile.get("requested_radius")
        )

    def _update_effective_inpainting_observation_from_opencv(self) -> None:
        """从 OpenCV 修复器同步最终实际生效的观测字段。"""
        self.last_effective_quality_level = self._normalize_effective_quality_level(
            getattr(self.image_inpainter, "last_quality_level", None)
        )
        self.last_effective_inpaint_radius = self._normalize_effective_inpaint_radius(
            getattr(self.image_inpainter, "last_effective_radius", None)
        )


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
