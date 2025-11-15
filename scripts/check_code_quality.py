#!/usr/bin/env python3
"""
代码质量检查脚本
检查Python文件是否符合300行以内的硬性指标

作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.0
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class FileAnalysis:
    """文件分析结果数据类"""

    path: str
    lines: int
    status: str  # 'OK', 'WARNING', 'ERROR'
    severity: str  # 'Low', 'Medium', 'High', 'Critical'


class CodeQualityChecker:
    """代码质量检查器"""

    def __init__(self, root_path: str = ".", line_limit: int = 300):
        self.root_path = Path(root_path)
        self.line_limit = line_limit
        self.results: List[FileAnalysis] = []

    def scan_python_files(self) -> List[Path]:
        """扫描所有Python文件"""
        python_files = []

        # 排除的目录
        exclude_dirs = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "node_modules",
            "dist",
            "build",
        }

        for py_file in self.root_path.rglob("*.py"):
            # 检查是否在排除目录中
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue
            python_files.append(py_file)

        return sorted(python_files)

    def count_lines(self, file_path: Path) -> int:
        """统计文件行数"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception as e:
            print(f"警告: 无法读取文件 {file_path}: {e}")
            return 0

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """分析单个文件"""
        lines = self.count_lines(file_path)
        relative_path = str(file_path.relative_to(self.root_path))

        if lines <= self.line_limit:
            status = "OK"
            severity = "Low"
        elif lines <= self.line_limit + 50:  # 300-350行
            status = "WARNING"
            severity = "Medium"
        elif lines <= self.line_limit + 100:  # 351-400行
            status = "WARNING"
            severity = "High"
        else:  # 401+行
            status = "ERROR"
            severity = "Critical"

        return FileAnalysis(path=relative_path, lines=lines, status=status, severity=severity)

    def run_analysis(self) -> Dict[str, int]:
        """运行完整分析"""
        python_files = self.scan_python_files()
        print(f"[INFO] 扫描到 {len(python_files)} 个Python文件")

        self.results = []
        for file_path in python_files:
            analysis = self.analyze_file(file_path)
            self.results.append(analysis)

        # 统计结果
        stats = {
            "total": len(self.results),
            "ok": sum(1 for r in self.results if r.status == "OK"),
            "warning": sum(1 for r in self.results if r.status == "WARNING"),
            "error": sum(1 for r in self.results if r.status == "ERROR"),
        }

        return stats

    def generate_report(self, stats: Dict[str, int], verbose: bool = False):
        """生成分析报告"""
        print("\n" + "=" * 70)
        print("[REPORT] 代码质量分析报告")
        print("=" * 70)

        # 总体统计
        print(f"\n[STATS] 总体统计:")
        print(f"   总文件数: {stats['total']}")
        print(f"   [OK] 合规文件: {stats['ok']} ({stats['ok']/stats['total']*100:.1f}%)")
        print(f"   [WARN] 警告文件: {stats['warning']} ({stats['warning']/stats['total']*100:.1f}%)")
        print(f"   [ERROR] 超标文件: {stats['error']} ({stats['error']/stats['total']*100:.1f}%)")

        # 问题文件详情
        problem_files = [r for r in self.results if r.status != "OK"]
        if problem_files:
            print(f"\n[ISSUES] 需要关注的文件 ({len(problem_files)} 个):")
            print("-" * 70)

            # 按严重程度排序
            problem_files.sort(key=lambda x: (x.lines, x.severity), reverse=True)

            for file_analysis in problem_files:
                icon = "[ERROR]" if file_analysis.status == "ERROR" else "[WARN]"
                over_limit = file_analysis.lines - self.line_limit
                over_percent = over_limit / self.line_limit * 100

                print(f"{icon} {file_analysis.path}")
                print(f"     行数: {file_analysis.lines} | 超标: +{over_limit}行 ({over_percent:.1f}%)")
                print(f"     严重程度: {file_analysis.severity}")
                print()

        # 详细列表（verbose模式）
        if verbose and stats["ok"] > 0:
            print(f"\n[OK] 合规文件详情 ({stats['ok']} 个):")
            print("-" * 70)
            ok_files = [r for r in self.results if r.status == "OK"]
            for file_analysis in sorted(ok_files, key=lambda x: x.lines, reverse=True):
                print(f"   {file_analysis.path} ({file_analysis.lines} 行)")

        # 建议
        if problem_files:
            print("\n[SUGGESTIONS] 优化建议:")
            critical_files = [r for r in problem_files if r.severity == "Critical"]
            if critical_files:
                print(f"   [CRITICAL] 立即处理 {len(critical_files)} 个严重超标文件")

            high_files = [r for r in problem_files if r.severity == "High"]
            if high_files:
                print(f"   [HIGH] 本周处理 {len(high_files)} 个高风险文件")

            medium_files = [r for r in problem_files if r.severity == "Medium"]
            if medium_files:
                print(f"   [MEDIUM] 计划处理 {len(medium_files)} 个中等风险文件")

        print("\n" + "=" * 70)

        # 返回退出码
        return 0 if stats["error"] == 0 else 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="检查Python文件行数是否符合质量标准")
    parser.add_argument("--path", default=".", help="扫描路径 (默认: 当前目录)")
    parser.add_argument("--limit", type=int, default=300, help="行数限制 (默认: 300)")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 运行检查
    checker = CodeQualityChecker(args.path, args.limit)
    stats = checker.run_analysis()
    exit_code = checker.generate_report(stats, args.verbose)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
