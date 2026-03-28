#!/usr/bin/env python3
"""
LaMa TorchScript 运行时。

当前实现优先支持两类资源：
1. 直接指向 TorchScript 模型文件（推荐：big-lama.pt）
2. 指向包含 TorchScript 模型文件的目录

说明：
- 官方 LaMa 训练导出目录（config.yaml + models/*.ckpt）当前只做识别与诊断，
  不在本轮直接加载，以避免把整条训练依赖链引入主工程。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
import torch

TORCHSCRIPT_SUFFIXES = {".pt", ".jit", ".ts"}
TORCHSCRIPT_CANDIDATE_NAMES = (
    "big-lama.pt",
    "lama.pt",
    "model.pt",
)


class LaMaRuntimeError(RuntimeError):
    """LaMa 运行时初始化/执行错误。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class LaMaTorchScriptRunner:
    """TorchScript LaMa 推理执行器。"""

    model: Any
    device: torch.device
    asset_ref: str
    model_path: str

    def __call__(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        **_: Any,
    ) -> np.ndarray:
        image_tensor, mask_tensor, original_height, original_width = _prepare_inputs(
            frame,
            mask,
            self.device,
        )

        with torch.inference_mode():
            output = self.model(image_tensor, mask_tensor)

        return _convert_output_to_bgr_image(output, original_height, original_width)

    def run_batch(
        self,
        frames: list[np.ndarray],
        masks: list[np.ndarray],
        **_: Any,
    ) -> list[np.ndarray]:
        """执行批量 LaMa 推理，降低逐帧调用与张量搬运开销。"""
        image_tensor, mask_tensor, original_sizes = _prepare_inputs_batch(
            frames,
            masks,
            self.device,
        )

        with torch.inference_mode():
            output = self.model(image_tensor, mask_tensor)

        return _convert_batch_output_to_bgr_images(output, original_sizes)


def build_lama_runner(
    *,
    config=None,
    torch_device=None,
    asset_ref: str | None = None,
):
    """根据资源引用创建 LaMa runner。"""
    del config

    if not asset_ref:
        raise LaMaRuntimeError(
            "missing_lama_model_path",
            "未提供 LaMa 模型路径，请设置 lama_model_path 或 VWR_LAMA_MODEL_PATH。",
        )

    device = _normalize_torch_device(torch_device)
    model_path = _resolve_torchscript_model_path(asset_ref)

    try:
        model = torch.jit.load(str(model_path), map_location=device)
        model.eval()
        model.to(device)
    except Exception as exc:  # noqa: BLE001
        raise LaMaRuntimeError(
            "lama_torchscript_load_failed",
            f"加载 LaMa TorchScript 模型失败：{exc}",
        ) from exc

    return LaMaTorchScriptRunner(
        model=model,
        device=device,
        asset_ref=str(Path(asset_ref).expanduser()),
        model_path=str(model_path),
    )


def _normalize_torch_device(torch_device: Any) -> torch.device:
    if isinstance(torch_device, torch.device):
        return torch_device

    if torch_device is None:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    normalized = str(torch_device).strip().lower()
    if normalized == "cuda":
        if not torch.cuda.is_available():
            raise LaMaRuntimeError("lama_cuda_unavailable", "CUDA 不可用，无法加载 LaMa GPU runner。")
        return torch.device("cuda")
    if normalized == "cpu":
        return torch.device("cpu")

    raise LaMaRuntimeError(
        "lama_device_resolution_failed",
        f"无法解析 LaMa 运行设备：{torch_device}",
    )


