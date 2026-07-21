#!/usr/bin/env python3
"""
配置参数验证器模块

提供参数范围验证和类型检查功能：
1. 数值范围验证
2. 类型转换与验证
3. 枚举值验证
4. 自动回退到默认值

"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class ValidationRule:
    """验证规则定义"""

    param_name: str
    param_type: type
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    description: str = ""


class ConfigValidator:
    """
    配置参数验证器

    提供统一的参数验证、类型转换和默认值回退功能
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._rules = self._define_validation_rules()

    def _define_validation_rules(self) -> Dict[str, ValidationRule]:
        """定义所有参数的验证规则"""
        return {
            # ============ 检测参数 ============
            "detection_sensitivity": ValidationRule(
                param_name="detection_sensitivity",
                param_type=float,
                default=0.5,
                min_value=0.0,
                max_value=1.0,
                description="检测敏感度 (0.0-1.0)",
            ),
            "conf_threshold": ValidationRule(
                param_name="conf_threshold",
                param_type=float,
                default=0.5,
                min_value=0.0,
                max_value=1.0,
                description="YOLO置信度阈值 (0.0-1.0)",
            ),
            "min_detection_area": ValidationRule(
                param_name="min_detection_area",
                param_type=int,
                default=100,
                min_value=1,
                max_value=10000,
                description="最小检测区域像素数 (1-10000)",
            ),
            "min_area_pixels": ValidationRule(
                param_name="min_area_pixels",
                param_type=int,
                default=100,
                min_value=1,
                max_value=10000,
                description="最小区域像素数 (1-10000)",
            ),
            # ============ 修复参数 ============
            "inpainting_radius": ValidationRule(
                param_name="inpainting_radius",
                param_type=int,
                default=3,
                min_value=1,
                max_value=10,
                description="修复半径 (1-10)",
            ),
            "inpaint_radius": ValidationRule(
                param_name="inpaint_radius",
                param_type=int,
                default=3,
                min_value=1,
                max_value=10,
                description="修复半径 (1-10)",
            ),
            "inpainting_quality": ValidationRule(
                param_name="inpainting_quality",
                param_type=int,
                default=3,
                min_value=1,
                max_value=5,
                description="修复质量等级 (1-5)",
            ),
            "quality_level": ValidationRule(
                param_name="quality_level",
                param_type=int,
                default=3,
                min_value=1,
                max_value=5,
                description="质量等级 (1-5)",
            ),
            # ============ 性能参数 ============
            "thread_count": ValidationRule(
                param_name="thread_count",
                param_type=int,
                default=4,
                min_value=1,
                max_value=16,
                description="线程/进程数量 (1-16)",
            ),
            "num_processes": ValidationRule(
                param_name="num_processes",
                param_type=int,
                default=4,
                min_value=1,
                max_value=16,
                description="进程数量 (1-16)",
            ),
            "gpu_memory_limit": ValidationRule(
                param_name="gpu_memory_limit",
                param_type=int,
                default=2048,
                min_value=256,
                max_value=32768,
                description="GPU内存限制MB (256-32768)",
            ),
            "gpu_memory_mb": ValidationRule(
                param_name="gpu_memory_mb",
                param_type=int,
                default=2048,
                min_value=256,
                max_value=32768,
                description="GPU内存MB (256-32768)",
            ),
            "cache_size": ValidationRule(
                param_name="cache_size",
                param_type=int,
                default=512,
                min_value=64,
                max_value=8192,
                description="缓存大小MB (64-8192)",
            ),
            "cache_size_mb": ValidationRule(
                param_name="cache_size_mb",
                param_type=int,
                default=512,
                min_value=64,
                max_value=8192,
                description="缓存大小MB (64-8192)",
            ),
            # ============ 输出参数 ============
            "compression_quality": ValidationRule(
                param_name="compression_quality",
                param_type=int,
                default=85,
                min_value=1,
                max_value=100,
                description="压缩质量 (1-100)",
            ),
            # ============ 日志参数 ============
            "log_level": ValidationRule(
                param_name="log_level",
                param_type=str,
                default="INFO",
                allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                description="日志级别",
            ),
            # ============ 设备参数 ============
            "device": ValidationRule(
                param_name="device",
                param_type=str,
                default="auto",
                allowed_values=["auto", "cuda", "cpu", "mps"],
                description="计算设备",
            ),
            "gpu_acceleration": ValidationRule(
                param_name="gpu_acceleration",
                param_type=str,
                default="auto",
                allowed_values=["auto", "on", "off"],
                description="GPU加速模式",
            ),
            # ============ 算法参数 ============
            "inpainting_algorithm": ValidationRule(
                param_name="inpainting_algorithm",
                param_type=str,
                default="auto",
                allowed_values=["auto", "gpu_dl", "telea", "navier_stokes", "custom_interpolation"],
                description="修复算法",
            ),
            "requested_inpainting_backend": ValidationRule(
                param_name="requested_inpainting_backend",
                param_type=str,
                default="opencv",
                allowed_values=["opencv", "lama", "mat"],
                description="请求的修复后端",
            ),
            "opencv_inpainting_method": ValidationRule(
                param_name="opencv_inpainting_method",
                param_type=str,
                default="auto",
                allowed_values=["auto", "telea", "navier_stokes", "custom_interpolation"],
                description="OpenCV 修复算法",
            ),
        }

    def validate(self, param_name: str, value: Any, fallback: Optional[Any] = None) -> Any:
        """
        验证单个参数值

        Args:
            param_name: 参数名称
            value: 待验证的值
            fallback: 自定义回退值（可选，否则使用规则默认值）

        Returns:
            验证后的值（可能经过类型转换或回退到默认值）
        """
        rule = self._rules.get(param_name)
        if rule is None:
            # 无验证规则，直接返回原值
            return value

        default = fallback if fallback is not None else rule.default

        # 1. 类型转换
        try:
            converted = rule.param_type(value)
        except (TypeError, ValueError):
            self.logger.warning(f"[参数验证] {param_name}={value} 类型转换失败，使用默认值 {default}")
            return default

        # 2. 枚举值验证
        if rule.allowed_values is not None:
            if converted not in rule.allowed_values:
                self.logger.warning(
                    f"[参数验证] {param_name}={converted} 不在允许范围 {rule.allowed_values}，"
                    f"使用默认值 {default}"
                )
                return default
            return converted

        # 3. 范围验证（数值类型）
        if rule.min_value is not None and converted < rule.min_value:
            self.logger.warning(f"[参数验证] {param_name}={converted} < 最小值 {rule.min_value}，" f"使用最小值")
            return rule.param_type(rule.min_value)

        if rule.max_value is not None and converted > rule.max_value:
            self.logger.warning(f"[参数验证] {param_name}={converted} > 最大值 {rule.max_value}，" f"使用最大值")
            return rule.param_type(rule.max_value)

        return converted

    def validate_params(self, params: Dict[str, Any], warn_unknown: bool = False) -> Dict[str, Any]:
        """
        批量验证参数字典

        Args:
            params: 待验证的参数字典
            warn_unknown: 是否警告未知参数

        Returns:
            验证后的参数字典
        """
        validated = {}

        for key, value in params.items():
            if key in self._rules:
                validated[key] = self.validate(key, value)
            else:
                if warn_unknown:
                    self.logger.debug(f"[参数验证] 未知参数: {key}")
                validated[key] = value  # 保留未知参数

        return validated

    def get_default(self, param_name: str) -> Any:
        """获取参数的默认值"""
        rule = self._rules.get(param_name)
        return rule.default if rule else None

    def get_rule(self, param_name: str) -> Optional[ValidationRule]:
        """获取参数的验证规则"""
        return self._rules.get(param_name)

    def get_all_defaults(self) -> Dict[str, Any]:
        """获取所有参数的默认值"""
        return {name: rule.default for name, rule in self._rules.items()}

    def describe_param(self, param_name: str) -> str:
        """获取参数描述"""
        rule = self._rules.get(param_name)
        if rule is None:
            return f"未知参数: {param_name}"

        desc = f"{param_name} ({rule.param_type.__name__}): {rule.description}"
        if rule.min_value is not None:
            desc += f", 最小值: {rule.min_value}"
        if rule.max_value is not None:
            desc += f", 最大值: {rule.max_value}"
        if rule.allowed_values is not None:
            desc += f", 允许值: {rule.allowed_values}"
        desc += f", 默认值: {rule.default}"

        return desc


# 全局单例
_validator_instance: Optional[ConfigValidator] = None


def get_validator() -> ConfigValidator:
    """获取全局验证器实例"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ConfigValidator()
    return _validator_instance


# 便捷函数
def validate_param(param_name: str, value: Any, fallback: Optional[Any] = None) -> Any:
    """验证单个参数（便捷函数）"""
    return get_validator().validate(param_name, value, fallback)


def validate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """批量验证参数（便捷函数）"""
    return get_validator().validate_params(params)


__all__ = [
    "ConfigValidator",
    "ValidationRule",
    "get_validator",
    "validate_param",
    "validate_params",
]
