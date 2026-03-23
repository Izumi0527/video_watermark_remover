#!/usr/bin/env python3
"""
深度学习图像修复模块

提供基于深度学习的 GPU 加速图像修复功能：
1. 轻量级 U-Net 架构 inpainting 模型
2. GPU 加速推理
3. 批处理支持
4. 为未来集成更复杂模型预留接口

"""

import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Union, cast

import cv2
import numpy as np
import torch
import torch.nn as nn

from ..exceptions import InpaintingError

# ==================== 轻量级 U-Net Inpainting 模型 ====================


@dataclass
class GPUInpaintingProfile:
    """GPU 修复路径的最小可调 profile。"""

    requested_radius: int
    quality_level: int
    mask_expand_px: int
    mask_feather_px: int
    blend_ratio: float
    resize_limit: int

    def to_dict(self) -> Dict[str, Union[int, float]]:
        return asdict(self)


@dataclass
class PreparedBatchItem:
    """真实 batch 前向前的中间准备数据。"""

    index: int
    original_rgb: np.ndarray
    prepared_mask: np.ndarray
    profile: GPUInpaintingProfile
    inference_frame_rgb: np.ndarray
    inference_mask: np.ndarray
    original_shape: tuple[int, ...]
    inference_shape: tuple[int, ...]


@dataclass(frozen=True)
class TileRegion:
    """单个 tile 在推理图上的覆盖区域。"""

    top: int
    left: int
    bottom: int
    right: int


GPU_MODEL_STRIDE = 16
GPU_TILE_TRIGGER_MAX_DIM = 1024
GPU_TILE_TRIGGER_MAX_PIXELS = 1024 * 1024
GPU_TILE_SIZE = 768
GPU_TILE_OVERLAP = 96


class UNetInpaintingModel(nn.Module):
    """
    轻量级 U-Net 架构的 Inpainting 模型

    专为快速推理和 GPU 加速设计
    """

    def __init__(self, in_channels=4, out_channels=3, base_channels=64):
        """
        初始化 U-Net 模型

        Args:
            in_channels: 输入通道数 (3 RGB + 1 mask = 4)
            out_channels: 输出通道数 (3 RGB)
            base_channels: 基础通道数
        """
        super(UNetInpaintingModel, self).__init__()

        self.base_channels = base_channels

        # Encoder
        self.enc1 = self._conv_block(in_channels, base_channels)
        self.enc2 = self._conv_block(base_channels, base_channels * 2)
        self.enc3 = self._conv_block(base_channels * 2, base_channels * 4)
        self.enc4 = self._conv_block(base_channels * 4, base_channels * 8)

        # Bottleneck
        self.bottleneck = self._conv_block(base_channels * 8, base_channels * 16)

        # Decoder
        self.dec4 = self._upconv_block(base_channels * 16, base_channels * 8)
        self.dec3 = self._upconv_block(base_channels * 8, base_channels * 4)
        self.dec2 = self._upconv_block(base_channels * 4, base_channels * 2)
        self.dec1 = self._upconv_block(base_channels * 2, base_channels)

        # Channel reduction layers (for skip connections)
        # After concatenation, channels are doubled, so we reduce them back
        self.reduce4 = nn.Conv2d(base_channels * 16, base_channels * 8, kernel_size=1)
        self.reduce3 = nn.Conv2d(base_channels * 8, base_channels * 4, kernel_size=1)
        self.reduce2 = nn.Conv2d(base_channels * 4, base_channels * 2, kernel_size=1)
        self.reduce1 = nn.Conv2d(base_channels * 2, base_channels, kernel_size=1)

        # Final output layer
        self.out_conv = nn.Conv2d(base_channels, out_channels, kernel_size=1)

        # Max pooling
        self.pool = nn.MaxPool2d(2)

    def _conv_block(self, in_ch, out_ch):
        """卷积块"""
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def _upconv_block(self, in_ch, out_ch):
        """上采样卷积块"""
        return nn.Sequential(
            nn.ConvTranspose2d(in_ch, out_ch, kernel_size=2, stride=2),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        """
        前向传播

        Args:
            x: 输入 tensor (B, 4, H, W) - RGB + mask

        Returns:
            输出 tensor (B, 3, H, W) - RGB
        """
        # Encoder
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))

        # Bottleneck
        b = self.bottleneck(self.pool(e4))

        # Decoder with skip connections
        d4 = self.dec4(b)
        d4 = torch.cat([d4, e4], dim=1)  # Skip connection: channels doubled
        d4 = self.reduce4(d4)  # Reduce channels back to base_channels * 8

        d3 = self.dec3(d4)
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.reduce3(d3)  # Reduce channels back to base_channels * 4

        d2 = self.dec2(d3)
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.reduce2(d2)  # Reduce channels back to base_channels * 2

        d1 = self.dec1(d2)
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.reduce1(d1)  # Reduce channels back to base_channels

        # Output
        out = self.out_conv(d1)
        out = torch.sigmoid(out)  # 输出范围 [0, 1]

        return out


# ==================== GPU 加速 Inpainter ====================