def _resolve_torchscript_model_path(asset_ref: str) -> Path:
    asset_path = Path(asset_ref).expanduser()
    if not asset_path.exists():
        raise LaMaRuntimeError(
            "lama_model_path_not_found",
            f"LaMa 资源路径不存在：{asset_path}",
        )

    if asset_path.is_file():
        suffix = asset_path.suffix.lower()
        if suffix in TORCHSCRIPT_SUFFIXES:
            return asset_path
        if suffix in {".ckpt", ".pth"}:
            raise LaMaRuntimeError(
                "lama_checkpoint_assets_unsupported",
                "当前 LaMa 运行时仅支持 TorchScript .pt/.jit/.ts 文件，" "暂不直接支持 .ckpt/.pth 训练检查点。",
            )
        raise LaMaRuntimeError(
            "lama_asset_layout_unsupported",
            f"无法识别的 LaMa 资产文件类型：{asset_path.name}",
        )

    torchscript_candidates = list(_iter_torchscript_candidates(asset_path))
    if len(torchscript_candidates) == 1:
        return torchscript_candidates[0]
    if len(torchscript_candidates) > 1:
        candidate_names = ", ".join(path.name for path in torchscript_candidates)
        raise LaMaRuntimeError(
            "lama_asset_layout_unsupported",
            f"LaMa 资产目录存在多个 TorchScript 候选文件，请显式传入文件路径：{candidate_names}",
        )

    if _looks_like_official_checkpoint_assets(asset_path):
        raise LaMaRuntimeError(
            "lama_checkpoint_assets_unsupported",
            "检测到官方 LaMa checkpoint 目录（config.yaml + models/*.ckpt），"
            "当前主工程 runner 仅支持 TorchScript 模型，请先转换为 big-lama.pt 后再使用。",
        )

    raise LaMaRuntimeError(
        "lama_asset_layout_unsupported",
        f"未在目录中找到可用的 LaMa TorchScript 模型：{asset_path}",
    )


