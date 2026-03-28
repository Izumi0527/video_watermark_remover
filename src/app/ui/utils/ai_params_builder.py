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
6. 参数验证与范围检查

"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

import numpy as np
from numpy.typing import NDArray

from ...config.advanced_params import (
    AdvancedParamsSnapshot,
    ProcessingContext,
    ResolvedPerformanceConfig,
)
from ...config.validators import get_validator


def _get_optional_config_value(
    config: Any, option: str, sections: tuple[str, ...]
) -> Optional[str]:
    """
    从配置中读取可选字段（不存在则返回 None）。

    说明：该逻辑需要同时兼容大小写不同的 section（例如 Models / models）。
    """
    if config is None:
        return None

    for section in sections:
        try:
            if config.has_option(section, option):
                value = config.get(section, option).strip()
                return value or None
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).debug(
                "读取配置项失败: section=%s option=%s error=%s",
                section,
                option,
                exc,
            )
    return None


def _inject_inpainting_model_paths(
    ai_params: Optional[Dict[str, Any]],
    config: Any,
) -> Dict[str, Any]:
    """
    将配置中的修复模型路径注入 ai_params。

    背景：VideoProcessorThread 会在启动时做同样的注入（便于单/多进程链路共用）。
    预加载阶段也必须保持一致，否则首任务会命中 refresh 判定，导致二次加载。
    """
    merged_params = dict(ai_params or {})

    # 若 UI/调用方已明确传入，则不覆盖。
    if not merged_params.get("inpainting_model_path"):
        model_path = _get_optional_config_value(
            config, "inpainting_model_path", ("Models", "models")
        )
        if model_path:
            merged_params["inpainting_model_path"] = model_path

    if not merged_params.get("lama_model_path"):
        lama_model_path = _get_optional_config_value(
            config, "lama_model_path", ("Models", "models")
        )
        if lama_model_path:
            merged_params["lama_model_path"] = lama_model_path

    if not merged_params.get("lama_model_dir"):
        lama_model_dir = _get_optional_config_value(config, "lama_model_dir", ("Models", "models"))
        if lama_model_dir:
            merged_params["lama_model_dir"] = lama_model_dir

    return merged_params


def build_preload_ai_params_snapshot(
    *,
    preferences: Any,
    advanced_params: Dict[str, Any],
    config: Any,
) -> Dict[str, Any]:
    """
    构建“预加载 AIHandler”用的参数快照。

    目标：让启动阶段的预加载参数尽量与默认 UI 参数一致，避免首任务触发 refresh 再次加载。

    注意：
    - 这里只构建默认任务的参数快照，不涉及具体输入文件和手动框选区域。
    - 若用户在启动后修改了参数，运行时仍会触发 refresh，这是合理且必要的。
    """
    builder = AIParamsBuilder()
    ai_params = builder.build_from_ui(
        preferences=preferences,
        advanced_params=advanced_params,
        manual_selections=None,
        input_file_path=None,
    )
    return _inject_inpainting_model_paths(ai_params, config)


def build_preload_runtime_snapshot(
    *,
    preferences: Any,
    advanced_params: Dict[str, Any],
    config: Any,
) -> Dict[str, Any]:
    """
    构建预加载阶段使用的统一运行时快照。

    返回值同时包含：
    - `ai_params`：供 AIHandler 直接使用
    - `runtime_performance`：供日志/追溯导出使用
    """
    builder = AIParamsBuilder()
    runtime_config = builder.build_resolved_performance_config(
        advanced_params=advanced_params,
        input_file_path=None,
        is_batch=False,
    )
    ai_params = build_preload_ai_params_snapshot(
        preferences=preferences,
        advanced_params=advanced_params,
        config=config,
    )
    return {
        "ai_params": ai_params,
        "runtime_performance": runtime_config.to_manifest_dict(),
    }


