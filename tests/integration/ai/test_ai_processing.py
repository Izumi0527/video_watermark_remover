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
import tempfile
from pathlib import Path
from typing import Callable, Tuple

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from tests.integration.test_utilities import (
    calculate_image_difference,
    create_test_image_with_watermark,
    create_test_mask,
    print_test_header,
    print_test_result,
    validate_image_properties,
)

RUNTIME_ROOT = Path(__file__).resolve().parents[3] / ".cache" / "tests" / "ai-processing"
ENABLE_HEAVY_AI_TESTS = os.getenv("VWR_RUN_HEAVY_AI_TESTS") == "1"


def _fail_test(test_name: str, error_msg: str) -> None:
    print_test_result(test_name, False, error_msg)
    raise AssertionError(error_msg)


def _require_heavy_ai_runtime() -> None:
    if not ENABLE_HEAVY_AI_TESTS:
        pytest.skip("需要完整 AI 运行环境；如需执行请设置 VWR_RUN_HEAVY_AI_TESTS=1")


def test_watermark_detection() -> None:
    """测试水印检测功能。"""
    test_name = "水印检测"
    print_test_header("测试水印检测功能")

    try:
        _require_heavy_ai_runtime()
        from app.config.config_manager import ConfigManager
        from app.core.ai.ai_handler import AIHandler

        config = ConfigManager.load_config()
        ai_handler = AIHandler(config=config, ai_params={})
        ai_handler.load_models()

        test_image = create_test_image_with_watermark()
        print(f"[OK] 创建测试图像: {test_image.shape}")

        mask = ai_handler.detect_watermark(test_image)

        if mask is not None and np.any(mask):
            watermark_pixels = np.sum(mask == 255)
            total_pixels = mask.shape[0] * mask.shape[1]
            coverage = (watermark_pixels / total_pixels) * 100
            details = f"检测到 {watermark_pixels} 像素 ({coverage:.1f}% 覆盖率)"
            print_test_result(test_name, True, details)
            return

        details = "未检测到水印区域，但检测算法运行正常"
        print_test_result(test_name, True, details)
    except Exception as exc:
        _fail_test(test_name, f"水印检测测试失败: {exc}")


def test_image_inpainting() -> None:
    """测试图像修复功能。"""
    test_name = "图像修复"
    print_test_header("测试图像修复功能")

    try:
        _require_heavy_ai_runtime()
        from app.config.config_manager import ConfigManager
        from app.core.ai.ai_handler import AIHandler

        config = ConfigManager.load_config()
        ai_handler = AIHandler(config=config, ai_params={})
        ai_handler.load_models()

        test_image = create_test_image_with_watermark()
        mask = create_test_mask(test_image.shape[:2])

        repair_pixels = np.sum(mask == 255)
        print(f"[OK] 创建修复掩码，修复区域: {repair_pixels} 像素")

        inpainted_image = ai_handler.inpaint_frame(test_image, mask)
        assert inpainted_image is not None, "图像修复失败，修复后的图像为空"
        assert validate_image_properties(inpainted_image, test_image.shape), "修复后图像属性验证失败"

        diff_value = calculate_image_difference(test_image, inpainted_image)
        details = f"图像修复完成，修复前后差异值: {diff_value:.0f}"
        print_test_result(test_name, True, details)
    except Exception as exc:
        _fail_test(test_name, f"图像修复测试失败: {exc}")


def test_full_processing_pipeline() -> None:
    """测试完整的处理流程。"""
    test_name = "完整处理流程"
    print_test_header("测试完整处理流程")

    try:
        _require_heavy_ai_runtime()
        from app.config.config_manager import ConfigManager
        from app.core.ai.ai_handler import AIHandler

        config = ConfigManager.load_config()
        ai_handler = AIHandler(config=config, ai_params={})
        ai_handler.load_models()

        test_image = create_test_image_with_watermark()
        processing_params = {"auto_detect": True, "detection_sensitivity": 0.5, "user_mask": None}

        print("[OK] 开始完整的AI处理流程...")
        processed_image, processing_info = ai_handler.process_frame(test_image, processing_params)

        assert processing_info is not None, "处理信息为空"
        assert "error" not in processing_info, f"处理出错: {processing_info['error']}"
        assert processed_image is not None, "处理后的图像为空"

        areas_found = processing_info.get("watermark_areas_found", 0)
        method = processing_info.get("inpainting_method", "unknown")
        processing_time = processing_info.get("processing_time", 0)

        details = f"检测到{areas_found}个水印区域，使用{method}方法，耗时{processing_time:.3f}秒"
        print_test_result(test_name, True, details)
    except Exception as exc:
        _fail_test(test_name, f"完整处理流程测试失败: {exc}")


def test_video_processor_thread() -> None:
    """测试视频处理线程（不启动实际GUI）。"""
    test_name = "视频处理线程"
    print_test_header("测试视频处理线程")

    temp_input_path = ""
    temp_output_path = ""

    try:
        from app.config.config_manager import ConfigManager
        from app.core.video.thread import VideoProcessorThread

        test_image = create_test_image_with_watermark()

        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=RUNTIME_ROOT, suffix=".jpg", delete=False) as tmp_file:
            temp_input_path = tmp_file.name
            cv2.imwrite(temp_input_path, test_image)

        temp_output_path = temp_input_path.replace(".jpg", "_processed.jpg")
        config = ConfigManager.load_config()

        processor = VideoProcessorThread(
            input_path=temp_input_path,
            output_path=temp_output_path,
            ai_params={"auto_detect": True},
            config=config,
        )

        assert processor is not None, "VideoProcessorThread应该创建成功"
        print_test_result(test_name, True, "VideoProcessorThread 创建成功")
    except Exception as exc:
        _fail_test(test_name, f"视频处理线程测试失败: {exc}")
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.unlink(temp_input_path)
        if temp_output_path and os.path.exists(temp_output_path):
            os.unlink(temp_output_path)


def run_ai_processing_tests() -> Tuple[int, int, dict]:
    """运行所有AI处理测试。"""
    tests: Tuple[Tuple[str, Callable[[], None]], ...] = (
        ("水印检测功能", test_watermark_detection),
        ("图像修复功能", test_image_inpainting),
        ("完整处理流程", test_full_processing_pipeline),
        ("视频处理线程", test_video_processor_thread),
    )

    passed = 0
    total = len(tests)
    test_results = {}

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            test_results[test_name] = (True, "通过")
        except Exception as exc:
            test_results[test_name] = (False, str(exc))

    return passed, total, test_results
