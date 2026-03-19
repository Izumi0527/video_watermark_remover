#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三阶段测试运行器 - 重构版

整合所有Phase 3测试模块，提供统一的测试入口。
使用模块化架构提高代码可维护性。

模块组成:
- phase3_core_tests: 核心组件测试
- phase3_feature_tests: 功能特性测试
- phase3_test_utilities: 测试工具和报告

运行方式:
python tests/phase3_test_runner.py

作者: Izumi0527
创建时间: 2025-09-06
版本: v2.0 (重构版)
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入测试模块
from phase3_core_tests import test_component_imports, test_file_structure, test_integration
from phase3_feature_tests import (
    test_advanced_parameters,
    test_ffmpeg_audio_processor,
    test_modern_style_manager,
    test_user_preferences,
)
from phase3_test_utilities import generate_test_report, print_test_summary, run_test_suite


def main():
    """主测试函数"""
    print("智能视频水印去除工具 - 第三阶段功能测试（重构版）")
    print("=" * 60)
    print(f"项目根目录: {project_root}")

    # 定义所有测试函数
    all_test_functions = {
        "组件导入": test_component_imports,
        "文件结构": test_file_structure,
        "用户偏好设置": test_user_preferences,
        "现代化样式管理器": test_modern_style_manager,
        "FFmpeg音频处理器": test_ffmpeg_audio_processor,
        "高级参数功能": test_advanced_parameters,
        "组件集成": test_integration,
    }

    # 运行核心测试套件
    core_tests = {
        "组件导入": test_component_imports,
        "文件结构": test_file_structure,
        "组件集成": test_integration,
    }
    core_passed, core_total, core_results = run_test_suite(core_tests, "核心组件测试套件")
    print_test_summary(core_passed, core_total, core_results, "核心组件")

    # 运行功能测试套件
    feature_tests = {
        "用户偏好设置": test_user_preferences,
        "现代化样式管理器": test_modern_style_manager,
        "FFmpeg音频处理器": test_ffmpeg_audio_processor,
        "高级参数功能": test_advanced_parameters,
    }
    feature_passed, feature_total, feature_results = run_test_suite(feature_tests, "功能特性测试套件")
    print_test_summary(feature_passed, feature_total, feature_results, "功能特性")

    # 合并所有结果
    all_results = {**core_results, **feature_results}
    total_passed = core_passed + feature_passed
    total_tests = core_total + feature_total

    # 生成综合报告
    print("\n" + "=" * 60)
    print(f"[统计] 第三阶段测试总结果: {total_passed}/{total_tests} 通过")
    print(f"[统计] 测试通过率: {(total_passed / total_tests) * 100:.1f}%")

    # 显示失败的测试
    failed_tests = [name for name, result in all_results.items() if not result]
    if failed_tests:
        print(f"[警告] 失败的测试 ({len(failed_tests)}个):")
        for test_name in failed_tests:
            print(f"  - {test_name}")

    # 生成详细报告
    generate_test_report(all_results)

    # 返回结果
    if total_passed == total_tests:
        print("\n[SUCCESS] 所有测试通过！第三阶段功能实现完成。")
        print("\n[提示] 现在可以运行: python main.py")
        print("   体验完整的智能水印去除功能！")
        return 0
    else:
        print("\n[WARNING] 部分测试失败，请检查相关功能。")
        print("\n[提示] 建议检查:")
        print("   - 依赖库安装状态")
        print("   - PyQt6环境配置")
        print("   - 模块导入路径")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
