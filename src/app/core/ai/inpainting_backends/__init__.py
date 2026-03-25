"""统一修复后端适配层。"""

from .base import BaseInpaintingBackend
from .factory import create_inpainting_backend
from .lama_backend import LaMaInpaintingBackend
from .legacy_unet_backend import LegacyUNetInpaintingBackend
from .opencv_backend import OpenCVInpaintingBackend

__all__ = [
    "BaseInpaintingBackend",
    "LaMaInpaintingBackend",
    "OpenCVInpaintingBackend",
    "LegacyUNetInpaintingBackend",
    "create_inpainting_backend",
]
