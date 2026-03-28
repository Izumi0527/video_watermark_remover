#!/usr/bin/env python3
"""
资源压力识别回归测试。
"""

from __future__ import annotations


def test_resource_pressure_matches_memory_error() -> None:
    from app.core.video.utils.resource_pressure import is_resource_pressure_error

    assert is_resource_pressure_error(MemoryError()) is True


def test_resource_pressure_matches_known_gpu_and_allocation_messages() -> None:
    from app.core.video.utils.resource_pressure import is_resource_pressure_error

    assert (
        is_resource_pressure_error(
            RuntimeError("Unable to allocate 10.5 MiB for an array with shape (1280, 720, 3)")
        )
        is True
    )
    assert is_resource_pressure_error(RuntimeError("ptxas fatal   : Memory allocation failure"))
    assert is_resource_pressure_error(
        RuntimeError("OpenCV error: (-4:Insufficient memory) Failed to allocate 2764800 bytes")
    )


def test_resource_pressure_does_not_match_generic_runtime_error() -> None:
    from app.core.video.utils.resource_pressure import is_resource_pressure_error

    assert is_resource_pressure_error(RuntimeError("generic processing failure")) is False
