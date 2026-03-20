#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三阶段测试工具模块
包含测试报告生成和通用测试工具函数

作者: Izumi0527
创建时间: 2025-09-06
版本: v1.0
"""

import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
report_root = project_root / ".cache" / "tests" / "legacy-phase3"


def generate_test_report(results):
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("[报告] 第三阶段功能测试报告")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    failed_tests = total_tests - passed_tests

    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests} [OK]")
    print(f"失败测试: {failed_tests} [ERROR]")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")

    print("\n详细结果:")
    for test_name, result in results.items():
        status = "[OK] 通过" if result else "[ERROR] 失败"
        print(f"  {test_name}: {status}")

    # 生成JSON报告
    report_data = {
        "test_date": "2025-09-06",
        "phase": "Phase 3 - 产品化完善",
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": passed_tests / total_tests * 100,
        "results": results,
        "features_implemented": [
            "手动水印区域选择",
            "处理效果对比预览",
            "FFmpeg音频处理",
            "批量处理队列",
            "现代化界面设计",
            "用户偏好设置",
            "高级处理参数控制",
        ],
    }

    try:
        report_root.mkdir(parents=True, exist_ok=True)
        report_path = report_root / "phase3_test_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"\n[INFO] 测试报告已保存到: {report_path}")
    except Exception as e:
        print(f"[ERROR] 测试报告保存失败: {e}")


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

    for test_name, result in test_results.items():
        status = "[OK]" if result else "[ERROR]"
        print(f"  {status} {test_name}")


def run_test_suite(test_functions: dict, suite_name: str = "测试套件") -> tuple:
    """
    运行测试套件

    Args:
        test_functions: 测试函数字典 {name: function}
        suite_name: 套件名称

    Returns:
        tuple: (passed_count, total_count, results_dict)
    """
    print(f"\n[运行] {suite_name}...")

    results = {}
    for test_name, test_func in test_functions.items():
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"[ERROR] 测试 '{test_name}' 发生异常: {e}")
            results[test_name] = False

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    return passed, total, results


def validate_test_results(results: dict) -> bool:
    """
    验证测试结果的完整性

    Args:
        results: 测试结果字典

    Returns:
        bool: 是否所有测试都有结果
    """
    return all(isinstance(result, bool) for result in results.values())


if __name__ == "__main__":
    """测试工具模块独立运行"""
    print("第三阶段测试工具模块")
    print("提供测试报告生成和工具函数")

    # 示例用法
    sample_results = {"示例测试1": True, "示例测试2": True, "示例测试3": False}

    print_test_summary(2, 3, sample_results, "示例")
    print(f"结果验证: {validate_test_results(sample_results)}")
