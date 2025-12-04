#!/usr/bin/env python3
"""
AI模块基础测试模块

提供AI模块的基础功能测试：
1. AI模块导入测试
2. 依赖项检查测试
3. AI处理器初始化测试
4. 基础配置验证测试

从 test_phase2.py 重构拆分
作者:
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import os
import sys
from typing import Any, Tuple

import cv2
import numpy as np

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_utilities import print_test_header, print_test_result


def test_ai_handler_import() -> Tuple[bool, str]:
    """
    测试AI处理模块导入

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试AI处理模块导入")

    try:
        from app.core.ai.ai_handler import AIHandler

        if AIHandler is None:
            return False, "AIHandler应该不为空"

        print_test_result("AI模块导入", True, "AIHandler 导入成功")
        return True, "AIHandler 导入成功"

    except ImportError as e:
        error_msg = f"AIHandler 导入失败: {e}"
        print_test_result("AI模块导入", False, error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"AI模块导入异常: {e}"
        print_test_result("AI模块导入", False, error_msg)
        return False, error_msg


def test_opencv_dependencies() -> Tuple[bool, str]:
    """
    测试OpenCV依赖

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试OpenCV依赖")

    try:
        import cv2
        import numpy as np

        print(f"[OK] OpenCV 版本: {cv2.__version__}")
        print(f"[OK] NumPy 版本: {np.__version__}")

        # 测试基本OpenCV功能
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        if cv2 is None or np is None:
            return False, "OpenCV或NumPy不可用"

        print_test_result("OpenCV依赖", True, "OpenCV 图像处理功能正常")
        return True, "OpenCV 图像处理功能正常"

    except Exception as e:
        error_msg = f"OpenCV 测试失败: {e}"
        print_test_result("OpenCV依赖", False, error_msg)
        return False, error_msg


def test_ai_handler_initialization() -> Tuple[bool, str]:
    """
    测试AI处理器初始化

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试AI处理器初始化")

    try:
        from app.config.config_manager import ConfigManager
        from app.core.ai.ai_handler import AIHandler

        # 加载配置
        config = ConfigManager.load_config()

        # 初始化AI处理器
        ai_handler = AIHandler(config=config, ai_params={})
        print_test_result("AI处理器创建", True, "AIHandler 初始化成功")

        # 加载模型
        result = ai_handler.load_models()
        if result:
            print_test_result("AI模型加载", True, "轻量级AI模型加载成功")
        else:
            return False, "AI模型加载失败"

        if ai_handler is None:
            return False, "AI处理器应该初始化成功"

        return True, "AI处理器初始化和模型加载成功"

    except Exception as e:
        error_msg = f"AI处理器初始化失败: {e}"
        print_test_result("AI处理器初始化", False, error_msg)
        return False, error_msg


def test_config_manager_loading() -> Tuple[bool, str]:
    """
    测试配置管理器加载

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试配置管理器加载")

    try:
        from app.config.config_manager import ConfigManager

        # 测试配置加载
        config = ConfigManager.load_config()

        if config is None:
            return False, "配置对象不应为空"

        if not isinstance(config, dict):
            return False, "配置应该是字典类型"

        print_test_result("配置管理器", True, f"配置加载成功，包含{len(config)}个配置项")
        return True, f"配置加载成功，包含{len(config)}个配置项"

    except Exception as e:
        error_msg = f"配置管理器加载失败: {e}"
        print_test_result("配置管理器", False, error_msg)
        return False, error_msg


def test_video_processor_thread_import() -> Tuple[bool, str]:
    """
    测试视频处理线程导入

    Returns:
        (成功状态, 详细信息)
    """
    print_test_header("测试视频处理线程导入")

    try:
        from app.core.video.video_processor import VideoProcessorThread

        if VideoProcessorThread is None:
            return False, "VideoProcessorThread应该不为空"

        print_test_result("视频处理线程导入", True, "VideoProcessorThread 导入成功")
        return True, "VideoProcessorThread 导入成功"

    except ImportError as e:
        error_msg = f"VideoProcessorThread 导入失败: {e}"
        print_test_result("视频处理线程导入", False, error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"视频处理线程导入异常: {e}"
        print_test_result("视频处理线程导入", False, error_msg)
        return False, error_msg


def run_basic_ai_tests() -> Tuple[int, int, dict]:
    """
    运行所有基础AI测试

    Returns:
        (通过数量, 总测试数量, 测试结果详情)
    """
    tests = [
        ("AI模块导入", test_ai_handler_import),
        ("OpenCV依赖", test_opencv_dependencies),
        ("配置管理器", test_config_manager_loading),
        ("AI处理器初始化", test_ai_handler_initialization),
        ("视频处理线程导入", test_video_processor_thread_import),
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
