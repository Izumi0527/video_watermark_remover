#!/usr/bin/env python3
"""
图片输出编码参数回归测试。
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace


class _DummySignal:
    def __init__(self) -> None:
        self.values = []

    def emit(self, value=None) -> None:
        self.values.append(value)


class _DummyAIHandler:
    def process_frame(self, image, _params):
        return image, {
            "watermark_areas_found": 1,
            "processing_time": 0.1,
            "inpainting_method": "lama",
        }


def test_process_image_passes_resolved_encoding_options_to_imwrite(monkeypatch) -> None:
    captured = {}
    image = SimpleNamespace(shape=(4, 4, 3))

    fake_cv2 = SimpleNamespace(IMWRITE_JPEG_QUALITY=1)
    fake_cv2.imread = lambda _path: image

    def _fake_imwrite(path, payload, params=None):
        captured["path"] = path
        captured["payload_shape"] = payload.shape
        captured["params"] = params
        return True

    fake_cv2.imwrite = _fake_imwrite
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.delitem(sys.modules, "app.core.video.image_processor", raising=False)
    image_processor = importlib.import_module("app.core.video.image_processor")

    processor = SimpleNamespace(
        input_path="C:/tmp/input.png",
        output_path="C:/tmp/output.jpg",
        ai_params={
            "compression_quality": 92,
            "output_format": "jpg",
        },
        ai_handler=_DummyAIHandler(),
        status=_DummySignal(),
        progress=_DummySignal(),
        preview_update=_DummySignal(),
        finished=_DummySignal(),
        error=_DummySignal(),
        logger=SimpleNamespace(
            info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None
        ),
        last_processing_info=None,
        last_effective_processing_info=None,
        last_processing_summary=None,
    )

    image_processor.process_image(processor)

    assert captured["path"] == "C:/tmp/output.jpg"
    assert captured["payload_shape"] == (4, 4, 3)
    assert captured["params"] == [1, 92]
