#!/usr/bin/env python3
"""
YOLOWatermarkDetector 模型解析与降级测试

目标：
- 当用户选择新模型 `yolo11x-watermark-corzent` 但无法使用时，
  能自动降级到默认模型 `yolo11x-watermark`，避免初始化直接失败。
"""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")


def _build_minimal_config(model_dir: Path, model_type: str, auto_download: bool) -> ConfigParser:
    config = ConfigParser()
    config["Paths"] = {"default_model_dir": str(model_dir)}
    config["YOLO"] = {
        "model_type": model_type,
        "auto_download_model": "yes" if auto_download else "no",
        "conf_threshold": "0.25",
        "iou_threshold": "0.45",
        "batch_size": "8",
        "custom_model_path": "",
    }
    return config


def test_init_falls_back_to_default_model_when_corzent_unavailable(tmp_path: Path):
    """
    当 corzent 模型不可用且禁用自动下载时，应自动降级到默认模型。
    """
    from app.core.ai.yolo_detector import YOLOWatermarkDetector  # noqa: WPS433

    # 仅准备默认模型文件（无需真实权重，仅需文件存在即可通过路径解析）
    fallback_model = tmp_path / "yolo11x-watermark.pt"
    fallback_model.write_bytes(b"stub")

    config = _build_minimal_config(
        model_dir=tmp_path,
        model_type="yolo11x-watermark-corzent",
        auto_download=False,
    )

    detector = YOLOWatermarkDetector(config=config, device="cpu")

    assert detector.model_type == "yolo11x-watermark"
    assert Path(detector.model_path) == fallback_model
