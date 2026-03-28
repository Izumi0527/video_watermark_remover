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
from typing import Any, Optional, Tuple, cast

import cv2
import numpy as np
import torch

from ...utils.inpainting_model_downloader import resolve_inpainting_asset_ref
from .image_inpainter import ImageInpainter
from .image_processor import apply_postprocessing, apply_preprocessing
from .inpainting_backends.factory import create_inpainting_backend

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
        self.requested_inpainting_backend = self._derive_requested_inpainting_backend()
        self.opencv_inpainting_method = self._derive_opencv_inpainting_method()
        self.inpaint_radius = self.ai_params.get("inpaint_radius", 3)
        raw_quality_level = self.ai_params.get("quality_level", 3)
        self.quality_level = int(raw_quality_level) if raw_quality_level is not None else 3
        raw_gpu_memory_limit_mb = self.ai_params.get("gpu_memory_mb", 2048)
        self.gpu_memory_limit_mb = (
            int(raw_gpu_memory_limit_mb) if raw_gpu_memory_limit_mb is not None else 2048
        )
        self.effective_gpu_memory_budget_mb: Optional[int] = None

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
        self.opencv_inpainting_backend = None
        self.deep_inpainting_backend = None
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
        self.configured_lama_model_path = self._resolve_lama_model_path()
        self.configured_inpainting_asset_ref = self._resolve_inpainting_asset_ref()
        self.loaded_inpainting_model_path: Optional[str] = None
        self.loaded_inpainting_asset_ref: Optional[str] = None

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
            f"requested_inpainting_backend={self.requested_inpainting_backend}, "
            f"inpainting_algorithm={self.inpainting_algorithm}, "
            f"inpaint_radius={self.inpaint_radius}, "
            f"quality_level={self.quality_level}, "
            f"gpu_memory_limit_mb={self.gpu_memory_limit_mb}, "
            f"configured_inpainting_model_path={self.configured_inpainting_model_path}, "
            f"configured_inpainting_asset_ref={self.configured_inpainting_asset_ref}"
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
        opencv_loaded = self._ensure_opencv_backend_loaded()

        if self.use_gpu_inpainting:
            # 加载深度学习 GPU inpainter
            try:
                self.logger.info("Loading GPU-accelerated deep learning inpainter...")
                dl_loaded = self._load_gpu_inpainter_or_fallback()

                if dl_loaded:
                    detector = self.watermark_detector
                    detector_model_type = getattr(detector, "model_type", None) or "unknown"
                    detector_device = getattr(detector, "device", None) or self.device
                    self.logger.info("All AI models loaded successfully:")
                    self.logger.info(
                        "  - Watermark Detection: YOLO %s (device=%s)",
                        detector_model_type,
                        detector_device,
                    )
                    self.logger.info(
                        "  - Image Inpainting: %s",
                        self._describe_loaded_deep_inpainting_backend(),
                    )
                    return detector_loaded and dl_loaded
            except Exception as e:
                self.logger.error(f"加载深度修复后端时发生异常：{e}")
                self.logger.warning("当前改用 OpenCV 修复")
                self._disable_gpu_inpainting("gpu_inpainter_load_exception")

        # 3. 加载 OpenCV inpainter (作为默认或降级选项)
        if not self.use_gpu_inpainting:
            if detector_loaded and opencv_loaded:
                detector = self.watermark_detector
                detector_model_type = getattr(detector, "model_type", None) or "unknown"
                detector_device = getattr(detector, "device", None) or self.device
                self.logger.info("All AI models loaded successfully:")
                self.logger.info(
                    "  - Watermark Detection: YOLO %s (device=%s)",
                    detector_model_type,
                    detector_device,
                )
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
            return self._process_frame_internal(frame, watermark_selection_params)

        except Exception as e:
            self.logger.error(f"Error in frame processing: {e}")
            return frame, {"error": str(e)}

    def process_frames_batch(
        self,
        frames: list[np.ndarray],
        watermark_selection_params: dict,
    ) -> list[Tuple[np.ndarray, dict]]:
        """对一批帧复用批量检测，再逐帧执行修复。"""
        if not frames:
            return []

        auto_detect_enabled = bool(watermark_selection_params.get("auto_detect", False))
        if not auto_detect_enabled or watermark_selection_params.get("user_mask") is not None:
            return [self.process_frame(frame, watermark_selection_params) for frame in frames]

        detector = self.watermark_detector
        if detector is None or not hasattr(detector, "detect_batch"):
            return [self.process_frame(frame, watermark_selection_params) for frame in frames]

        prepared_frames: list[np.ndarray] = []
        processing_infos: list[dict] = []
        for frame in frames:
            if frame is None or frame.size == 0:
                return [self.process_frame(item, watermark_selection_params) for item in frames]
            processing_info = self._create_processing_info(frame)
            prepared_frames.append(self._apply_preprocessing_if_needed(frame, processing_info))
            processing_infos.append(processing_info)

        try:
            masks = detector.detect_batch(prepared_frames)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("批量检测失败，回退逐帧检测: %s", exc)
            return [self.process_frame(frame, watermark_selection_params) for frame in frames]

        precomputed_inpainting_results = self._try_batch_inpaint_frames(
            prepared_frames,
            masks,
        )

        results: list[Tuple[np.ndarray, dict]] = []
        for index, (frame, prepared_frame, mask, processing_info) in enumerate(
            zip(frames, prepared_frames, masks, processing_infos)
        ):
            self._reset_runtime_trace_fields()
            precomputed_result = precomputed_inpainting_results.get(index)
            results.append(
                self._finalize_processed_frame(
                    original_frame=frame,
                    working_frame=prepared_frame,
                    mask=mask,
                    processing_info=processing_info,
                    watermark_selection_params=watermark_selection_params,
                    detection_method="automatic_yolo",
                    precomputed_inpainting_result=precomputed_result,
                )
            )
        return results

    def _try_batch_inpaint_frames(
        self,
        frames: list[np.ndarray],
        masks: list[Optional[np.ndarray]],
    ) -> dict[int, dict]:
        """尝试对同批帧执行批量深度修复；失败时回退单帧路径。"""
        backend = getattr(self, "deep_inpainting_backend", None)
        if not self.use_gpu_inpainting or backend is None:
            return {}

        batch_inpaint = getattr(backend, "batch_inpaint_frames", None)
        if not callable(batch_inpaint):
            return {}

        candidate_indices = [
            index for index, mask in enumerate(masks) if mask is not None and np.any(mask)
        ]
        if not candidate_indices:
            return {}

        try:
            runtime_profile = self.build_gpu_runtime_profile(frames[0].shape)
            self._update_effective_inpainting_observation_from_gpu_profile(runtime_profile)
            batch_results = batch_inpaint(
                [frames[index] for index in candidate_indices],
                [masks[index] for index in candidate_indices],
                inpaint_radius=self.inpaint_radius,
                quality_level=self.quality_level,
                opencv_method="auto",
            )
            backend_trace: Any = getattr(backend, "get_last_trace", lambda: {})()
            if isinstance(backend_trace, dict):
                self.logger.info(
                    "批量 LaMa 修复命中: candidates=%s groups=%s group_sizes=%s resize_limit=%s memory_budget=%s",
                    backend_trace.get("batch_total_candidates", len(candidate_indices)),
                    backend_trace.get("batch_group_count", 1),
                    backend_trace.get("batch_group_sizes", [len(candidate_indices)]),
                    backend_trace.get("resize_limit", runtime_profile.get("resize_limit")),
                    backend_trace.get("memory_budget_mb", runtime_profile.get("memory_budget_mb")),
                )
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("批量 LaMa 修复失败，回退逐帧修复: %s", exc)
            return {}

        if len(batch_results) != len(candidate_indices):
            self.logger.warning(
                "批量 LaMa 修复返回数量异常，回退逐帧修复: expected=%s actual=%s",
                len(candidate_indices),
                len(batch_results),
            )
            return {}

        return {candidate_indices[index]: result for index, result in enumerate(batch_results)}

    def _process_frame_internal(
        self,
        frame: np.ndarray,
        watermark_selection_params: dict,
    ) -> Tuple[np.ndarray, dict]:
        self._reset_runtime_trace_fields()
        processing_info = self._create_processing_info(frame)
        working_frame = self._apply_preprocessing_if_needed(frame, processing_info)
        mask, detection_error = self._resolve_mask(
            working_frame,
            watermark_selection_params,
            processing_info,
        )
        if detection_error is not None:
            return frame, {"error": detection_error}
        return self._finalize_processed_frame(
            original_frame=frame,
            working_frame=working_frame,
            mask=mask,
            processing_info=processing_info,
            watermark_selection_params=watermark_selection_params,
        )

    def _reset_runtime_trace_fields(self) -> None:
        self.last_inpainting_method_used = None
        self.last_inpainting_backend = None
        self.last_gpu_inpainting_profile_used = None
        self.last_gpu_inpainting_retry_info = None
        self.last_gpu_inpainting_oom_retry_used = False
        self.last_gpu_inpainting_retry_count = 0
        self.last_gpu_inpainting_retry_profile_used = None

    def _create_processing_info(self, frame: np.ndarray) -> dict:
        requested_backend = self._derive_requested_inpainting_backend()
        return {
            "original_shape": frame.shape,
            "detection_method": None,
            "inpainting_method": None,
            "inpainting_backend": None,
            "requested_inpainting_backend": requested_backend,
            "actual_inpainting_backend": None,
            "inpainting_fallback_reason": self.gpu_inpainting_fallback_reason,
            "watermark_areas_found": 0,
            "processing_time": 0,
            "preprocessing_applied": [],
            "postprocessing_applied": [],
            "gpu_inpainting_requested": requested_backend in {"legacy_unet", "lama", "mat"},
            "gpu_inpainting_fallback_reason": self.gpu_inpainting_fallback_reason,
            "configured_inpainting_asset_ref": getattr(
                self, "configured_inpainting_asset_ref", None
            ),
            "loaded_inpainting_asset_ref": getattr(self, "loaded_inpainting_asset_ref", None),
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

    def _apply_preprocessing_if_needed(
        self, frame: np.ndarray, processing_info: dict
    ) -> np.ndarray:
        if not any(
            [
                self.enable_blur_preprocess,
                self.enable_denoise_preprocess,
                self.enable_sharp_preprocess,
            ]
        ):
            return frame

        processed = apply_preprocessing(
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
        self.logger.debug(f"Applied preprocessing: {processing_info['preprocessing_applied']}")
        return processed

    def _resolve_mask(  # noqa: C901
        self,
        frame: np.ndarray,
        watermark_selection_params: dict,
        processing_info: dict,
        *,
        precomputed_mask: Optional[np.ndarray] = None,
    ) -> tuple[Optional[np.ndarray], Optional[str]]:
        auto_detect_enabled = bool(watermark_selection_params.get("auto_detect", False))
        user_mask_data = (
            None if auto_detect_enabled else watermark_selection_params.get("user_mask")
        )

        if auto_detect_enabled and watermark_selection_params.get("user_mask") is not None:
            self.logger.debug("自动检测模式已启用，忽略静态 user_mask 以支持动态水印逐帧跟随")

        if user_mask_data is not None:
            if isinstance(user_mask_data, list) and len(user_mask_data) > 0:
                mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
                for region in user_mask_data:
                    if len(region) == 4:
                        x, y, w, h = region
                        x = max(0, min(x, frame.shape[1] - 1))
                        y = max(0, min(y, frame.shape[0] - 1))
                        w = max(1, min(w, frame.shape[1] - x))
                        h = max(1, min(h, frame.shape[0] - y))
                        cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

                processing_info["detection_method"] = "manual_selection"
                processing_info["manual_regions_count"] = len(user_mask_data)
                self.logger.info(f"Using manual selection with {len(user_mask_data)} regions")
                return mask, None

            if isinstance(user_mask_data, np.ndarray):
                mask = user_mask_data.copy()
                if len(mask.shape) == 3:
                    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
                processing_info["detection_method"] = "user_provided_mask"
                self.logger.info("Using user-provided mask array")
                return mask, None

            self.logger.warning("Invalid user_mask format")
            return None, "Invalid user_mask format"

        if auto_detect_enabled:
            if self.watermark_detector is None:
                self.logger.error("Watermark detector not initialized")
                return None, "Watermark detector not initialized"

            mask = precomputed_mask
            if mask is None:
                _ = watermark_selection_params.get("detection_sensitivity", 0.5)
                mask = self.watermark_detector.detect_watermark(frame)
            processing_info["detection_method"] = "automatic_yolo"
            detector = self.watermark_detector
            detector_model_type = getattr(detector, "model_type", None) or "unknown"
            detector_device = getattr(detector, "device", None) or self.device
            self.logger.debug(
                "Using automatic watermark detection (YOLO %s, device=%s)",
                detector_model_type,
                detector_device,
            )
            return mask, None

        self.logger.info("No watermark detection method specified")
        return None, None

    def _finalize_processed_frame(
        self,
        *,
        original_frame: np.ndarray,
        working_frame: np.ndarray,
        mask: Optional[np.ndarray],
        processing_info: dict,
        watermark_selection_params: dict,
        detection_method: Optional[str] = None,
        precomputed_inpainting_result: Optional[dict] = None,
    ) -> Tuple[np.ndarray, dict]:
        start_time = time.time()
        if detection_method:
            processing_info["detection_method"] = detection_method

        if processing_info["detection_method"] is None and not bool(
            watermark_selection_params.get("auto_detect", False)
        ):
            processing_info["processing_time"] = time.time() - start_time
            return working_frame, processing_info

        if mask is not None and np.any(mask):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            processing_info["watermark_areas_found"] = len(contours)

            if (
                isinstance(precomputed_inpainting_result, dict)
                and precomputed_inpainting_result.get("frame") is not None
            ):
                processed_frame = np.asarray(precomputed_inpainting_result["frame"])
                self._sync_trace_from_snapshot(precomputed_inpainting_result.get("trace"))
            else:
                processed_frame = self.inpaint_frame(working_frame, mask)
            total_area = sum(cv2.contourArea(c) for c in contours)
            image_area = working_frame.shape[0] * working_frame.shape[1]
            area_ratio = total_area / image_area if image_area else 0

            processing_info["inpainting_method"] = (
                self.last_inpainting_method_used or processing_info["inpainting_method"]
            )
            processing_info["actual_inpainting_backend"] = (
                self.last_inpainting_backend or processing_info["actual_inpainting_backend"]
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
            processing_info["gpu_inpainting_fallback_reason"] = self.gpu_inpainting_fallback_reason
            processing_info["inpainting_fallback_reason"] = self.gpu_inpainting_fallback_reason
            processing_info["gpu_inpainting_runtime_error"] = getattr(
                self, "last_gpu_inpainting_runtime_error", None
            )
            processing_info["loaded_inpainting_asset_ref"] = getattr(
                self, "loaded_inpainting_asset_ref", None
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

            self.logger.debug(
                f"Processed frame with {len(contours)} watermark areas "
                f"({area_ratio * 100:.1f}% of image)"
            )

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
            processed_frame = working_frame
            processing_info["watermark_areas_found"] = 0
            self.logger.debug("No watermark areas detected")

        processing_info["processing_time"] = time.time() - start_time
        return processed_frame, processing_info

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
            if self.use_gpu_inpainting and self.deep_inpainting_backend is not None:
                try:
                    self.build_gpu_runtime_profile(frame.shape)
                    dl_result = cast(
                        np.ndarray,
                        self.deep_inpainting_backend.inpaint_frame(
                            frame,
                            mask,
                            inpaint_radius=self.inpaint_radius,
                            quality_level=self.quality_level,
                            opencv_method="auto",
                        ),
                    )
                    self._sync_trace_from_deep_backend()
                    typed_result = np.asarray(dl_result)
                    return cast(np.ndarray, typed_result)
                except Exception as exc:
                    self.last_gpu_inpainting_runtime_error = str(exc)
                    self._disable_gpu_inpainting(
                        self._build_runtime_fallback_reason(),
                        clear_loaded_model_path=False,
                    )
                    self.logger.error(
                        "GPU inpainting failed at runtime, falling back to OpenCV: %s",
                        exc,
                    )

            # 降级使用 OpenCV inpainter
            if self._ensure_opencv_backend_loaded():
                backend = self.opencv_inpainting_backend
                if backend is None:
                    self.logger.error("OpenCV backend unexpectedly unavailable after load")
                    return frame
                resolved_method = self._resolve_opencv_inpainting_method()
                result = backend.inpaint_frame(
                    frame,
                    mask,
                    inpaint_radius=self.inpaint_radius,
                    quality_level=self.quality_level,
                    opencv_method=resolved_method,
                )
                if result is None:
                    self.logger.warning("Inpainting returned None, using original frame")
                    return frame
                self._sync_trace_from_opencv_backend()
                return cast(np.ndarray, result)

            self.logger.error("No inpainter available")
            return frame

        except Exception as e:
            self.logger.error(f"Error in direct image inpainting: {e}")
            return frame

    def _resolve_inpainting_model_path(self) -> Optional[str]:
        """解析 GPU 深度学习修复权重路径，优先使用 ai_params，其次读取配置。"""
        return resolve_inpainting_asset_ref(
            self.ai_params,
            self.config,
            ("inpainting_model_path",),
        )

    def _resolve_lama_model_path(self) -> Optional[str]:
        """解析 LaMa 资源路径。"""
        return resolve_inpainting_asset_ref(
            self.ai_params,
            self.config,
            ("lama_model_path", "lama_model_dir"),
        )

    def _resolve_inpainting_asset_ref(self) -> Optional[str]:
        """根据请求 backend 解析当前实际需要的资源引用。"""
        requested_backend = self._derive_requested_inpainting_backend()
        if requested_backend == "lama":
            return self.configured_lama_model_path
        return self.configured_inpainting_model_path

    def _describe_loaded_deep_inpainting_backend(self) -> str:
        """返回当前已加载深度修复 backend 的人类可读描述。"""
        backend_id = (
            str(getattr(self.deep_inpainting_backend, "backend_id", "") or "").strip().lower()
        )
        label_mapping = {
            "legacy_unet": "GPU Deep Learning (U-Net)",
            "lama": "LaMa TorchScript",
            "mat": "MAT",
        }
        return label_mapping.get(backend_id, "GPU Deep Learning")

    def _disable_gpu_inpainting(self, reason: str, clear_loaded_model_path: bool = True) -> None:
        """禁用 GPU 修复，并记录明确的降级原因。"""
        self.use_gpu_inpainting = False
        self.dl_inpainter = None
        self.deep_inpainting_backend = None
        if clear_loaded_model_path:
            self.loaded_inpainting_model_path = None
            self.loaded_inpainting_asset_ref = None
        self.gpu_inpainting_fallback_reason = reason

    def _load_gpu_inpainter_or_fallback(self) -> bool:
        """尝试加载 GPU 深度学习修复器，失败时明确降级到 OpenCV。"""
        self.deep_inpainting_backend = create_inpainting_backend(
            self._derive_requested_inpainting_backend(),
            config=self.config,
            torch_device=self.torch_device,
            dl_inpainter=self.dl_inpainter,
            model_path=self.configured_inpainting_asset_ref,
        )
        if getattr(self.deep_inpainting_backend, "backend_id", None) not in {"legacy_unet", "lama"}:
            self.logger.warning(
                "Unsupported deep inpainting backend requested; falling back to OpenCV"
            )
            self._disable_gpu_inpainting("unsupported_gpu_backend")
            return False

        if self.deep_inpainting_backend.load():
            self.dl_inpainter = getattr(self.deep_inpainting_backend, "dl_inpainter", None)
            self.use_gpu_inpainting = True
            self.loaded_inpainting_model_path = getattr(
                self.deep_inpainting_backend,
                "loaded_model_path",
                None,
            ) or getattr(
                self.deep_inpainting_backend,
                "loaded_asset_ref",
                self.configured_inpainting_asset_ref,
            )
            self.loaded_inpainting_asset_ref = getattr(
                self.deep_inpainting_backend,
                "loaded_asset_ref",
                self.loaded_inpainting_model_path,
            )
            self.gpu_inpainting_fallback_reason = None
            return True

        load_trace = self.deep_inpainting_backend.get_last_trace()
        load_failure_reason = load_trace.get("load_failure_reason", "inpainting_model_load_failed")
        self._disable_gpu_inpainting(str(load_failure_reason))
        self._log_gpu_inpainting_load_failure(
            str(load_failure_reason),
            load_trace.get("load_failure_detail"),
        )
        return False

    def _log_gpu_inpainting_load_failure(
        self,
        reason: str,
        detail: Optional[str] = None,
    ) -> None:
        """区分可预期降级与真实加载故障，输出更准确的日志。"""
        if reason == "missing_lama_model_path":
            self.logger.warning(
                "未配置 LaMa 模型路径，当前改用 OpenCV 修复。可设置 lama_model_path 或 VWR_LAMA_MODEL_PATH。"
            )
            return

        if reason == "missing_inpainting_model_path":
            self.logger.warning(
                "未配置 GPU 修复模型路径，当前改用 OpenCV 修复。可设置 inpainting_model_path 或 VWR_INPAINTING_MODEL_PATH。"
            )
            return

        if detail:
            self.logger.error("GPU 深度修复加载失败：%s | %s", reason, detail)
        else:
            self.logger.error("GPU 深度修复加载失败：%s", reason)
        self.logger.warning("当前改用 OpenCV 修复")

    def _ensure_opencv_backend_loaded(self) -> bool:
        """确保 OpenCV backend 已创建并完成加载。"""
        if self.opencv_inpainting_backend is None:
            self.opencv_inpainting_backend = create_inpainting_backend(
                "opencv",
                config=self.config,
                torch_device=self.torch_device,
                image_inpainter=self.image_inpainter,
            )
            self.image_inpainter = getattr(
                self.opencv_inpainting_backend,
                "image_inpainter",
                self.image_inpainter,
            )
        return bool(self.opencv_inpainting_backend.load())

    def _resolve_effective_gpu_memory_budget_mb(self) -> int:
        """解析当前深度修复链路实际可用的软显存预算。"""
        requested_budget_mb = max(256, int(self.gpu_memory_limit_mb))
        effective_budget_mb = requested_budget_mb

        if self.device == "cuda":
            try:
                mem_get_info = getattr(getattr(torch, "cuda", None), "mem_get_info", None)
                if callable(mem_get_info):
                    free_bytes, _ = mem_get_info()
                    free_mb = max(256, int(free_bytes / (1024 * 1024)))
                    effective_budget_mb = min(requested_budget_mb, free_mb)
            except Exception as exc:  # noqa: BLE001
                self.logger.debug("读取 CUDA 可用显存失败，继续使用请求预算: %s", exc)

        self.effective_gpu_memory_budget_mb = effective_budget_mb
        return effective_budget_mb

    def _resolve_runtime_resize_limit_from_budget(self, memory_budget_mb: int) -> int:
        """把软显存预算映射为更保守的推理尺寸上限。"""
        requested_backend = self._derive_requested_inpainting_backend()
        if requested_backend == "lama":
            if memory_budget_mb <= 1024:
                return 640
            if memory_budget_mb <= 1536:
                return 768
            return 960

        if memory_budget_mb <= 1024:
            return 640
        if memory_budget_mb <= 1536:
            return 768
        if memory_budget_mb <= 2048:
            return 960
        return 1152

    def build_gpu_runtime_profile(self, frame_shape: tuple[int, ...]) -> dict[str, object]:
        """构建当前帧的 GPU 运行时预算快照，并同步到深度修复器。"""
        memory_budget_mb = self._resolve_effective_gpu_memory_budget_mb()
        runtime_profile = {
            "frame_shape": tuple(frame_shape),
            "memory_budget_mb": memory_budget_mb,
            "resize_limit": self._resolve_runtime_resize_limit_from_budget(memory_budget_mb),
            "requested_radius": int(self.inpaint_radius),
            "quality_level": int(self.quality_level),
        }

        if self.dl_inpainter is not None:
            set_budget = getattr(self.dl_inpainter, "set_runtime_memory_budget", None)
            if callable(set_budget):
                set_budget(memory_budget_mb)
            else:
                setattr(self.dl_inpainter, "memory_budget_mb", memory_budget_mb)

        if self.deep_inpainting_backend is not None:
            set_runtime_profile = getattr(self.deep_inpainting_backend, "set_runtime_profile", None)
            if callable(set_runtime_profile):
                set_runtime_profile(runtime_profile)

        return runtime_profile

    def _sync_trace_from_opencv_backend(self) -> None:
        """把 OpenCV backend trace 同步回历史兼容字段。"""
        if self.opencv_inpainting_backend is None:
            return
        trace = self.opencv_inpainting_backend.get_last_trace()
        self._sync_trace_from_snapshot(trace, default_backend="opencv", default_method=None)

    def _sync_trace_from_deep_backend(self) -> None:
        """把 deep backend trace 同步回历史兼容字段。"""
        if self.deep_inpainting_backend is None:
            return
        trace = self.deep_inpainting_backend.get_last_trace()
        self._sync_trace_from_snapshot(
            trace,
            default_backend="gpu_deep_learning_unet",
            default_method="gpu_deep_learning_unet",
        )

    def _sync_trace_from_snapshot(
        self,
        trace: Optional[dict],
        *,
        default_backend: Optional[str] = None,
        default_method: Optional[str] = None,
    ) -> None:
        """把显式 trace 快照同步回兼容字段。"""
        normalized_trace = dict(trace or {})
        self.last_inpainting_backend = normalized_trace.get("inpainting_backend", default_backend)
        self.last_inpainting_method_used = normalized_trace.get("inpainting_method", default_method)
        profile_used = normalized_trace.get("gpu_inpainting_profile")
        if isinstance(profile_used, dict):
            self.last_gpu_inpainting_profile_used = dict(profile_used)
        retry_info = normalized_trace.get("gpu_inpainting_retry")
        if isinstance(retry_info, dict):
            self.last_gpu_inpainting_retry_info = dict(retry_info)
        self.last_gpu_inpainting_oom_retry_used = bool(
            normalized_trace.get("gpu_inpainting_oom_retry_used", False)
        )
        self.last_gpu_inpainting_retry_count = int(
            normalized_trace.get("gpu_inpainting_retry_count", 0)
        )
        retry_profile = normalized_trace.get("gpu_inpainting_retry_profile")
        if isinstance(retry_profile, dict):
            self.last_gpu_inpainting_retry_profile_used = dict(retry_profile)
        self.last_effective_quality_level = self._normalize_effective_quality_level(
            normalized_trace.get("effective_quality_level")
        )
        self.last_effective_inpaint_radius = self._normalize_effective_inpaint_radius(
            normalized_trace.get("effective_inpaint_radius")
        )
        if normalized_trace.get("loaded_inpainting_asset_ref") is not None:
            self.loaded_inpainting_asset_ref = normalized_trace.get("loaded_inpainting_asset_ref")
        if normalized_trace.get("loaded_inpainting_model_path") is not None:
            self.loaded_inpainting_model_path = normalized_trace.get("loaded_inpainting_model_path")

    def _build_runtime_fallback_reason(self) -> str:
        """根据请求 backend 生成运行期降级原因。"""
        requested_backend = self._derive_requested_inpainting_backend()
        if requested_backend == "lama":
            return "lama_runtime_exception"
        if requested_backend == "mat":
            return "mat_runtime_exception"
        return "gpu_runtime_exception"

    def _resolve_opencv_inpainting_method(self) -> str:
        """
        解析当前 OpenCV 路径应使用的修复算法。

        说明：
        - UI 明确选了 OpenCV 算法时，尊重用户选择
        - 若当前配置为 GPU 深度学习，但实际走到 OpenCV（例如降级），则回退到 auto
        """
        if self._derive_requested_inpainting_backend() != "opencv":
            return "auto"

        algorithm = (self.opencv_inpainting_method or self.inpainting_algorithm or "auto").lower()
        method_mapping = {
            "telea": "telea",
            "navier_stokes": "navier_stokes",
            "custom_interpolation": "custom_interpolation",
            "auto": "auto",
        }
        return method_mapping.get(algorithm, "auto")

    def _derive_requested_inpainting_backend(self) -> str:
        """从新旧参数推导统一的请求后端枚举。"""
        ai_params = getattr(self, "ai_params", {}) or {}
        raw_backend = str(ai_params.get("requested_inpainting_backend", "") or "").strip().lower()
        if raw_backend in {"opencv", "lama", "legacy_unet", "mat"}:
            return raw_backend

        algorithm = str(self.inpainting_algorithm or "auto").strip().lower()
        if algorithm == "gpu_dl" or bool(getattr(self, "requested_gpu_inpainting", False)):
            return "legacy_unet"
        return "opencv"

    def _derive_opencv_inpainting_method(self) -> str:
        """从新旧参数推导 OpenCV 专用方法。"""
        ai_params = getattr(self, "ai_params", {}) or {}
        raw_method = str(ai_params.get("opencv_inpainting_method", "") or "").strip().lower()
        if raw_method in {"auto", "telea", "navier_stokes", "custom_interpolation"}:
            return raw_method

        algorithm = str(self.inpainting_algorithm or "auto").strip().lower()
        if algorithm in {"auto", "telea", "navier_stokes", "custom_interpolation"}:
            return algorithm
        return "auto"

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
