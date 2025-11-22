#!/usr/bin/env python3
"""
AI参数构建器

负责将前端UI参数转换为后端AI模块可用的参数格式

功能：
1. 从AdvancedParametersWidget获取所有UI参数
2. 从PreferencesManager获取基础设置
3. 转换手动选择区域为后端格式
4. 映射前端参数名到后端参数名
5. 构建完整的ai_params字典

作者: Claude Code Assistant
创建时间: 2025-11-16
版本: v1.0
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np


class AIParamsBuilder:
    """
    AI参数构建器

    将前端UI参数转换为后端AI处理器所需的参数格式
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def build_from_ui(
        self,
        preferences: Any,
        advanced_params: Dict[str, Any],
        manual_selections: Optional[List] = None,
        input_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        从UI组件构建完整的AI参数字典

        Args:
            preferences: PreferencesManager实例
            advanced_params: AdvancedParametersWidget返回的参数字典
            manual_selections: 手动选择的区域列表
            input_file_path: 输入文件路径（用于转换手动选择区域）

        Returns:
            dict: 完整的ai_params字典
        """
        ai_params = {}

        # 1. 基础设置（从Preferences）
        ai_params["auto_detect"] = preferences.get_preference(
            "processing", "auto_mode", True
        )

        # 2. 检测参数
        detection_params = self._build_detection_params(advanced_params)
        ai_params.update(detection_params)

        # 3. 修复参数
        inpainting_params = self._build_inpainting_params(advanced_params)
        ai_params.update(inpainting_params)

        # 4. 性能参数
        performance_params = self._build_performance_params(advanced_params)
        ai_params.update(performance_params)

        # 5. 输出参数
        output_params = self._build_output_params(advanced_params)
        ai_params.update(output_params)

        # 6. 手动选择区域转换
        user_mask = self._convert_manual_selections(
            manual_selections, input_file_path
        )
        ai_params["user_mask"] = user_mask

        self.logger.info(f"[参数构建] 成功构建AI参数，共 {len(ai_params)} 个参数")
        self.logger.debug(f"[参数详情] {ai_params}")

        return ai_params

    def _build_detection_params(self, advanced_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建检测参数

        前端参数映射：
        - detection_sensitivity (0.1-1.0) → conf_threshold
        - detection_method (下拉框) → device ("cuda"/"cpu"/"auto")
        - min_detection_area (像素数) → min_area_pixels
        - enable_blur_preprocess → enable_blur_preprocess
        - enable_sharp_preprocess → enable_sharp_preprocess
        - enable_denoise_preprocess → enable_denoise_preprocess
        """
        params = {}

        # 检测敏感度 → YOLO置信度阈值
        params["conf_threshold"] = advanced_params.get("detection_sensitivity", 0.5)

        # 检测方法 → 设备选择
        detection_method = advanced_params.get("detection_method", "YOLO v11s 深度学习 (推荐)")
        params["device"] = self._map_detection_method_to_device(detection_method)

        # 最小检测区域
        params["min_area_pixels"] = advanced_params.get("min_detection_area", 100)

        # 预处理选项
        params["enable_blur_preprocess"] = advanced_params.get("enable_blur_preprocess", True)
        params["enable_sharp_preprocess"] = advanced_params.get("enable_sharp_preprocess", False)
        params["enable_denoise_preprocess"] = advanced_params.get("enable_denoise_preprocess", True)

        self.logger.debug(f"[检测参数] conf_threshold={params['conf_threshold']}, device={params['device']}")

        return params

    def _build_inpainting_params(self, advanced_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建修复参数

        前端参数映射：
        - inpainting_method (下拉框) → inpainting_algorithm
        - inpainting_radius (1-10) → inpaint_radius
        - inpainting_quality (1-5) → quality_level
        - enable_gpu (复选框) → use_gpu_inpainting
        - enable_smooth_postprocess → enable_smooth_postprocess
        - enable_blend_postprocess → enable_blend_postprocess
        - enable_enhance_postprocess → enable_enhance_postprocess
        """
        params = {}

        # 修复方法
        inpainting_method = advanced_params.get("inpainting_method", "GPU 深度学习 U-Net (推荐)")
        params["inpainting_algorithm"] = self._map_inpainting_method(inpainting_method)

        # 修复半径
        params["inpaint_radius"] = advanced_params.get("inpainting_radius", 3)

        # 修复质量等级
        params["quality_level"] = advanced_params.get("inpainting_quality", 3)

        # GPU加速开关
        params["use_gpu_inpainting"] = advanced_params.get("enable_gpu", True)

        # 后处理选项
        params["enable_smooth_postprocess"] = advanced_params.get("enable_smooth_postprocess", True)
        params["enable_blend_postprocess"] = advanced_params.get("enable_blend_postprocess", True)
        params["enable_enhance_postprocess"] = advanced_params.get("enable_enhance_postprocess", False)

        self.logger.debug(
            f"[修复参数] algorithm={params['inpainting_algorithm']}, "
            f"gpu={params['use_gpu_inpainting']}, radius={params['inpaint_radius']}"
        )

        return params

    def _build_performance_params(self, advanced_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建性能参数

        前端参数映射：
        - thread_count (1-16) → num_processes
        - gpu_memory_limit (MB) → gpu_memory_mb
        - cache_size (MB) → cache_size_mb
        - enable_cache → enable_cache
        """
        params = {}

        # 线程/进程数量
        params["num_processes"] = advanced_params.get("thread_count", 4)

        # GPU内存限制
        params["gpu_memory_mb"] = advanced_params.get("gpu_memory_limit", 2048)

        # 缓存大小
        params["cache_size_mb"] = advanced_params.get("cache_size", 512)

        # 缓存开关
        params["enable_cache"] = advanced_params.get("enable_cache", True)

        self.logger.debug(
            f"[性能参数] num_processes={params['num_processes']}, "
            f"gpu_memory={params['gpu_memory_mb']}MB"
        )

        return params

    def _build_output_params(self, advanced_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建输出参数

        前端参数映射：
        - output_format → output_format
        - compression_quality (1-100) → compression_quality
        - add_suffix → add_processed_suffix
        - add_timestamp → add_timestamp
        """
        params = {}

        # 输出格式
        params["output_format"] = advanced_params.get("output_format", "保持原格式")

        # 压缩质量
        params["compression_quality"] = advanced_params.get("compression_quality", 85)

        # 文件名后缀
        params["add_processed_suffix"] = advanced_params.get("add_suffix", True)

        # 时间戳
        params["add_timestamp"] = advanced_params.get("add_timestamp", False)

        self.logger.debug(
            f"[输出参数] format={params['output_format']}, "
            f"quality={params['compression_quality']}"
        )

        return params

    def _convert_manual_selections(
        self,
        manual_selections: Optional[List],
        input_file_path: Optional[str] = None
    ) -> Optional[Any]:
        """
        将前端手动选择区域转换为后端可用格式

        Args:
            manual_selections: QRect对象列表或None
            input_file_path: 输入文件路径（用于创建掩码时获取图像尺寸）

        Returns:
            区域列表 [(x, y, w, h), ...] 或 None
        """
        if not manual_selections:
            self.logger.debug("[手动选择] 无手动选择区域")
            return None

        try:
            regions = []
            for rect in manual_selections:
                # 从QRect提取坐标和尺寸
                x = rect.x()
                y = rect.y()
                w = rect.width()
                h = rect.height()
                regions.append((x, y, w, h))

            self.logger.info(f"[手动选择] 成功转换 {len(regions)} 个选择区域")
            self.logger.debug(f"[区域详情] {regions}")

            return regions

        except Exception as e:
            self.logger.error(f"[手动选择] 转换失败: {e}")
            return None

    def _map_detection_method_to_device(self, detection_method: str) -> str:
        """
        映射检测方法到设备类型

        前端选项 → 后端device参数：
        - "YOLO v11s 深度学习 (推荐)" → "auto"
        - "YOLO v11s GPU 加速" → "cuda"
        - "YOLO v11s CPU 模式" → "cpu"
        """
        if "GPU" in detection_method or "gpu" in detection_method.lower():
            return "cuda"
        elif "CPU" in detection_method or "cpu" in detection_method.lower():
            return "cpu"
        else:
            return "auto"  # 自动检测

    def _map_inpainting_method(self, inpainting_method: str) -> str:
        """
        映射修复方法到算法标识

        前端选项 → 后端algorithm参数：
        - "GPU 深度学习 U-Net (推荐)" → "gpu_dl"
        - "TELEA 快速修复 (OpenCV)" → "telea"
        - "Navier-Stokes 高质量 (OpenCV)" → "navier_stokes"
        - "自定义插值方法" → "custom_interpolation"
        """
        method_mapping = {
            "GPU 深度学习 U-Net (推荐)": "gpu_dl",
            "TELEA 快速修复 (OpenCV)": "telea",
            "Navier-Stokes 高质量 (OpenCV)": "navier_stokes",
            "自定义插值方法": "custom_interpolation",
        }

        return method_mapping.get(inpainting_method, "gpu_dl")

    def create_mask_from_regions(
        self,
        regions: List[tuple],
        image_shape: tuple
    ) -> np.ndarray:
        """
        从区域列表创建二值掩码图像（备用方法）

        Args:
            regions: 区域列表 [(x, y, w, h), ...]
            image_shape: 图像形状 (height, width, channels)

        Returns:
            np.ndarray: 二值掩码 (height, width)，255表示水印区域
        """
        import cv2

        mask = np.zeros((image_shape[0], image_shape[1]), dtype=np.uint8)

        for x, y, w, h in regions:
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

        self.logger.debug(f"[掩码创建] 创建掩码: shape={mask.shape}, 区域数={len(regions)}")

        return mask
