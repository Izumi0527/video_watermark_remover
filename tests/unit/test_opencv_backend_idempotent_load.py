#!/usr/bin/env python3
"""
OpenCVInpaintingBackend.load() 幂等性回归测试。

目标：
- 同一个 backend 实例在同一任务生命周期内，多次调用 load() 不应重复触发底层 load_model()。
  否则命中水印的逐帧修复路径会被大量无意义 load 放大，形成可见性能损耗与日志刷屏。
"""

from __future__ import annotations


def test_opencv_backend_load_calls_image_inpainter_only_once() -> None:
    from app.core.ai.inpainting_backends.opencv_backend import OpenCVInpaintingBackend

    calls = {"count": 0}

    class _DummyImageInpainter:
        def load_model(self) -> bool:
            calls["count"] += 1
            return True

        def inpaint_frame(self, frame, mask, method=None, radius=3, quality_level=3):
            return frame

    backend = OpenCVInpaintingBackend(config=None, image_inpainter=_DummyImageInpainter())

    assert backend.load() is True
    assert backend.load() is True

    assert calls["count"] == 1
