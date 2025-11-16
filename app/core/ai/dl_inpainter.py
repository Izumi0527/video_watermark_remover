#!/usr/bin/env python3
"""
深度学习图像修复模块 (Phase 5 Stage 2)

提供基于深度学习的 GPU 加速图像修复功能：
1. 轻量级 U-Net 架构 inpainting 模型
2. GPU 加速推理
3. 批处理支持
4. 为未来集成更复杂模型预留接口

作者: Claude Code Assistant
创建时间: 2025-11-16
版本: v1.0 (Phase 5 初始版本)
"""

import logging
import os
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn as nn

from ..exceptions import InpaintingError

# ==================== 轻量级 U-Net Inpainting 模型 ====================


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

    def inpaint_frame(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        使用深度学习模型修复单帧

        Args:
            frame: 输入帧 (H, W, 3) BGR uint8
            mask: 掩码 (H, W) uint8, 255=需要修复

        Returns:
            修复后的帧 (H, W, 3) BGR uint8
        """
        if self.model is None:
            raise InpaintingError("Model not loaded")

        if mask is None or not np.any(mask):
            return frame.copy()

        try:
            # 预处理
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_tensor = self._preprocess(frame_rgb, mask)

            # GPU 推理
            with torch.no_grad():
                output_tensor = self.model(frame_tensor)

            # 后处理
            result_rgb = self._postprocess(output_tensor, frame_rgb, mask)
            result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

            return result_bgr  # type: ignore[no-any-return]

        except Exception as e:
            self.logger.error(f"Error in deep learning inpainting: {e}")
            raise InpaintingError(f"Inpainting failed: {e}")

    def inpaint_batch(self, frames: list, masks: list) -> list:
        """
        批量修复多帧 (GPU 加速优势)

        Args:
            frames: 帧列表 [(H, W, 3) BGR uint8]
            masks: 掩码列表 [(H, W) uint8]

        Returns:
            修复后的帧列表
        """
        if self.model is None:
            raise InpaintingError("Model not loaded")

        if len(frames) != len(masks):
            raise ValueError("frames and masks must have same length")

        try:
            # 批量预处理
            batch_tensors = []
            for frame, mask in zip(frames, masks):
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_tensor = self._preprocess(frame_rgb, mask)
                batch_tensors.append(frame_tensor)

            # 合并为 batch
            batch = torch.cat(batch_tensors, dim=0)

            # 批量 GPU 推理
            with torch.no_grad():
                output_batch = self.model(batch)

            # 批量后处理
            results = []
            for i, (frame, mask) in enumerate(zip(frames, masks)):
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result_rgb = self._postprocess(output_batch[i : i + 1], frame_rgb, mask)
                result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
                results.append(result_bgr)

            return results

        except Exception as e:
            self.logger.error(f"Error in batch inpainting: {e}")
            raise InpaintingError(f"Batch inpainting failed: {e}")

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
        self, output_tensor: torch.Tensor, original_rgb: np.ndarray, mask: np.ndarray
    ) -> np.ndarray:
        """
        后处理：PyTorch tensor → numpy，并混合原图

        Args:
            output_tensor: 模型输出 (1, 3, H, W) float32 [0, 1]
            original_rgb: 原始 RGB 图像 (H, W, 3) uint8
            mask: 掩码 (H, W) uint8

        Returns:
            result_rgb: 修复后 RGB 图像 (H, W, 3) uint8
        """
        # tensor → numpy
        output_np = output_tensor.squeeze(0).cpu().numpy()  # (3, H, W)
        output_np = np.transpose(output_np, (1, 2, 0))  # (H, W, 3)
        output_np = (output_np * 255).astype(np.uint8)

        # 混合：只替换掩码区域
        mask_3ch = np.stack([mask] * 3, axis=2)  # (H, W, 3)
        mask_bool = mask_3ch > 127

        result_rgb = original_rgb.copy()
        result_rgb[mask_bool] = output_np[mask_bool]

        return result_rgb

    def cleanup(self):
        """清理 GPU 内存"""
        if self.device.type == "cuda":
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
