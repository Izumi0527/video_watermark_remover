#!/usr/bin/env python3
"""
多进程视频分块输出容器策略测试。
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace


def test_calculate_chunks_uses_output_container_suffix(monkeypatch) -> None:
    fake_cv2 = SimpleNamespace()
    fake_qtcore = types.ModuleType("PyQt6.QtCore")
    fake_qtcore.QTimer = object
    fake_pyqt6 = types.ModuleType("PyQt6")
    fake_pyqt6.QtCore = fake_qtcore
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setitem(sys.modules, "PyQt6", fake_pyqt6)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", fake_qtcore)
    monkeypatch.delitem(sys.modules, "app.core.video.modes.multiprocess", raising=False)
    from app.core.video.modes.multiprocess import _calculate_chunks

    processor = SimpleNamespace(
        logger=SimpleNamespace(info=lambda *_args, **_kwargs: None),
    )
    chunks = _calculate_chunks(
        processor,
        total_frames=120,
        num_processes=3,
        output_path="C:/tmp/final_output.avi",
    )

    assert len(chunks) == 3
    assert all(str(chunk_path).lower().endswith(".avi") for _, _, chunk_path in chunks)
