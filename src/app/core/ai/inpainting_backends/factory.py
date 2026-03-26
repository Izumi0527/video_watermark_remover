"""统一修复后端工厂。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .base import BaseInpaintingBackend

if TYPE_CHECKING:
    from ..dl_inpainter import DeepLearningInpainter
    from ..image_inpainter import ImageInpainter


def create_inpainting_backend(
    requested_backend: str,
    *,
    config=None,
    torch_device=None,
    image_inpainter: Optional["ImageInpainter"] = None,
    dl_inpainter: Optional["DeepLearningInpainter"] = None,
    model_path: Optional[str] = None,
) -> BaseInpaintingBackend:
    """根据统一后端枚举创建适配器。"""
    normalized = str(requested_backend or "").strip().lower()
    if normalized == "lama":
        from .lama_backend import LaMaInpaintingBackend

        return LaMaInpaintingBackend(
            config=config,
            torch_device=torch_device,
            asset_ref=model_path,
        )

    if normalized == "legacy_unet":
        from .legacy_unet_backend import LegacyUNetInpaintingBackend

        return LegacyUNetInpaintingBackend(
            config=config,
            torch_device=torch_device,
            model_path=model_path,
            dl_inpainter=dl_inpainter,
        )

    from .opencv_backend import OpenCVInpaintingBackend

    return OpenCVInpaintingBackend(
        config=config,
        image_inpainter=image_inpainter,
    )
