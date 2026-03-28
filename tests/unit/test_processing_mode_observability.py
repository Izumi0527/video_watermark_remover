#!/usr/bin/env python3
"""
运行模式可观测性文案测试。
"""

from __future__ import annotations


def test_build_processing_mode_runtime_summary_for_guarded_mode() -> None:
    from app.config.advanced_params import build_processing_mode_runtime_summary

    summary = build_processing_mode_runtime_summary(
        requested_mode="multiprocess",
        resolved_mode="single_process",
    )

    assert summary == "运行模式：请求多进程分块，实际单进程"


def test_mode_restriction_reason_to_label_is_user_friendly() -> None:
    from app.config.advanced_params import mode_restriction_reason_to_label

    label = mode_restriction_reason_to_label("gpu_deep_backend_serial_only")

    assert label == "GPU 深度修复仅支持串行，已自动切换为单进程"