class DeepLearningInpainter:
    """
    深度学习图像修复器 (GPU 加速)

    使用轻量级 U-Net 模型进行图像修复
    """

    def __init__(self, config=None, device=None):
        """
        初始化深度学习 inpainter

        Args:
            config: 配置对象
            device: PyTorch 设备 (None = 自动检测)
        """
        self.config = config
        self.model = None
        self.logger = logging.getLogger(__name__)

        # 设备设置
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = device

        self.last_profile_used: Optional[Dict[str, Union[int, float]]] = None
        self.last_batch_execution_mode: Optional[str] = None
        self.last_retry_info: Optional[Dict[str, Union[bool, int, str]]] = None
        self.last_oom_retry_used: bool = False
        self.last_oom_retry_count: int = 0
        self.last_retry_profile_used: Optional[Dict[str, Union[int, float]]] = None
        self.logger.info(f"DeepLearningInpainter initialized on device: {self.device}")

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """
        加载深度学习模型

        Args:
            model_path: 预训练模型路径 (None = 使用随机初始化)

        Returns:
            bool: 加载是否成功
        """
        try:
            self.logger.info("Loading deep learning inpainting model...")

            # 创建模型
            self.model = UNetInpaintingModel(in_channels=4, out_channels=3, base_channels=32)

            # 加载预训练权重 (如果提供)
            if model_path and os.path.exists(model_path):
                self.logger.info(f"Loading pretrained weights from: {model_path}")
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
            else:
                self.logger.warning("No pretrained weights provided, using random initialization")
                self.logger.warning("Model will need training or fine-tuning for best results")

            # 移动到设备
            self.model.to(self.device)
            self.model.eval()

            self.logger.info("Deep learning inpainting model loaded successfully")
            self.logger.info("  - Architecture: Lightweight U-Net")
            self.logger.info(f"  - Device: {self.device}")
            self.logger.info(f"  - Parameters: {self._count_parameters():,}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to load deep learning model: {e}")
            return False

    def _count_parameters(self) -> int:
        """统计模型参数量."""
        if self.model is None:
            return 0
        return sum(p.numel() for p in self.model.parameters() if p.requires_grad)

    def inpaint_frame(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        radius: int = 3,
        quality_level: int = 3,
        profile: Optional[Union[GPUInpaintingProfile, Dict[str, Any]]] = None,
    ) -> np.ndarray:
        """
        使用深度学习模型修复单帧

        Args:
            frame: 输入帧 (H, W, 3) BGR uint8
            mask: 掩码 (H, W) uint8, 255=需要修复
            radius: 修复半径，对 GPU 路径映射为上下文扩张强度
            quality_level: 修复质量，对 GPU 路径映射为推理 profile 档位
            profile: 可选的显式 profile，便于上层做更细粒度控制

        Returns:
            修复后的帧 (H, W, 3) BGR uint8
        """
        if self.model is None:
            raise InpaintingError("Model not loaded")

        self._reset_retry_tracking()
        self.last_profile_used = None
        if mask is None or not np.any(mask):
            return frame.copy()

        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            active_profile = self._resolve_profile(
                frame.shape,
                radius=radius,
                quality_level=quality_level,
                profile=profile,
            )
            result_bgr = self._run_single_inference_with_retry(
                frame_rgb,
                mask,
                active_profile,
            )

            return cast(np.ndarray, np.asarray(result_bgr))

        except Exception as e:
            self.logger.error(f"Error in deep learning inpainting: {e}")
            raise InpaintingError(f"Inpainting failed: {e}")

    def inpaint_batch(
        self,
        frames: list,
        masks: list,
        radius: int = 3,
        quality_level: int = 3,
        profiles: Optional[list[Optional[Union[GPUInpaintingProfile, Dict[str, Any]]]]] = None,
    ) -> list:
        """
        批量修复多帧 (GPU 加速优势)

        Args:
            frames: 帧列表 [(H, W, 3) BGR uint8]
            masks: 掩码列表 [(H, W) uint8]
            radius: 默认修复半径
            quality_level: 默认修复质量
            profiles: 每帧可选的显式 profile 列表

        Returns:
            修复后的帧列表
        """
        if self.model is None:
            raise InpaintingError("Model not loaded")

        if len(frames) != len(masks):
            raise ValueError("frames and masks must have same length")

        try:
            self._reset_retry_tracking()
            batch_items = self._prepare_batch_items(
                frames,
                masks,
                radius=radius,
                quality_level=quality_level,
                profiles=profiles,
            )
            results, execution_mode, last_profile_used = self._execute_grouped_batch(
                batch_items,
                frames,
                masks,
                radius=radius,
                quality_level=quality_level,
                profiles=profiles,
            )
            self.last_batch_execution_mode = execution_mode
            self.last_profile_used = last_profile_used
            return results

        except Exception as e:
            self.logger.error(f"Error in batch inpainting: {e}")
            raise InpaintingError(f"Batch inpainting failed: {e}")

    def _prepare_batch_items(
        self,
        frames: list,
        masks: list,
        radius: int = 3,
        quality_level: int = 3,
        profiles: Optional[list[Optional[Union[GPUInpaintingProfile, Dict[str, Any]]]]] = None,
    ) -> list[PreparedBatchItem]:
        """为批量推理预先计算每帧的 profile、掩码和推理输入尺寸。"""
        batch_items: list[PreparedBatchItem] = []

        for index, (frame, mask) in enumerate(zip(frames, masks)):
            current_profile = None
            if profiles is not None and index < len(profiles):
                current_profile = profiles[index]
            batch_items.append(
                self._prepare_batch_item(
                    index,
                    frame,
                    mask,
                    radius=radius,
                    quality_level=quality_level,
                    profile=current_profile,
                )
            )

        return batch_items

    def _prepare_batch_item(
        self,
        index: int,
        frame: np.ndarray,
        mask: np.ndarray,
        radius: int = 3,
        quality_level: int = 3,
        profile: Optional[Union[GPUInpaintingProfile, Dict[str, Any]]] = None,
    ) -> PreparedBatchItem:
        """构造单个批量样本的预处理结果，便于 grouped batch 和 retry 复用。"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resolved_profile = self._resolve_profile(
            frame.shape,
            radius=radius,
            quality_level=quality_level,
            profile=profile,
        )
        prepared_mask = self._prepare_mask(mask, resolved_profile)
        inference_frame_rgb, inference_mask = self._resize_for_inference(
            frame_rgb,
            prepared_mask,
            resolved_profile,
        )
        return PreparedBatchItem(
            index=index,
            original_rgb=frame_rgb,
            prepared_mask=prepared_mask,
            profile=resolved_profile,
            inference_frame_rgb=inference_frame_rgb,
            inference_mask=inference_mask,
            original_shape=tuple(frame.shape),
            inference_shape=tuple(inference_frame_rgb.shape),
        )

    def _get_batch_group_key(
        self,
        item: PreparedBatchItem,
    ) -> Optional[tuple[tuple[tuple[str, Union[int, float]], ...], tuple[int, ...]]]:
        """生成可用于真实 batch 的分组 key；空掩码帧不进入真实 batch。"""
        if not np.any(item.prepared_mask):
            return None

        profile_key = tuple(sorted(item.profile.to_dict().items()))
        return profile_key, item.inference_shape

    def _group_batch_items(
        self, batch_items: list[PreparedBatchItem]
    ) -> list[list[PreparedBatchItem]]:
        """按生效 profile 和实际推理输入尺寸对样本分组。"""
        grouped_items: list[list[PreparedBatchItem]] = []
        grouped_map: Dict[
            tuple[tuple[tuple[str, Union[int, float]], ...], tuple[int, ...]],
            list[PreparedBatchItem],
        ] = {}

        for item in batch_items:
            group_key = self._get_batch_group_key(item)
            if group_key is None:
                grouped_items.append([item])
                continue

            existing_group = grouped_map.get(group_key)
            if existing_group is None:
                existing_group = []
                grouped_map[group_key] = existing_group
                grouped_items.append(existing_group)
            existing_group.append(item)

        return grouped_items

    def _can_use_true_batch(self, batch_items: list[PreparedBatchItem]) -> bool:
        """判断一批样本是否满足真实 GPU batch 前向条件。"""
        if len(batch_items) < 2:
            return False

        first_item = batch_items[0]
        expected_profile = first_item.profile.to_dict()
        expected_inference_shape = first_item.inference_shape

        for item in batch_items:
            if item.profile.to_dict() != expected_profile:
                return False
            if item.inference_shape != expected_inference_shape:
                return False
            if self._requires_tiled_execution(item):
                return False
            if not np.any(item.prepared_mask):
                return False

        return True

    def _requires_tiled_execution(self, item: PreparedBatchItem) -> bool:
        """判断单个 batch item 是否需要改走 tile 内部推理。"""
        return self._should_use_tiled_inference(item.inference_shape, item.profile)

    def _prepare_model_forward_inputs(
        self,
        frame_rgb: np.ndarray,
        mask: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
        """把模型输入 pad 到稳定步幅，并记录裁回尺寸。"""
        height, width = frame_rgb.shape[:2]
        padded_height = max(
            GPU_MODEL_STRIDE, int(np.ceil(height / GPU_MODEL_STRIDE)) * GPU_MODEL_STRIDE
        )
        padded_width = max(
            GPU_MODEL_STRIDE, int(np.ceil(width / GPU_MODEL_STRIDE)) * GPU_MODEL_STRIDE
        )

        if padded_height == height and padded_width == width:
            return frame_rgb, mask, (height, width)

        pad_bottom = padded_height - height
        pad_right = padded_width - width
        padded_frame = cv2.copyMakeBorder(
            frame_rgb,
            0,
            pad_bottom,
            0,
            pad_right,
            cv2.BORDER_REFLECT_101,
        )
        padded_mask = cv2.copyMakeBorder(
            mask,
            0,
            pad_bottom,
            0,
            pad_right,
            cv2.BORDER_REPLICATE,
        )
        return padded_frame, padded_mask, (height, width)

    def _crop_model_output(
        self,
        output_tensor: Union[torch.Tensor, np.ndarray],
        target_shape: tuple[int, int],
    ) -> Union[torch.Tensor, np.ndarray]:
        """把模型输出裁回 pad 前尺寸。"""
        target_height, target_width = target_shape
        return output_tensor[:, :, :target_height, :target_width]

    def _tensor_to_numpy(self, output_tensor: Union[torch.Tensor, np.ndarray]) -> np.ndarray:
        """把模型输出统一转成 numpy，便于 tile 融合。"""
        if hasattr(output_tensor, "detach"):
            output_np = output_tensor.detach().cpu().numpy()
        else:
            output_np = np.asarray(output_tensor)
        return cast(np.ndarray, np.asarray(output_np, dtype=np.float32))

    def _numpy_to_output_tensor(
        self,
        output_array: np.ndarray,
    ) -> Union[torch.Tensor, np.ndarray]:
        """把 numpy 输出还原成 postprocess 可接受的张量形态。"""
        output_array = cast(np.ndarray, np.asarray(output_array, dtype=np.float32))
        from_numpy = getattr(torch, "from_numpy", None)
        if callable(from_numpy):
            output_tensor = from_numpy(output_array)
            to_method = getattr(output_tensor, "to", None)
            if callable(to_method):
                return cast(torch.Tensor, to_method(self.device))
            return cast(torch.Tensor, output_tensor)
        return output_array

    def _run_model_forward(
        self,
        inference_frame_rgb: np.ndarray,
        inference_mask: np.ndarray,
    ) -> Union[torch.Tensor, np.ndarray]:
        """执行一次共享模型前向，并裁回原始推理尺寸。"""
        model = self.model
        if model is None:
            raise InpaintingError("Model not loaded")

        prepared_frame, prepared_mask, target_shape = self._prepare_model_forward_inputs(
            inference_frame_rgb,
            inference_mask,
        )
        frame_tensor = self._preprocess(prepared_frame, prepared_mask)
        with torch.no_grad():
            output_tensor = model(frame_tensor)
        return self._crop_model_output(output_tensor, target_shape)

    def _should_use_tiled_inference(
        self,
        inference_shape: tuple[int, ...],
        profile: GPUInpaintingProfile,
    ) -> bool:
        """根据实际推理尺寸判断是否需要切到 tile 模式。"""
        _ = profile
        height, width = inference_shape[:2]
        pixel_count = height * width
        return (
            max(height, width) > GPU_TILE_TRIGGER_MAX_DIM
            or pixel_count > GPU_TILE_TRIGGER_MAX_PIXELS
        )

    def _build_tile_starts(self, length: int, tile_size: int, overlap: int) -> list[int]:
        """为单个轴生成 tile 起点，确保最后一块兜住边界。"""
        if length <= tile_size:
            return [0]

        step = max(1, tile_size - overlap)
        starts = list(range(0, max(1, length - tile_size + 1), step))
        last_start = max(0, length - tile_size)
        if not starts or starts[-1] != last_start:
            starts.append(last_start)

        deduped_starts: list[int] = []
        for start in starts:
            if not deduped_starts or deduped_starts[-1] != start:
                deduped_starts.append(start)
        return deduped_starts

    def _build_tile_regions(
        self,
        image_shape: tuple[int, ...],
        tile_size: int,
        overlap: int,
    ) -> list[TileRegion]:
        """为推理图生成稳定的 tile 区域列表。"""
        height, width = image_shape[:2]
        effective_tile_size = max(GPU_MODEL_STRIDE, min(tile_size, height, width))
        effective_overlap = max(0, min(overlap, effective_tile_size - 1))
        y_starts = self._build_tile_starts(height, effective_tile_size, effective_overlap)
        x_starts = self._build_tile_starts(width, effective_tile_size, effective_overlap)

        regions: list[TileRegion] = []
        for top in y_starts:
            for left in x_starts:
                regions.append(
                    TileRegion(
                        top=top,
                        left=left,
                        bottom=min(height, top + effective_tile_size),
                        right=min(width, left + effective_tile_size),
                    )
                )
        return regions

    def _build_tile_axis_weight(self, length: int, overlap: int) -> np.ndarray:
        """构造单轴 overlap 融合权重。"""
        weights = np.ones(length, dtype=np.float32)
        feather = min(overlap, max(1, length // 2))
        if feather <= 0:
            return weights

        ramp = np.linspace(0.25, 1.0, feather, dtype=np.float32)
        weights[:feather] = np.minimum(weights[:feather], ramp)
        weights[-feather:] = np.minimum(weights[-feather:], ramp[::-1])
        return weights

    def _build_tile_weight(self, height: int, width: int, overlap: int) -> np.ndarray:
        """构造二维 tile overlap 融合权重。"""
        y_weight = self._build_tile_axis_weight(height, overlap)
        x_weight = self._build_tile_axis_weight(width, overlap)
        return cast(np.ndarray, np.outer(y_weight, x_weight).astype(np.float32))

    def _run_tiled_model_forward(
        self,
        inference_frame_rgb: np.ndarray,
        inference_mask: np.ndarray,
        profile: GPUInpaintingProfile,
    ) -> Union[torch.Tensor, np.ndarray]:
        """按 tile / overlap 执行单帧内部前向，再拼回完整输出。"""
        _ = profile
        height, width = inference_frame_rgb.shape[:2]
        tile_regions = self._build_tile_regions(
            inference_frame_rgb.shape,
            GPU_TILE_SIZE,
            GPU_TILE_OVERLAP,
        )
        merged_output = np.zeros((1, 3, height, width), dtype=np.float32)
        merged_weight = np.zeros((1, 1, height, width), dtype=np.float32)

        for region in tile_regions:
            tile_frame = inference_frame_rgb[region.top : region.bottom, region.left : region.right]
            tile_mask = inference_mask[region.top : region.bottom, region.left : region.right]
            tile_output = self._tensor_to_numpy(self._run_model_forward(tile_frame, tile_mask))
            if tile_output.ndim == 3:
                tile_output = tile_output[np.newaxis, ...]

            tile_height = region.bottom - region.top
            tile_width = region.right - region.left
            tile_output = tile_output[:, :, :tile_height, :tile_width]
            tile_weight = self._build_tile_weight(tile_height, tile_width, GPU_TILE_OVERLAP)
            tile_weight_4d = tile_weight[np.newaxis, np.newaxis, :, :]

            merged_output[:, :, region.top : region.bottom, region.left : region.right] += (
                tile_output * tile_weight_4d
            )
            merged_weight[
                :, :, region.top : region.bottom, region.left : region.right
            ] += tile_weight_4d

        safe_weight = np.maximum(merged_weight, 1e-6)
        merged_output /= safe_weight
        return self._numpy_to_output_tensor(merged_output)

    def _run_true_batch(self, batch_items: list[PreparedBatchItem]) -> list[np.ndarray]:
        """对同尺寸同 profile 的批次执行一次真实 GPU 前向。"""
        model = self.model
        if model is None:
            raise InpaintingError("Model not loaded")

        batch_tensors = [
            self._preprocess(
                *self._prepare_model_forward_inputs(item.inference_frame_rgb, item.inference_mask)[
                    :2
                ]
            )
            for item in batch_items
        ]
        batch_tensor = torch.cat(batch_tensors, dim=0)

        with torch.no_grad():
            output_batch = model(batch_tensor)

        results = []
        for index, item in enumerate(batch_items):
            output_tensor = self._crop_model_output(
                output_batch[index : index + 1],
                (item.inference_shape[0], item.inference_shape[1]),
            )
            result_rgb = self._postprocess(
                output_tensor,
                item.original_rgb,
                item.prepared_mask,
                item.profile,
            )
            result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
            results.append(cast(np.ndarray, np.asarray(result_bgr)))

        self.last_profile_used = batch_items[0].profile.to_dict()
        return results

    def _execute_grouped_batch(
        self,
        batch_items: list[PreparedBatchItem],
        frames: list,
        masks: list,
        radius: int = 3,
        quality_level: int = 3,
        profiles: Optional[list[Optional[Union[GPUInpaintingProfile, Dict[str, Any]]]]] = None,
    ) -> tuple[list[np.ndarray], str, Optional[Dict[str, Union[int, float]]]]:
        """执行按组 batch 编排，并返回最终结果与执行模式。"""
        results = cast(list[Optional[np.ndarray]], [None] * len(batch_items))
        final_profiles: Dict[int, Optional[Dict[str, Union[int, float]]]] = {}
        used_true_batch = False
        used_sequential = False
        true_batch_group_count = 0
        used_oom_retry = False
        oom_retry_count = 0
        last_retry_profile_used: Optional[Dict[str, Union[int, float]]] = None

        for group in self._group_batch_items(batch_items):
            (
                grouped_results,
                group_used_true_batch,
                group_profiles_used,
                group_oom_retry_used,
                group_retry_count,
                group_retry_profile,
            ) = self._execute_batch_group(
                group,
                frames,
                masks,
                radius=radius,
                quality_level=quality_level,
                profiles=profiles,
            )
            if group_used_true_batch:
                used_true_batch = True
                true_batch_group_count += 1
            else:
                used_sequential = True

            if group_oom_retry_used:
                used_oom_retry = True
                oom_retry_count += group_retry_count
                last_retry_profile_used = group_retry_profile

            for item, result, profile_used in zip(group, grouped_results, group_profiles_used):
                results[item.index] = result
                final_profiles[item.index] = profile_used

        if any(result is None for result in results):
            raise InpaintingError("Grouped batch execution produced incomplete results")

        self.last_oom_retry_used = used_oom_retry
        self.last_oom_retry_count = oom_retry_count
        self.last_retry_profile_used = last_retry_profile_used
        if used_oom_retry:
            self.last_retry_info = {"applied": True, "count": oom_retry_count, "reason": "oom"}
        execution_mode = self._resolve_batch_execution_mode(
            used_true_batch,
            used_sequential,
            true_batch_group_count,
        )
        last_profile_used = self._resolve_last_batch_profile(final_profiles, batch_items)
        return cast(list[np.ndarray], results), execution_mode, last_profile_used

    def _execute_batch_group(
        self,
        batch_items: list[PreparedBatchItem],
        frames: list,
        masks: list,
        radius: int = 3,
        quality_level: int = 3,
        profiles: Optional[list[Optional[Union[GPUInpaintingProfile, Dict[str, Any]]]]] = None,
    ) -> tuple[
        list[np.ndarray],
        bool,
        list[Optional[Dict[str, Union[int, float]]]],
        bool,
        int,
        Optional[Dict[str, Union[int, float]]],
    ]:
        """执行单个分组；返回结果以及是否命中真实 batch。"""
        if self._can_use_true_batch(batch_items):
            try:
                return (
                    self._run_true_batch(batch_items),
                    True,
                    [item.profile.to_dict() for item in batch_items],
                    False,
                    0,
                    None,
                )
            except Exception as exc:
                if self._is_oom_error(exc):
                    retry_items = self._build_oom_retry_batch_items(
                        batch_items,
                        frames,
                        masks,
                    )
                    retry_profile_used = retry_items[0].profile.to_dict() if retry_items else None
                    self._clear_cuda_cache_if_possible()
                    try:
                        return (
                            self._run_true_batch(retry_items),
                            True,
                            [item.profile.to_dict() for item in retry_items],
                            True,
                            1,
                            retry_profile_used,
                        )
                    except Exception as retry_exc:
                        self.logger.warning(
                            "Grouped batch OOM retry failed, falling back to sequential mode: %s",
                            retry_exc,
                        )
                else:
                    self.logger.warning(
                        "Grouped batch inpainting failed, falling back to sequential mode: %s",
                        exc,
                    )

        (
            sequential_results,
            sequential_profiles,
            sequential_retry_count,
            sequential_retry_profile,
        ) = self._run_group_sequential(
            batch_items,
            frames,
            masks,
            radius=radius,
            quality_level=quality_level,
            profiles=profiles,
        )
        return (
            sequential_results,
            False,
            sequential_profiles,
            sequential_retry_count > 0,
            sequential_retry_count,
            sequential_retry_profile,
        )

    def _run_group_sequential(
        self,
        batch_items: list[PreparedBatchItem],
        frames: list,
        masks: list,
        radius: int = 3,
        quality_level: int = 3,
        profiles: Optional[list[Optional[Union[GPUInpaintingProfile, Dict[str, Any]]]]] = None,
    ) -> tuple[
        list[np.ndarray],
        list[Optional[Dict[str, Union[int, float]]]],
        int,
        Optional[Dict[str, Union[int, float]]],
    ]:
        """只对当前分组顺序执行，保持结果语义与单帧路径一致。"""
        results: list[np.ndarray] = []
        profiles_used: list[Optional[Dict[str, Union[int, float]]]] = []
        retry_count = 0
        retry_profile_used: Optional[Dict[str, Union[int, float]]] = None

        for item in batch_items:
            current_profile = None
            if profiles is not None and item.index < len(profiles):
                current_profile = profiles[item.index]
            results.append(
                self.inpaint_frame(
                    frames[item.index],
                    masks[item.index],
                    radius=radius,
                    quality_level=quality_level,
                    profile=current_profile,
                )
            )
            profiles_used.append(
                dict(self.last_profile_used) if isinstance(self.last_profile_used, dict) else None
            )
            if isinstance(self.last_retry_info, dict):
                retry_count += int(self.last_retry_info.get("count", 0))
                if isinstance(self.last_profile_used, dict):
                    retry_profile_used = dict(self.last_profile_used)

        return results, profiles_used, retry_count, retry_profile_used

    def _resolve_batch_execution_mode(
        self,
        used_true_batch: bool,
        used_sequential: bool,
        true_batch_group_count: int,
    ) -> str:
        """收口当前批次的执行模式，便于日志与测试观测。"""
        if used_true_batch and used_sequential:
            return "mixed_grouped_batch"
        if used_true_batch and true_batch_group_count > 1:
            return "grouped_true_batch"
        if used_true_batch:
            return "true_batch"
        return "fallback_sequential"

    def _resolve_last_batch_profile(
        self,
        final_profiles: Dict[int, Optional[Dict[str, Union[int, float]]]],
        batch_items: list[PreparedBatchItem],
    ) -> Optional[Dict[str, Union[int, float]]]:
        """返回最后一个有效输入样本的 profile，避免分组执行顺序污染观测。"""
        for item in reversed(batch_items):
            if np.any(item.prepared_mask):
                return final_profiles.get(item.index)
        return None

    def _reset_retry_tracking(self) -> None:
        """重置当前调用的 OOM 重试观测状态。"""
        self.last_retry_info = None
        self.last_oom_retry_used = False
        self.last_oom_retry_count = 0
        self.last_retry_profile_used = None

    def _is_oom_error(self, exc: Exception) -> bool:
        """保守识别 GPU OOM 类失败，避免把普通异常误判为可重试。"""
        message = str(exc).lower()
        oom_markers = (
            "out of memory",
            "cuda out of memory",
            "insufficient memory",
            "cudnn_status_alloc_failed",
            "显存不足",
        )
        return any(marker in message for marker in oom_markers)

    def _build_oom_retry_profile(
        self,
        profile: GPUInpaintingProfile,
    ) -> GPUInpaintingProfile:
        """为 OOM 场景构造更保守的内部重试 profile。"""
        resize_tiers = [512, 640, 768, 960, 1152]
        lower_resize_limit = next(
            (tier for tier in reversed(resize_tiers) if tier < profile.resize_limit),
            max(256, int(round(profile.resize_limit * 0.75))),
        )

        return GPUInpaintingProfile(
            requested_radius=profile.requested_radius,
            quality_level=profile.quality_level,
            mask_expand_px=max(1, profile.mask_expand_px - 1),
            mask_feather_px=max(1, profile.mask_feather_px - 2),
            blend_ratio=max(0.45, round(profile.blend_ratio - 0.1, 2)),
            resize_limit=max(128, lower_resize_limit),
        )

    def _clear_cuda_cache_if_possible(self) -> None:
        """在 OOM 后尽量释放 CUDA cache，帮助下一次保守 profile 重试。"""
        device_type = getattr(self.device, "type", str(self.device))
        empty_cache = getattr(getattr(torch, "cuda", None), "empty_cache", None)
        if device_type == "cuda" and callable(empty_cache):
            empty_cache()

    def _run_single_inference(
        self,
        frame_rgb: np.ndarray,
        prepared_mask: np.ndarray,
        profile: GPUInpaintingProfile,
    ) -> np.ndarray:
        """按给定 profile 执行一次单帧 GPU 推理。"""
        model = self.model
        if model is None:
            raise InpaintingError("Model not loaded")

        inference_frame_rgb, inference_mask = self._resize_for_inference(
            frame_rgb,
            prepared_mask,
            profile,
        )
        if self._should_use_tiled_inference(inference_frame_rgb.shape, profile):
            output_tensor = self._run_tiled_model_forward(
                inference_frame_rgb,
                inference_mask,
                profile,
            )
        else:
            output_tensor = self._run_model_forward(inference_frame_rgb, inference_mask)

        result_rgb = self._postprocess(
            output_tensor,
            frame_rgb,
            prepared_mask,
            profile,
        )
        result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
        return cast(np.ndarray, np.asarray(result_bgr))

    def _run_single_inference_with_retry(
        self,
        frame_rgb: np.ndarray,
        original_mask: np.ndarray,
        active_profile: GPUInpaintingProfile,
    ) -> np.ndarray:
        """执行单帧 GPU 推理；若命中 OOM，则按更保守 profile 自动重试一次。"""
        prepared_mask = self._prepare_mask(original_mask, active_profile)
        try:
            result_bgr = self._run_single_inference(frame_rgb, prepared_mask, active_profile)
            self.last_profile_used = active_profile.to_dict()
            return result_bgr
        except Exception as exc:
            if not self._is_oom_error(exc):
                raise

            retry_profile = self._build_oom_retry_profile(active_profile)
            self.last_retry_info = {"applied": True, "count": 1, "reason": "oom"}
            self.last_oom_retry_used = True
            self.last_oom_retry_count = 1
            self.last_retry_profile_used = retry_profile.to_dict()
            self._clear_cuda_cache_if_possible()
            retry_mask = self._prepare_mask(original_mask, retry_profile)
            result_bgr = self._run_single_inference(frame_rgb, retry_mask, retry_profile)
            self.last_profile_used = retry_profile.to_dict()
            return result_bgr

    def _build_oom_retry_batch_items(
        self,
        batch_items: list[PreparedBatchItem],
        frames: list,
        masks: list,
    ) -> list[PreparedBatchItem]:
        """为 OOM 的 batch 分组构造一组更保守的 retry items。"""
        retry_items: list[PreparedBatchItem] = []
        for item in batch_items:
            retry_profile = self._build_oom_retry_profile(item.profile)
            retry_items.append(
                self._prepare_batch_item(
                    item.index,
                    frames[item.index],
                    masks[item.index],
                    profile=retry_profile,
                )
            )
        return retry_items

    def _run_sequential_batch(
        self,
        frames: list,
        masks: list,
        radius: int = 3,
        quality_level: int = 3,
        profiles: Optional[list[Optional[Union[GPUInpaintingProfile, Dict[str, Any]]]]] = None,
    ) -> list[np.ndarray]:
        """按当前稳定的单帧流程逐帧执行整批样本。"""
        results = []
        for index, (frame, mask) in enumerate(zip(frames, masks)):
            current_profile = None
            if profiles is not None and index < len(profiles):
                current_profile = profiles[index]
            results.append(
                self.inpaint_frame(
                    frame,
                    mask,
                    radius=radius,
                    quality_level=quality_level,
                    profile=current_profile,
                )
            )
        return results

    def _normalize_quality_level(self, quality_level: Optional[int]) -> int:
        """把质量等级收敛到 GPU profile 支持的范围。"""
        try:
            normalized = int(quality_level if quality_level is not None else 3)
        except (TypeError, ValueError):
            normalized = 3
        return max(1, min(5, normalized))

    def _normalize_radius(self, radius: Optional[int]) -> int:
        """把修复半径收敛到稳定的 GPU 上下文扩张范围。"""
        try:
            normalized = int(radius if radius is not None else 3)
        except (TypeError, ValueError):
            normalized = 3
        return max(1, min(12, normalized))

    def _build_inpainting_profile(
        self,
        frame_shape: tuple[int, ...],
        radius: int = 3,
        quality_level: int = 3,
    ) -> GPUInpaintingProfile:
        """
        根据 UI 参数构建 GPU 修复 profile。

        说明：
        - `quality_level` 控制推理分辨率上限、混合强度和羽化强度
        - `radius` 在 GPU 路径上不再表示 OpenCV 半径，而是控制上下文扩张
        """
        _ = frame_shape
        normalized_quality = self._normalize_quality_level(quality_level)
        normalized_radius = self._normalize_radius(radius)

        resize_limit_map = {
            1: 512,
            2: 640,
            3: 768,
            4: 960,
            5: 1152,
        }
        blend_ratio_map = {
            1: 0.55,
            2: 0.65,
            3: 0.75,
            4: 0.85,
            5: 0.92,
        }
        mask_expand_px = normalized_radius + normalized_quality - 1
        mask_feather_px = normalized_quality + max(1, normalized_radius // 2)

        return GPUInpaintingProfile(
            requested_radius=normalized_radius,
            quality_level=normalized_quality,
            mask_expand_px=mask_expand_px,
            mask_feather_px=mask_feather_px,
            blend_ratio=blend_ratio_map[normalized_quality],
            resize_limit=resize_limit_map[normalized_quality],
        )

    def _resolve_profile(
        self,
        frame_shape: tuple[int, ...],
        radius: int = 3,
        quality_level: int = 3,
        profile: Optional[Union[GPUInpaintingProfile, Dict[str, Any]]] = None,
    ) -> GPUInpaintingProfile:
        """解析显式 profile；若未提供则根据参数现算。"""
        if isinstance(profile, GPUInpaintingProfile):
            return profile

        if isinstance(profile, dict):
            requested_radius = profile.get("requested_radius", radius)
            requested_quality = profile.get("quality_level", quality_level)
            resolved = self._build_inpainting_profile(
                frame_shape,
                radius=self._normalize_radius(requested_radius),
                quality_level=self._normalize_quality_level(requested_quality),
            )
            if "mask_expand_px" in profile:
                resolved.mask_expand_px = max(0, int(profile["mask_expand_px"]))
            if "mask_feather_px" in profile:
                resolved.mask_feather_px = max(1, int(profile["mask_feather_px"]))
            if "blend_ratio" in profile:
                resolved.blend_ratio = min(1.0, max(0.0, float(profile["blend_ratio"])))
            if "resize_limit" in profile:
                resolved.resize_limit = max(64, int(profile["resize_limit"]))
            return resolved

        return self._build_inpainting_profile(
            frame_shape,
            radius=radius,
            quality_level=quality_level,
        )

    def _prepare_mask(
        self,
        mask: np.ndarray,
        profile: GPUInpaintingProfile,
    ) -> np.ndarray:
        """按 GPU profile 对掩码做扩张和羽化。"""
        if mask.ndim == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

        prepared_mask = np.where(mask > 127, 255, 0).astype(np.uint8)

        if profile.mask_expand_px > 0:
            kernel_size = profile.mask_expand_px * 2 + 1
            dilate_kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (kernel_size, kernel_size),
            )
            prepared_mask = cv2.dilate(prepared_mask, dilate_kernel, iterations=1)

        if profile.mask_feather_px > 0:
            feather_kernel_size = profile.mask_feather_px * 2 + 1
            feathered_mask = cv2.GaussianBlur(
                prepared_mask,
                (feather_kernel_size, feather_kernel_size),
                0,
            )
            prepared_mask = np.maximum(prepared_mask, feathered_mask)

        return cast(np.ndarray, np.asarray(prepared_mask, dtype=np.uint8))

    def _resize_for_inference(
        self,
        frame_rgb: np.ndarray,
        prepared_mask: np.ndarray,
        profile: GPUInpaintingProfile,
    ) -> tuple[np.ndarray, np.ndarray]:
        """根据 profile 的分辨率上限缩放输入，兼顾性能与质量。"""
        height, width = frame_rgb.shape[:2]
        max_dimension = max(height, width)

        if max_dimension <= profile.resize_limit:
            return frame_rgb, prepared_mask

        scale = profile.resize_limit / float(max_dimension)
        resized_width = max(1, int(round(width * scale)))
        resized_height = max(1, int(round(height * scale)))

        resized_frame = cv2.resize(
            frame_rgb,
            (resized_width, resized_height),
            interpolation=cv2.INTER_AREA,
        )
        resized_mask = cv2.resize(
            prepared_mask,
            (resized_width, resized_height),
            interpolation=cv2.INTER_LINEAR,
        )
        return resized_frame, cast(np.ndarray, np.asarray(resized_mask, dtype=np.uint8))

    def _blend_with_original(
        self,
        generated_rgb: np.ndarray,
        original_rgb: np.ndarray,
        prepared_mask: np.ndarray,
        profile: GPUInpaintingProfile,
    ) -> np.ndarray:
        """按 profile 的羽化掩码和混合强度，把生成结果融合回原图。"""
        if prepared_mask is None or not np.any(prepared_mask):
            return original_rgb.copy()

        alpha = (prepared_mask.astype(np.float32) / 255.0) * float(profile.blend_ratio)
        alpha = np.clip(alpha, 0.0, 1.0)
        alpha_3ch = alpha[:, :, np.newaxis]

        blended = (
            original_rgb.astype(np.float32) * (1.0 - alpha_3ch)
            + generated_rgb.astype(np.float32) * alpha_3ch
        )
        return cast(np.ndarray, np.clip(blended, 0, 255).astype(np.uint8))

    def _preprocess(self, frame_rgb: np.ndarray, mask: np.ndarray) -> torch.Tensor:
        """
        预处理：numpy → PyTorch tensor

        Args:
            frame_rgb: RGB 图像 (H, W, 3) uint8
            mask: 掩码 (H, W) uint8

        Returns:
            tensor (1, 4, H, W) float32, 范围 [0, 1]
        """
        # 归一化到 [0, 1]
        frame_float = frame_rgb.astype(np.float32) / 255.0
        mask_float = mask.astype(np.float32) / 255.0

        # HWC → CHW
        frame_chw = np.transpose(frame_float, (2, 0, 1))  # (3, H, W)
        mask_chw = mask_float[np.newaxis, :, :]  # (1, H, W)

        # 合并 RGB + mask
        input_array = np.concatenate([frame_chw, mask_chw], axis=0)  # (4, H, W)

        # numpy → torch tensor
        input_tensor = torch.from_numpy(input_array).unsqueeze(0)  # (1, 4, H, W)
        input_tensor = input_tensor.to(self.device)

        return input_tensor

    def _postprocess(
        self,
        output_tensor: torch.Tensor,
        original_rgb: np.ndarray,
        prepared_mask: np.ndarray,
        profile: GPUInpaintingProfile,
    ) -> np.ndarray:
        """
        后处理：PyTorch tensor → numpy，并混合原图

        Args:
            output_tensor: 模型输出 (1, 3, H, W) float32 [0, 1]
            original_rgb: 原始 RGB 图像 (H, W, 3) uint8
            prepared_mask: 经过扩张和羽化后的掩码
            profile: 当前生效的 GPU 修复 profile

        Returns:
            result_rgb: 修复后 RGB 图像 (H, W, 3) uint8
        """
        # tensor → numpy
        output_np = output_tensor.squeeze(0).detach().cpu().numpy()  # (3, H, W)
        output_np = np.transpose(output_np, (1, 2, 0))  # (H, W, 3)
        output_np = np.clip(output_np * 255, 0, 255).astype(np.uint8)

        if output_np.shape[:2] != original_rgb.shape[:2]:
            output_np = cv2.resize(
                output_np,
                (original_rgb.shape[1], original_rgb.shape[0]),
                interpolation=cv2.INTER_CUBIC,
            )

        return self._blend_with_original(output_np, original_rgb, prepared_mask, profile)

    def cleanup(self):
        """清理 GPU 内存"""
        device_type = getattr(self.device, "type", str(self.device))
        if device_type == "cuda":
            torch.cuda.empty_cache()
            self.logger.debug("GPU memory cache cleared")


# ==================== 测试代码 ====================


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("DeepLearningInpainter GPU 测试")
    print("=" * 60)

    # 创建 inpainter
    inpainter = DeepLearningInpainter()

    # 加载模型
    if inpainter.load_model():
        print("✅ 模型加载成功")

        # 创建测试数据
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        test_mask = np.zeros((480, 640), dtype=np.uint8)
        cv2.rectangle(test_mask, (100, 100), (200, 200), 255, -1)

        # 单帧推理测试
        start = time.time()
        result = inpainter.inpaint_frame(test_frame, test_mask)
        elapsed = time.time() - start

        print(f"✅ 单帧推理完成: {elapsed * 1000:.2f} ms")
        print(f"   输出形状: {result.shape}")

        # 批处理测试
        batch_frames = [test_frame] * 4
        batch_masks = [test_mask] * 4

        start = time.time()
        batch_results = inpainter.inpaint_batch(batch_frames, batch_masks)
        elapsed = time.time() - start

        print(f"✅ 批处理推理完成 (4 帧): {elapsed * 1000:.2f} ms " f"({elapsed * 1000 / 4:.2f} ms/帧)")

        # 清理
        inpainter.cleanup()
    else:
        print("❌ 模型加载失败")

    print("=" * 60)
