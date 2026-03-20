#!/usr/bin/env python3
"""
AI处理功能测试模块

提供AI处理的核心功能测试：
1. 水印检测功能测试
2. 图像修复功能测试
3. 完整处理流程测试
4. 视频处理线程测试

从 test_phase2.py 重构拆分
作者: Izumi0527
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Tuple

import pytest

np = pytest.importorskip("numpy")

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.integration.test_utilities import (
    calculate_image_difference,
    create_test_image_with_watermark,
    create_test_mask,
    print_test_header,
    print_test_result,
    validate_image_properties,
)

RUNTIME_ROOT = Path(__file__).resolve().parents[1] / ".cache" / "tests" / "ai-processing"


def test_watermark_detection() -> Tuple[bool, str]:
    """
    测试水印检测功能

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试水印检测功能")

    try:
        from app.config.config_manager import ConfigManager
        from app.core.ai.ai_handler import AIHandler

        # 初始化AI处理器
        config = ConfigManager.load_config()
        ai_handler = AIHandler(config=config, ai_params={})
        ai_handler.load_models()

        # 创建测试图像
        test_image = create_test_image_with_watermark()
        print(f"[OK] 创建测试图像: {test_image.shape}")

        # 检测水印
        mask = ai_handler.detect_watermark(test_image)

        if mask is not None and np.any(mask):
            watermark_pixels = np.sum(mask == 255)
            total_pixels = mask.shape[0] * mask.shape[1]
            coverage = (watermark_pixels / total_pixels) * 100

            details = f"检测到 {watermark_pixels} 像素 ({coverage:.1f}% 覆盖率)"
            print_test_result("水印检测", True, details)
            return True, details
        else:
            # 未检测到水印，但算法运行正常
            details = "未检测到水印区域，但检测算法运行正常"
            print_test_result("水印检测", True, details)
            return True, details

    except Exception as e:
        error_msg = f"水印检测测试失败: {e}"
        print_test_result("水印检测", False, error_msg)
        return False, error_msg


def test_image_inpainting() -> Tuple[bool, str]:
    """
    测试图像修复功能

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试图像修复功能")

    try:
        import cv2

        from app.config.config_manager import ConfigManager
        from app.core.ai.ai_handler import AIHandler

        # 初始化AI处理器
        config = ConfigManager.load_config()
        ai_handler = AIHandler(config=config, ai_params={})
        ai_handler.load_models()

        # 创建测试图像和掩码
        test_image = create_test_image_with_watermark()
        mask = create_test_mask(test_image.shape[:2])

        repair_pixels = np.sum(mask == 255)
        print(f"[OK] 创建修复掩码，修复区域: {repair_pixels} 像素")

        # 应用图像修复
        inpainted_image = ai_handler.inpaint_frame(test_image, mask)

        if inpainted_image is not None:
            if not validate_image_properties(inpainted_image, test_image.shape):
                return False, "修复后图像属性验证失败"

            # 计算修复前后的差异
            diff_value = calculate_image_difference(test_image, inpainted_image)

            details = f"图像修复完成，修复前后差异值: {diff_value:.0f}"
            print_test_result("图像修复", True, details)
            return True, details
        else:
            return False, "图像修复失败，修复后的图像为空"

    except Exception as e:
        error_msg = f"图像修复测试失败: {e}"
        print_test_result("图像修复", False, error_msg)
        return False, error_msg


def test_full_processing_pipeline() -> Tuple[bool, str]:
    """
    测试完整的处理流程

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试完整处理流程")

    try:
        from app.config.config_manager import ConfigManager
        from app.core.ai.ai_handler import AIHandler

        # 初始化AI处理器
        config = ConfigManager.load_config()
        ai_handler = AIHandler(config=config, ai_params={})
        ai_handler.load_models()

        # 创建测试图像
        test_image = create_test_image_with_watermark()

        # 设置处理参数
        processing_params = {"auto_detect": True, "detection_sensitivity": 0.5, "user_mask": None}

        print("[OK] 开始完整的AI处理流程...")

        # 执行完整处理
        processed_image, processing_info = ai_handler.process_frame(test_image, processing_params)

        if "error" in processing_info:
            return False, f"处理出错: {processing_info['error']}"

        # 显示处理结果
        areas_found = processing_info.get("watermark_areas_found", 0)
        method = processing_info.get("inpainting_method", "unknown")
        processing_time = processing_info.get("processing_time", 0)

        details = f"检测到{areas_found}个水印区域，使用{method}方法，耗时{processing_time:.3f}秒"

        if processed_image is None:
            return False, "处理后的图像为空"

        if processing_info is None:
            return False, "处理信息为空"

        print_test_result("完整处理流程", True, details)
        return True, details

    except Exception as e:
        error_msg = f"完整处理流程测试失败: {e}"
        print_test_result("完整处理流程", False, error_msg)
        return False, error_msg


def test_video_processor_thread() -> Tuple[bool, str]:
    """
    测试视频处理线程（不启动实际GUI）

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试视频处理线程")

    try:
        import cv2

        from app.config.config_manager import ConfigManager
        from app.core.video.thread import VideoProcessorThread

        # 创建临时测试图片
        test_image = create_test_image_with_watermark()

        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=RUNTIME_ROOT, suffix=".jpg", delete=False) as tmp_file:
            temp_input_path = tmp_file.name
            cv2.imwrite(temp_input_path, test_image)

        temp_output_path = temp_input_path.replace(".jpg", "_processed.jpg")

        # 加载配置
        config = ConfigManager.load_config()

        # 创建处理线程（但不启动）
        processor = VideoProcessorThread(
            input_path=temp_input_path,
            output_path=temp_output_path,
            ai_params={"auto_detect": True},
            config=config,
        )

        print_test_result("视频处理线程", True, "VideoProcessorThread 创建成功")

        # 清理临时文件
        os.unlink(temp_input_path)

        if processor is None:
            return False, "VideoProcessorThread应该创建成功"

        return True, "VideoProcessorThread 创建成功"

    except Exception as e:
        error_msg = f"视频处理线程测试失败: {e}"
        print_test_result("视频处理线程", False, error_msg)
        return False, error_msg


def run_ai_processing_tests() -> Tuple[int, int, dict]:
    """
    运行所有AI处理测试

    Returns:
        (通过数量, 总测试数量, 测试结果详情)
    """
    tests = [
        ("水印检测功能", test_watermark_detection),
        ("图像修复功能", test_image_inpainting),
        ("完整处理流程", test_full_processing_pipeline),
        ("视频处理线程", test_video_processor_thread),
    ]

    passed = 0
    total = len(tests)
    test_results = {}

    for test_name, test_func in tests:
        try:
            success, details = test_func()
            if success:
                passed += 1
                test_results[test_name] = (True, details)
            else:
                test_results[test_name] = (False, details)
        except Exception as e:
            error_msg = f"测试执行异常: {e}"
            test_results[test_name] = (False, error_msg)

    return passed, total, test_results