def _iter_torchscript_candidates(asset_dir: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    models_dir = asset_dir / "models"
    nested_search_roots = [asset_dir]
    if models_dir.exists() and models_dir.is_dir():
        nested_search_roots.append(models_dir)

    discovered: list[Path] = [asset_dir / name for name in TORCHSCRIPT_CANDIDATE_NAMES]
    for root in nested_search_roots:
        for path in root.iterdir():
            if not path.is_file():
                continue
            if (
                path.name in TORCHSCRIPT_CANDIDATE_NAMES
                or path.suffix.lower() in TORCHSCRIPT_SUFFIXES
            ):
                discovered.append(path)

    for candidate in discovered:
        if not candidate.exists() or not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield candidate


def _looks_like_official_checkpoint_assets(asset_dir: Path) -> bool:
    config_path = asset_dir / "config.yaml"
    models_dir = asset_dir / "models"
    if not config_path.exists() or not models_dir.exists() or not models_dir.is_dir():
        return False
    return any(path.suffix.lower() == ".ckpt" for path in models_dir.iterdir() if path.is_file())


def _prepare_inputs(
    frame: np.ndarray,
    mask: np.ndarray,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, int, int]:
    image_array, mask_array, original_height, original_width = _prepare_input_arrays(frame, mask)
    image_tensor = torch.from_numpy(image_array).unsqueeze(0).to(device)
    mask_tensor = torch.from_numpy(mask_array).unsqueeze(0).to(device)
    return image_tensor, mask_tensor, original_height, original_width


def _prepare_inputs_batch(
    frames: list[np.ndarray],
    masks: list[np.ndarray],
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, list[tuple[int, int]]]:
    if not frames or not masks or len(frames) != len(masks):
        raise LaMaRuntimeError("lama_invalid_batch", "LaMa 批量推理要求 frame/mask 数量一致且非空。")

    prepared_images: list[np.ndarray] = []
    prepared_masks: list[np.ndarray] = []
    original_sizes: list[tuple[int, int]] = []
    max_height = 0
    max_width = 0

    for frame, mask in zip(frames, masks):
        image_array, mask_array, original_height, original_width = _prepare_input_arrays(
            frame, mask
        )
        prepared_images.append(image_array)
        prepared_masks.append(mask_array)
        original_sizes.append((original_height, original_width))
        max_height = max(max_height, int(image_array.shape[1]))
        max_width = max(max_width, int(image_array.shape[2]))

    batch_images = np.stack(
        [
            _pad_chw_to_size(image, max_height=max_height, max_width=max_width)
            for image in prepared_images
        ],
        axis=0,
    )
    batch_masks = np.stack(
        [
            _pad_chw_to_size(mask, max_height=max_height, max_width=max_width)
            for mask in prepared_masks
        ],
        axis=0,
    )

    image_tensor = torch.from_numpy(np.ascontiguousarray(batch_images)).to(device)
    mask_tensor = torch.from_numpy(np.ascontiguousarray(batch_masks)).to(device)
    return image_tensor, mask_tensor, original_sizes


def _prepare_input_arrays(
    frame: np.ndarray,
    mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    image = np.asarray(frame)
    if image.ndim != 3 or image.shape[2] != 3:
        raise LaMaRuntimeError(
            "lama_invalid_frame",
            f"LaMa 仅支持 HWC 三通道图像，当前 shape={image.shape}",
        )

    raw_mask = np.asarray(mask)
    if raw_mask.ndim == 3:
        raw_mask = raw_mask[..., 0]
    if raw_mask.ndim != 2:
        raise LaMaRuntimeError(
            "lama_invalid_mask",
            f"LaMa 仅支持 HW 单通道掩码，当前 shape={raw_mask.shape}",
        )

    original_height, original_width = image.shape[:2]
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    chw_image = np.transpose(rgb_image.astype(np.float32) / 255.0, (2, 0, 1))
    chw_mask = ((raw_mask > 0).astype(np.float32))[None, ...]

    padded_image = _pad_chw_to_modulo(chw_image, 8)
    padded_mask = _pad_chw_to_modulo(chw_mask, 8)
    return padded_image, padded_mask, original_height, original_width


def _pad_chw_to_size(
    image: np.ndarray,
    *,
    max_height: int,
    max_width: int,
) -> np.ndarray:
    channels, height, width = image.shape
    if height == max_height and width == max_width:
        return image
    return np.pad(
        image,
        ((0, 0), (0, max(0, max_height - height)), (0, max(0, max_width - width))),
        mode="symmetric",
    )


def _pad_chw_to_modulo(image: np.ndarray, modulo: int) -> np.ndarray:
    channels, height, width = image.shape
    padded_height = _ceil_modulo(height, modulo)
    padded_width = _ceil_modulo(width, modulo)
    return np.pad(
        image,
        ((0, 0), (0, padded_height - height), (0, padded_width - width)),
        mode="symmetric",
    )


def _ceil_modulo(value: int, modulo: int) -> int:
    if value % modulo == 0:
        return value
    return (value // modulo + 1) * modulo


def _convert_output_to_bgr_image(
    output: Any,
    original_height: int,
    original_width: int,
) -> np.ndarray:
    if isinstance(output, (tuple, list)):
        if not output:
            raise LaMaRuntimeError("lama_invalid_output", "LaMa 模型返回了空输出。")
        output = output[0]

    if not isinstance(output, torch.Tensor):
        raise LaMaRuntimeError(
            "lama_invalid_output",
            f"LaMa 模型返回了不支持的输出类型：{type(output)!r}",
        )

    if output.ndim == 4:
        output = output[0]

    if output.ndim != 3 or output.shape[0] != 3:
        raise LaMaRuntimeError(
            "lama_invalid_output",
            f"LaMa 模型输出 shape 非法：{tuple(output.shape)}",
        )

    cropped = output[:, :original_height, :original_width]
    rgb_image = cropped.detach().float().cpu().clamp(0, 1).permute(1, 2, 0).numpy()
    rgb_uint8 = np.clip(rgb_image * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2BGR)


def _convert_batch_output_to_bgr_images(
    output: Any,
    original_sizes: list[tuple[int, int]],
) -> list[np.ndarray]:
    if isinstance(output, (tuple, list)):
        if not output:
            raise LaMaRuntimeError("lama_invalid_output", "LaMa 模型返回了空输出。")
        output = output[0]

    if not isinstance(output, torch.Tensor):
        raise LaMaRuntimeError(
            "lama_invalid_output",
            f"LaMa 模型返回了不支持的输出类型：{type(output)!r}",
        )

    if output.ndim == 3:
        output = output.unsqueeze(0)

    if output.ndim != 4 or output.shape[1] != 3:
        raise LaMaRuntimeError(
            "lama_invalid_output",
            f"LaMa 批量输出 shape 非法：{tuple(output.shape)}",
        )

    if output.shape[0] != len(original_sizes):
        raise LaMaRuntimeError(
            "lama_invalid_output",
            f"LaMa 批量输出数量异常：batch={int(output.shape[0])} expected={len(original_sizes)}",
        )

    images: list[np.ndarray] = []
    for index, (original_height, original_width) in enumerate(original_sizes):
        images.append(_convert_output_to_bgr_image(output[index], original_height, original_width))
    return images
