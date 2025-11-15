#!/usr/bin/env python3
# -*- coding: utf-8 BOM-*-
"""
第二阶段测试脚本 - AI功能集成测试

用于测试第二阶段的核心AI功能：
1. OpenCV水印检测算法
2. 图像修复算法
3. AI处理模块集成
4. 真实的图片处理流程

重构版本：将测试拆分为专门模块，提高代码可维护性
- test_utilities.py: 测试工具函数
- ai_module_tests.py: AI模块基础测试
- ai_processing_tests.py: AI处理功能测试

运行方式:
python test_phase2.py

作者: Claude Code Assistant
创建时间: 2025-01-31
版本: v2.0 (重构版)
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_module_tests import run_basic_ai_tests
from ai_processing_tests import run_ai_processing_tests


def print_test_summary(passed: int, total: int, test_results: dict, phase_name: str) -> None:
    """
    打印测试摘要
    
    Args:
        passed: 通过的测试数量
        total: 总测试数量  
        test_results: 测试结果详情
        phase_name: 阶段名称
    """
    print(f"\n{phase_name}测试结果: {passed}/{total} 通过")
    
    for test_name, (success, details) in test_results.items():
        status = "[OK]" if success else "[ERROR]"
        print(f"  {status} {test_name}: {details}")


def main():
    """主测试函数"""
    print("智能视频水印去除工具 - 第二阶段AI功能测试")
    print("=" * 60)
    
    total_passed = 0
    total_tests = 0
    all_results = {}
    
    # 运行基础AI模块测试
    print("\n[阶段1] 运行AI模块基础测试...")
    basic_passed, basic_total, basic_results = run_basic_ai_tests()
    total_passed += basic_passed
    total_tests += basic_total
    all_results.update(basic_results)
    
    print_test_summary(basic_passed, basic_total, basic_results, "AI模块基础")
    
    # 运行AI处理功能测试
    print("\n[阶段2] 运行AI处理功能测试...")
    processing_passed, processing_total, processing_results = run_ai_processing_tests()
    total_passed += processing_passed
    total_tests += processing_total
    all_results.update(processing_results)
    
    print_test_summary(processing_passed, processing_total, processing_results, "AI处理功能")
    
    # 总结果
    print("\n" + "=" * 60)
    print(f"[统计] 第二阶段测试结果: {total_passed}/{total_tests} 通过")
    print(f"[统计] 测试通过率: {(total_passed/total_tests)*100:.1f}%")
    
    # 显示失败的测试
    failed_tests = [name for name, (success, _) in all_results.items() if not success]
    if failed_tests:
        print(f"[警告] 失败的测试 ({len(failed_tests)}个):")
        for test_name in failed_tests:
            print(f"  - {test_name}")
    
    if total_passed == total_tests:
        print("[成功] 所有AI功能测试通过！第二阶段开发成功。")
        print("\n[提示] 现在可以运行: python main.py")
        print("   体验真实的AI水印去除功能！")
        return 0
    else:
        print("[警告] 部分AI功能测试失败，请检查实现。")
        print("\n[提示] 建议检查:")
        print("   - OpenCV版本兼容性")
        print("   - PyTorch安装状态")
        print("   - 模块导入路径")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)