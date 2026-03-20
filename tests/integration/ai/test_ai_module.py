#!/usr/bin/env python3
"""
AI模块基础测试模块

提供AI模块的基础功能测试：
1. AI模块导入测试
2. 依赖项检查测试
3. AI处理器初始化测试
4. 基础配置验证测试

从 test_phase2.py 重构拆分
作者: Izumi0527
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import os
from configparser import ConfigParser
from typing import Callable, Tuple

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from tests.integration.test_utilities import print_test_header, print_test_result

ENABLE_HEAVY_AI_TESTS = os.getenv("VWR_RUN_HEAVY_AI_TESTS") == "1"


def _fail_test(test_name: str, error_msg: str) -> None:
    print_test_result(test_name, False, error_msg)
    raise AssertionError(error_msg)


def _require_heavy_ai_runtime() -> None:
    if not ENABLE_HEAVY_AI_TESTS:
        pytest.skip("需要完整 AI 运行环境；如需执行请设置 VWR_RUN_HEAVY_AI_TESTS=1")


def test_ai_handler_import() -> None:
    """测试AI处理模块导入。"""
    test_name = "AI模块导入"
    print_test_header("测试AI处理模块导入")

    try:
        _require_heavy_ai_runtime()
        from app.core.ai.ai_handler import AIHandler

        assert AIHandler is not None, "AIHandler应该不为空"
        print_test_result(test_name, True, "AIHandler 导入成功")
    except Exception as exc:
        _fail_test(test_name, f"AI模块导入异常: {exc}")


def test_opencv_dependencies() -> None:
    """测试OpenCV依赖。"""
    test_name = "OpenCV依赖"
    print_test_header("测试OpenCV依赖")

    try:
        import cv2 as cv2_module
        import numpy as np_module

        print(f"[OK] OpenCV 版本: {cv2_module.__version__}")
        print(f"[OK] NumPy 版本: {np_module.__version__}")

        test_image = np_module.zeros((100, 100, 3), dtype=np_module.uint8)
        gray = cv2_module.cvtColor(test_image, cv2_module.COLOR_BGR2GRAY)
        cv2_module.Canny(gray, 50, 150)

        assert cv2_module is not None and np_module is not None, "OpenCV或NumPy不可用"
        print_test_result(test_name, True, "OpenCV 图像处理功能正常")
    except Exception as exc:
        _fail_test(test_name, f"OpenCV 测试失败: {exc}")


def test_ai_handler_initialization() -> None:
    """测试AI处理器初始化。"""
    test_name = "AI处理器初始化"
    print_test_header("测试AI处理器初始化")

    try:
        _require_heavy_ai_runtime()
        from app.config.config_manager import ConfigManager
        from app.core.ai.ai_handler import AIHandler

        config = ConfigManager.load_config()
        ai_handler = AIHandler(config=config, ai_params={})
        print_test_result("AI处理器创建", True, "AIHandler 初始化成功")

        result = ai_handler.load_models()
        assert result, "AI模型加载失败"
        assert ai_handler is not None, "AI处理器应该初始化成功"

        print_test_result("AI模型加载", True, "轻量级AI模型加载成功")
    except Exception as exc:
        _fail_test(test_name, f"AI处理器初始化失败: {exc}")


def test_config_manager_loading() -> None:
    """测试配置管理器加载。"""
    test_name = "配置管理器"
    print_test_header("测试配置管理器加载")

    try:
        from app.config.config_manager import ConfigManager

        config = ConfigManager.load_config()
        assert config is not None, "配置对象不应为空"
        assert isinstance(config, ConfigParser), "配置应该是 ConfigParser 类型"
        assert config.has_section("Paths"), "配置缺少 Paths section"
        assert config.has_section("Processing"), "配置缺少 Processing section"
        print_test_result(test_name, True, f"配置加载成功，包含{len(config.sections())}个配置分区")
    except Exception as exc:
        _fail_test(test_name, f"配置管理器加载失败: {exc}")


def test_video_processor_thread_import() -> None:
    """测试视频处理线程导入。"""
    test_name = "视频处理线程导入"
    print_test_header("测试视频处理线程导入")

    try:
        from app.core.video.thread import VideoProcessorThread

        assert VideoProcessorThread is not None, "VideoProcessorThread应该不为空"
        print_test_result(test_name, True, "VideoProcessorThread 导入成功")
    except ImportError as exc:
        _fail_test(test_name, f"VideoProcessorThread 导入失败: {exc}")
    except Exception as exc:
        _fail_test(test_name, f"视频处理线程导入异常: {exc}")


def run_basic_ai_tests() -> Tuple[int, int, dict]:
    """运行所有基础AI测试。"""
    tests: Tuple[Tuple[str, Callable[[], None]], ...] = (
        ("AI模块导入", test_ai_handler_import),
        ("OpenCV依赖", test_opencv_dependencies),
        ("配置管理器", test_config_manager_loading),
        ("AI处理器初始化", test_ai_handler_initialization),
        ("视频处理线程导入", test_video_processor_thread_import),
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
