#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三阶段功能测试脚本 - 重构版

这是重构后的 pytest 桥接入口，实际测试逻辑已移至模块化结构：
- core_checks.py: 核心组件测试
- feature_checks.py: 功能特性测试
- support.py: 测试工具
- runner.py: 主运行器

当前目录仅保留这一个可收集入口，用于桥接 `legacy_phase3.runner`。

测试以下Phase 3功能：
1. 手动水印区域选择
2. 处理效果对比预览
3. FFmpeg音频处理
4. 批量处理队列
5. 现代化界面设计
6. 用户偏好设置
7. 高级处理参数控制

作者: Izumi0527
创建时间: 2025-01-31 (原版)
重构时间: 2025-09-06 (重构版)
版本: v2.0 (重构版)
"""

import sys
from pathlib import Path

# 添加 src 目录到路径
project_root = Path(__file__).resolve().parents[3]
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

# 导入测试运行器
try:
    from tests.integration.legacy_phase3.runner import main as run_phase3_tests

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
    print("  - tests/integration/legacy_phase3/core_checks.py")
    print("  - tests/integration/legacy_phase3/feature_checks.py")
    print("  - tests/integration/legacy_phase3/support.py")
    print("  - tests/integration/legacy_phase3/runner.py")

    def main():
        """错误处理版本"""
        return 1


def test_phase3_runner_entrypoint():
    """验证 phase3 历史桥接入口仍可调用。"""
    result = main()
    assert isinstance(result, int)
    assert result in {0, 1}


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
