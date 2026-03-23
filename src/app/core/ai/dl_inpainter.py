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
            prepared_mask = self._prepare_mask(mask, active_profile)
            inference_frame_rgb, inference_mask = self._resize_for_inference(
                frame_rgb,
                prepared_mask,
                active_profile,
            )
            frame_tensor = self._preprocess(inference_frame_rgb, inference_mask)

            # GPU 推理
            with torch.no_grad():
                output_tensor = self.model(frame_tensor)

            # 后处理
            result_rgb = self._postprocess(
                output_tensor,
                frame_rgb,
                prepared_mask,
                active_profile,
            )
            result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
            self.last_profile_used = active_profile.to_dict()

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

        except Exception as e:
            self.logger.error(f"Error in batch inpainting: {e}")
            raise InpaintingError(f"Batch inpainting failed: {e}")

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
