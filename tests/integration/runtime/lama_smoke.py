#!/usr/bin/env python3
"""
LaMa backend subprocess smoke。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np


def _resolve_asset_ref() -> str | None:
    raw_path = os.environ.get("VWR_LAMA_MODEL_PATH", "").strip()
    if not raw_path:
        return None
    return str(Path(raw_path).expanduser())


def main() -> int:
    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        print(f"SKIP: torch 不可用: {exc}")
        return 2

    if not torch.cuda.is_available():
        print("SKIP: CUDA 不可用")
        return 2

    asset_ref = _resolve_asset_ref()
    if not asset_ref:
        print("SKIP: 未设置 VWR_LAMA_MODEL_PATH")
        return 2

    from app.core.ai.inpainting_backends.factory import create_inpainting_backend

    backend = create_inpainting_backend(
        requested_backend="lama",
        config=None,
        torch_device=torch.device("cuda"),
        model_path=asset_ref,
    )

    if not backend.load():
        trace = backend.get_last_trace()
        reason = trace.get("load_failure_reason", "lama_load_failed")
        detail = trace.get("load_failure_detail")
        if detail:
            print(f"FAIL: LaMa backend 加载失败: {reason} | {detail}")
        else:
            print(f"FAIL: LaMa backend 加载失败: {reason}")
        return 1

    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[16:32, 16:32] = 255

    try:
        result = backend.inpaint_frame(
            frame,
            mask,
            inpaint_radius=3,
            quality_level=3,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: LaMa backend 运行失败: {exc}")
        return 1

    if result.shape != frame.shape:
        print(f"FAIL: 输出 shape 异常: {result.shape}")
        return 1

    trace = backend.get_last_trace()
    if trace.get("inpainting_backend") != "lama":
        print(f"FAIL: trace backend 异常: {trace}")
        return 1
    if not trace.get("loaded_inpainting_model_path"):
        print(f"FAIL: trace 缺少 loaded_inpainting_model_path: {trace}")
        return 1

    print("PASS: LaMa backend smoke 成功")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
