#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三阶段功能测试脚本 - 重构版

这是重构后的简化版本，实际测试逻辑已移至模块化结构：
- phase3_core_tests.py: 核心组件测试
- phase3_feature_tests.py: 功能特性测试
- phase3_test_utilities.py: 测试工具
- phase3_test_runner.py: 主运行器

为保持向后兼容性，此文件作为入口点重定向到新的测试运行器。

测试以下Phase 3功能：
1. 手动水印区域选择
2. 处理效果对比预览
3. FFmpeg音频处理
4. 批量处理队列
5. 现代化界面设计
6. 用户偏好设置
7. 高级处理参数控制

作者: Claude Code Assistant
创建时间: 2025-01-31 (原版)
重构时间: 2025-09-06 (重构版)
版本: v2.0 (重构版)
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入新的测试运行器
try:
    from tests.phase3_test_runner import main as run_phase3_tests

    def main():
        """主测试函数 - 重定向到新的模块化测试运行器"""
        print("第三阶段功能测试 - 重构版")
        print("使用模块化架构提高代码可维护性")
        print("-" * 50)

        # 运行新的测试运行器
        return run_phase3_tests()

except ImportError as e:
    print(f"[ERROR] 无法导入测试运行器: {e}")
    print("请确保测试模块文件存在:")
    print("  - tests/phase3_core_tests.py")
    print("  - tests/phase3_feature_tests.py")
    print("  - tests/phase3_test_utilities.py")
    print("  - tests/phase3_test_runner.py")

    def main():
        """错误处理版本"""
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