class AIParamsBuilder:
    """
    AI参数构建器

    将前端UI参数转换为后端AI处理器所需的参数格式
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._validator = get_validator()

    def _is_cuda_available(self) -> bool:
        """判断当前环境是否可用 CUDA。"""
        try:
            torch_module = sys.modules.get("torch")
            if torch_module is None:
                return False
            return bool(torch_module.cuda.is_available())
        except Exception:  # noqa: BLE001
            return False

    def build_from_ui(
        self,
        preferences: Any,
        advanced_params: Dict[str, Any],
        manual_selections: Optional[List] = None,
        input_file_path: Optional[str] = None,
        is_batch: bool = False,
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
        auto_detect_enabled = preferences.get_preference("processing", "auto_mode", True)
        ai_params["auto_detect"] = auto_detect_enabled

        # 2. 检测参数
        detection_params = self._build_detection_params(advanced_params)
        ai_params.update(detection_params)

        # 3. 修复参数
        inpainting_params = self._build_inpainting_params(advanced_params)
        ai_params.update(inpainting_params)

        # 4. 性能参数
        performance_params = self._build_performance_params(
            advanced_params,
            input_file_path=input_file_path,
            is_batch=is_batch,
        )
        ai_params.update(performance_params)

        # 5. 输出参数
        output_params = self._build_output_params(
            advanced_params,
            input_file_path=input_file_path,
        )
        ai_params.update(output_params)

        # 6. 手动选择区域转换
        # 自动检测模式下必须忽略历史手动框，避免视频动态水印被静态区域短路
        if auto_detect_enabled:
            if manual_selections:
                self.logger.info(f"[参数构建] 当前为自动检测模式，忽略 {len(manual_selections)} 个手动选择区域")
            ai_params["user_mask"] = None
        else:
            user_mask = self._convert_manual_selections(manual_selections, input_file_path)
            ai_params["user_mask"] = user_mask

        self.logger.info(f"[参数构建] 成功构建AI参数，共 {len(ai_params)} 个参数")
        self.logger.debug(f"[参数详情] {ai_params}")

        return ai_params

    def _build_detection_params(self, advanced_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建检测参数（带验证）

        前端参数映射：
        - detection_sensitivity (0.1-1.0) → conf_threshold
        - detection_method (下拉框) → device ("cuda"/"cpu"/"auto")
        - min_detection_area (像素数) → min_area_pixels
        - enable_blur_preprocess → enable_blur_preprocess
        - enable_sharp_preprocess → enable_sharp_preprocess
        - enable_denoise_preprocess → enable_denoise_preprocess
        """
        params = {}

        # 检测敏感度 → YOLO置信度阈值（带验证）
        raw_sensitivity = advanced_params.get("detection_sensitivity", 0.5)
        params["conf_threshold"] = self._validator.validate("conf_threshold", raw_sensitivity)

        # 检测方法 → 设备选择（带验证）
        detection_method = advanced_params.get("detection_method", "YOLO v11x 深度学习auto (推荐)")
        raw_device = self._map_detection_method_to_device(detection_method)
        params["device"] = self._validator.validate("device", raw_device)

        # 最小检测区域（带验证）
        raw_min_area = advanced_params.get("min_detection_area", 100)
        params["min_area_pixels"] = self._validator.validate("min_area_pixels", raw_min_area)

        # 预处理选项（布尔值，无需验证）
        params["enable_blur_preprocess"] = advanced_params.get("enable_blur_preprocess", True)
        params["enable_sharp_preprocess"] = advanced_params.get("enable_sharp_preprocess", False)
        params["enable_denoise_preprocess"] = advanced_params.get("enable_denoise_preprocess", True)

        self.logger.debug(
            f"[检测参数] conf_threshold={params['conf_threshold']}, device={params['device']}"
        )

        return params

    def _build_inpainting_params(self, advanced_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建修复参数（带验证）

        前端参数映射：
        - inpainting_method (下拉框) → inpainting_algorithm
        - inpainting_radius (1-10) → inpaint_radius
        - inpainting_quality (1-5) → quality_level
        - enable_gpu (复选框) → use_gpu_inpainting（仅当选择 GPU U-Net 时生效）
        - enable_smooth_postprocess → enable_smooth_postprocess
        - enable_blend_postprocess → enable_blend_postprocess
        - enable_enhance_postprocess → enable_enhance_postprocess
        """
        params = {}

        # 修复方法（带验证）
        inpainting_method = advanced_params.get("inpainting_method", "LaMa 深度学习修复（推荐）")
        raw_algorithm = self._map_inpainting_method(inpainting_method)
        params["inpainting_algorithm"] = self._validator.validate(
            "inpainting_algorithm", raw_algorithm
        )
        params["requested_inpainting_backend"] = self._validator.validate(
            "requested_inpainting_backend",
            self._resolve_requested_inpainting_backend(
                inpainting_method, params["inpainting_algorithm"]
            ),
        )
        params["opencv_inpainting_method"] = self._validator.validate(
            "opencv_inpainting_method",
            self._resolve_opencv_inpainting_method(params["inpainting_algorithm"]),
        )

        # 修复半径（带验证）
        raw_radius = advanced_params.get("inpainting_radius", 3)
        params["inpaint_radius"] = self._validator.validate("inpaint_radius", raw_radius)

        # 修复质量等级（带验证）
        raw_quality = advanced_params.get("inpainting_quality", 3)
        params["quality_level"] = self._validator.validate("quality_level", raw_quality)

        # GPU 修复开关（布尔值）：仅当用户选择了 GPU 深度学习 U-Net 时才启用。
        # 否则即使勾选了“启用 GPU”，也应尊重 OpenCV 算法选择，避免“修复算法看起来不生效”。
        enable_gpu = bool(advanced_params.get("enable_gpu", True))
        cuda_available = self._is_cuda_available()
        params["use_gpu_inpainting"] = bool(
            enable_gpu
            and cuda_available
            and params["requested_inpainting_backend"] in {"legacy_unet", "lama", "mat"}
        )

        # 后处理选项（布尔值，无需验证）
        params["enable_smooth_postprocess"] = advanced_params.get("enable_smooth_postprocess", True)
        params["enable_blend_postprocess"] = advanced_params.get("enable_blend_postprocess", True)
        params["enable_enhance_postprocess"] = advanced_params.get(
            "enable_enhance_postprocess", False
        )

        self.logger.debug(
            f"[修复参数] backend={params['requested_inpainting_backend']}, "
            f"algorithm={params['inpainting_algorithm']}, "
            f"gpu={params['use_gpu_inpainting']}, radius={params['inpaint_radius']}"
        )

        return params

    def _build_performance_params(
        self,
        advanced_params: Dict[str, Any],
        *,
        input_file_path: Optional[str] = None,
        is_batch: bool = False,
    ) -> Dict[str, Any]:
        """
        构建性能参数（带验证）

        前端参数映射：
        - processing_mode → enable_multiprocess / use_pipeline
        - worker_count (0-16) → num_processes
        - gpu_memory_limit_mb (MB) → gpu_memory_mb
        - cache_size_mb (MB) → cache_size_mb
        - enable_cache → enable_cache
        """
        runtime_config = self.build_resolved_performance_config(
            advanced_params=advanced_params,
            input_file_path=input_file_path,
            is_batch=is_batch,
        )
        params = runtime_config.to_ai_params()

        self.logger.debug(
            "[性能参数] mode=%s resolved=%s num_processes=%s gpu_memory=%sMB cache=%s/%sMB",
            runtime_config.requested_processing_mode,
            runtime_config.resolved_processing_mode,
            runtime_config.worker_count,
            runtime_config.gpu_memory_budget_mb,
            runtime_config.enable_cache,
            runtime_config.cache_size_mb,
        )

        return params

    def build_resolved_performance_config(
        self,
        advanced_params: Dict[str, Any],
        *,
        input_file_path: Optional[str] = None,
        is_batch: bool = False,
    ) -> ResolvedPerformanceConfig:
        """从 UI 参数构建统一运行时性能配置。"""
        snapshot = AdvancedParamsSnapshot.from_dict(advanced_params)
        inpainting_method = advanced_params.get("inpainting_method", "LaMa 深度学习修复（推荐）")
        normalized_algorithm = self._map_inpainting_method(inpainting_method)
        requested_inpainting_backend = self._resolve_requested_inpainting_backend(
            inpainting_method,
            normalized_algorithm,
        )
        use_gpu_inpainting = bool(
            advanced_params.get("enable_gpu", snapshot.enable_gpu)
            and self._is_cuda_available()
            and requested_inpainting_backend in {"legacy_unet", "lama", "mat"}
        )
        context = ProcessingContext(
            input_file_path=input_file_path,
            is_batch=is_batch,
            prefer_pipeline=True,
            cpu_count=os.cpu_count() or 4,
            gpu_enabled=bool(advanced_params.get("enable_gpu", snapshot.enable_gpu)),
            requested_inpainting_backend=requested_inpainting_backend,
            use_gpu_inpainting=use_gpu_inpainting,
        )
        return snapshot.resolve(context)

    def build_batch_config(
        self,
        advanced_params: Dict[str, Any],
        *,
        input_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """从统一高级参数构建批处理策略配置。"""
        runtime_config = self.build_resolved_performance_config(
            advanced_params=advanced_params,
            input_file_path=input_file_path,
            is_batch=True,
        )
        return runtime_config.to_batch_config()

    def build_resolved_output_config(
        self,
        advanced_params: Dict[str, Any],
        *,
        input_file_path: Optional[str] = None,
    ):
        """从 UI 参数构建统一输出配置。"""
        snapshot = AdvancedParamsSnapshot.from_dict(advanced_params)
        return snapshot.resolve_output_config()

    def _build_output_params(
        self,
        advanced_params: Dict[str, Any],
        *,
        input_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构建输出参数，并统一收敛到高级参数快照。"""
        output_config = self.build_resolved_output_config(
            advanced_params,
            input_file_path=input_file_path,
        )
        params = output_config.to_ai_params()
        self.logger.debug(
            "[输出参数] format=%s, quality=%s, suffix=%s, timestamp=%s, preserve_audio=%s",
            params["output_format"],
            params["compression_quality"],
            params["add_suffix"],
            params["add_timestamp"],
            params["preserve_audio"],
        )
        return dict(params)

    def _convert_manual_selections(
        self, manual_selections: Optional[List], input_file_path: Optional[str] = None
    ) -> Optional[Any]:
        """
        将前端手动选择区域转换为后端可用格式

        Args:
            manual_selections: QRect对象列表、tuple列表或None
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
                # 智能识别输入格式并提取坐标
                if hasattr(rect, "x") and callable(getattr(rect, "x")):
                    # 格式1: QRect对象（PyQt6）
                    x = rect.x()
                    y = rect.y()
                    w = rect.width()
                    h = rect.height()
                    self.logger.debug(f"[手动选择] 识别为QRect对象: ({x}, {y}, {w}, {h})")
                elif isinstance(rect, (tuple, list)) and len(rect) == 4:
                    # 格式2: tuple/list (x, y, w, h)
                    x, y, w, h = rect
                    self.logger.debug(f"[手动选择] 识别为tuple/list: ({x}, {y}, {w}, {h})")
                elif isinstance(rect, dict):
                    # 格式3: dict {"x": x, "y": y, "width": w, "height": h}
                    x = rect.get("x", 0)
                    y = rect.get("y", 0)
                    w = rect.get("width", 0) or rect.get("w", 0)
                    h = rect.get("height", 0) or rect.get("h", 0)
                    self.logger.debug(f"[手动选择] 识别为dict: ({x}, {y}, {w}, {h})")
                else:
                    self.logger.warning(f"[手动选择] 未知格式: {type(rect)}, 跳过该区域")
                    continue

                regions.append((x, y, w, h))

            if not regions:
                self.logger.warning("[手动选择] 没有有效的选择区域")
                return None

            self.logger.info(f"[手动选择] 成功转换 {len(regions)} 个选择区域")
            self.logger.debug(f"[区域详情] {regions}")

            return regions

        except Exception as e:
            self.logger.error(f"[手动选择] 转换失败: {e}", exc_info=True)
            return None

    def _map_detection_method_to_device(self, detection_method: str) -> str:
        """
        映射检测方法到设备类型

        前端选项 → 后端device参数：
        - "YOLO v11x 深度学习auto (推荐)" → "auto"
        - "YOLO v11x GPU 加速" → "cuda"
        - "YOLO v11x CPU 模式" → "cpu"
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
        - "LaMa 深度学习修复（推荐）" → "gpu_dl"（兼容字段，实际后端由 requested_inpainting_backend 决定）
        - "兼容 U-Net 深度修复（旧模型）" → "gpu_dl"
        - "GPU 深度学习 U-Net (推荐)" → "gpu_dl"
        - "TELEA 快速修复 (OpenCV)" → "telea"
        - "Navier-Stokes 高质量 (OpenCV)" → "navier_stokes"
        - "自定义插值方法" → "custom_interpolation"
        """
        ui_mapping = {
            "LaMa 深度学习修复（推荐）": "gpu_dl",
            "兼容 U-Net 深度修复（旧模型）": "gpu_dl",
            "GPU 深度学习 U-Net (推荐)": "gpu_dl",
            "TELEA 快速修复 (OpenCV)": "telea",
            "Navier-Stokes 高质量 (OpenCV)": "navier_stokes",
            "自定义插值方法": "custom_interpolation",
        }
        normalized = str(inpainting_method or "").strip()
        if normalized in ui_mapping:
            return ui_mapping[normalized]

        lowered = normalized.lower()
        compact = lowered.replace("_", "").replace("-", "").replace(" ", "")
        compatibility_mapping = {
            "auto": "auto",
            "telea": "telea",
            "opencvtelea": "telea",
            "ns": "navier_stokes",
            "navierstokes": "navier_stokes",
            "custom": "custom_interpolation",
            "custominterpolation": "custom_interpolation",
            "gpudl": "gpu_dl",
            "gpuunet": "gpu_dl",
            "gpudeeplearningunet": "gpu_dl",
            "lama": "gpu_dl",
            "lamadeeplearningrepairrecommended": "gpu_dl",
        }
        if compact in compatibility_mapping:
            return compatibility_mapping[compact]

        self.logger.warning(
            "[修复参数] 未识别的 inpainting_method=%r，安全回退到 auto，避免误触发 GPU 路径",
            inpainting_method,
        )
        return "auto"

    def _resolve_requested_inpainting_backend(
        self, inpainting_method: str, normalized_algorithm: str
    ) -> str:
        """根据 UI 选择与兼容算法名，归一到统一后端枚举。"""
        normalized = str(inpainting_method or "").strip()
        compact = normalized.lower().replace("_", "").replace("-", "").replace(" ", "")
        if normalized == "LaMa 深度学习修复（推荐）" or compact == "lama":
            return "lama"
        if normalized == "兼容 U-Net 深度修复（旧模型）":
            return "legacy_unet"
        if normalized_algorithm == "gpu_dl":
            return "legacy_unet"
        return "opencv"

    def _resolve_opencv_inpainting_method(self, normalized_algorithm: str) -> str:
        """将兼容算法字段收敛成 OpenCV 专用方法枚举。"""
        if normalized_algorithm in {"telea", "navier_stokes", "custom_interpolation", "auto"}:
            return normalized_algorithm
        return "auto"

    def create_mask_from_regions(
        self, regions: List[tuple], image_shape: tuple
    ) -> NDArray[np.uint8]:
        """
        从区域列表创建二值掩码图像（备用方法）

        Args:
            regions: 区域列表 [(x, y, w, h), ...]
            image_shape: 图像形状 (height, width, channels)

        Returns:
            np.ndarray: 二值掩码 (height, width)，255表示水印区域
        """
        import cv2

        mask: NDArray[np.uint8] = np.zeros((image_shape[0], image_shape[1]), dtype=np.uint8)

        for x, y, w, h in regions:
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

        self.logger.debug(f"[掩码创建] 创建掩码: shape={mask.shape}, 区域数={len(regions)}")

        return mask
