#!/usr/bin/env python3
"""
预加载 AI 参数快照回归测试。

目标：
- 预加载不应再使用空 ai_params，否则首任务会触发 VideoProcessorThread 的 refresh 判定。
- 预加载快照需要包含关键 refresh 字段，并注入配置中的 inpainting/lama 路径，保证与运行时一致。
"""

from __future__ import annotations

import configparser


class _DummyPreferences:
    def get_preference(self, section: str, key: str, default=None):
        return default


def test_build_preload_ai_params_snapshot_injects_model_paths() -> None:
    from app.ui.utils.ai_params_builder import build_preload_ai_params_snapshot

    config = configparser.ConfigParser()
    config["Models"] = {
        "lama_model_path": "models/big-lama.pt",
        "inpainting_model_path": "models/stub-unet.pth",
    }

    snapshot = build_preload_ai_params_snapshot(
        preferences=_DummyPreferences(),
        advanced_params={},
        config=config,
    )

    # refresh 关键字段应存在（避免空预加载导致首任务 refresh）
    assert snapshot.get("device") is not None
    assert snapshot.get("requested_inpainting_backend") is not None
    assert snapshot.get("use_gpu_inpainting") is not None
    assert snapshot.get("quality_level") is not None
    assert snapshot.get("min_area_pixels") is not None

    # 配置注入必须生效（与 VideoProcessorThread 的注入逻辑对齐）
    assert snapshot.get("lama_model_path") == "models/big-lama.pt"
    assert snapshot.get("inpainting_model_path") == "models/stub-unet.pth"
