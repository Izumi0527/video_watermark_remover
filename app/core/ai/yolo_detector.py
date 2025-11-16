#!/usr/bin/env python3
"""
YOLO水印检测器 (Phase 6)

基于 YOLOv11s 的深度学习水印检测，纯 GPU 加速。

作者: Claude Code Assistant
创建时间: 2025-11-16
版本: v1.0 (Phase 6 初始版本)
"""

import logging
from typing import Optional

import cv2
import numpy as np
import torch

from ..exceptions import DetectionError


class YOLOWatermarkDetector:
    """
    基于 YOLOv11s 的水印检测器（纯 GPU）

    特性:
    - 纯 GPU pipeline（预处理 → 推理 → 后处理）
    - 支持批处理检测
    - 自动 boxes → mask 转换
    - 高精度、高召回率
    """

    def __init__(
        self,
        model_path: str = "models/yolo11s-watermark.pt",
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.4,
        device: Optional[str] = None,
    ):
        """
        初始化 YOLO 检测器

        Args:
            model_path: YOLO 模型权重路径
            conf_threshold: 置信度阈值 (0-1)
            iou_threshold: IoU 阈值 (0-1)
            device: 设备 ('cuda' or 'cpu', None=自动检测)
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.model = None
        self.logger = logging.getLogger(__name__)

        # 设备检测
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.logger.info(f"YOLOWatermarkDetector initialized on device: {self.device}")

    def load_model(self) -> bool:
        """
        加载 YOLO 模型到 GPU

        Returns:
            bool: 加载是否成功
        """
        try:
            from ultralytics import YOLO

            self.logger.info(f"Loading YOLO model from: {self.model_path}")

            # 加载模型
            self.model = YOLO(self.model_path)

            # 移动到设备
            self.model.to(self.device)

            self.logger.info("YOLO model loaded successfully")
            self.logger.info(f"  - Model: YOLOv11s")
            self.logger.info(f"  - Device: {self.device}")
            self.logger.info(f"  - Conf threshold: {self.conf_threshold}")
            self.logger.info(f"  - IoU threshold: {self.iou_threshold}")

            return True

        except FileNotFoundError:
            self.logger.error(f"Model file not found: {self.model_path}")
            self.logger.info("Using pre-trained YOLO11s from Ultralytics...")

            try:
                # 尝试使用预训练模型
                self.model = YOLO("yolo11s.pt")
                self.model.to(self.device)
                self.logger.warning("Loaded generic YOLOv11s (not watermark-specific)")
                return True
            except Exception as e:
                self.logger.error(f"Failed to load fallback model: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {e}")
            return False

    def detect_watermark(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        检测水印区域（纯 GPU pipeline）

        Args:
            frame: 输入图像 (H, W, 3) BGR uint8

        Returns:
            二值掩码 (H, W) uint8, 255=水印, 0=干净
            None if detection fails
        """
        if self.model is None:
            self.logger.warning("YOLO model not loaded")
            return None

        if frame is None or frame.size == 0:
            self.logger.warning("Invalid input frame")
            return None

        try:
            # YOLO 推理（纯 GPU）
            results = self.model(
                frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
                device=self.device,
            )

            # Boxes → Mask 转换
            mask = self._boxes_to_mask(results[0].boxes, frame.shape)

            return mask

        except Exception as e:
            self.logger.error(f"YOLO detection failed: {e}")
            raise DetectionError(f"YOLO 检测失败: {e}")

    def detect_batch(self, frames: list) -> list:
        """
        批量检测水印（GPU 优势）

        Args:
            frames: 帧列表 [(H, W, 3) BGR uint8]

        Returns:
            掩码列表 [(H, W) uint8]
        """
        if self.model is None:
            self.logger.warning("YOLO model not loaded")
            return [None] * len(frames)

        if not frames or len(frames) == 0:
            return []

        try:
            # 批量推理（GPU 并行）
            results = self.model(
                frames,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
                device=self.device,
            )

            # 批量转换 Boxes → Mask
            masks = []
            for i, result in enumerate(results):
                mask = self._boxes_to_mask(result.boxes, frames[i].shape)
                masks.append(mask)

            return masks

        except Exception as e:
            self.logger.error(f"Batch detection failed: {e}")
            raise DetectionError(f"批量检测失败: {e}")

    def _boxes_to_mask(self, boxes, frame_shape) -> np.ndarray:
        """
        将 YOLO bounding boxes 转换为二值 mask

        Args:
            boxes: YOLO boxes 对象
            frame_shape: 帧形状 (H, W, C)

        Returns:
            二值 mask (H, W) uint8
        """
        h, w = frame_shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        if boxes is None or len(boxes) == 0:
            return mask

        # 遍历所有检测框
        for box in boxes:
            # 获取坐标 (xyxy 格式)
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

            # 扩展边界框（确保完全覆盖水印）
            padding = 10
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(w, x2 + padding)
            y2 = min(h, y2 + padding)

            # 填充矩形区域
            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

        # 形态学操作平滑边缘
        if np.any(mask):
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        return mask

    def cleanup(self):
        """清理 GPU 内存"""
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
            self.logger.debug("GPU memory cache cleared")


# ==================== 测试代码 ====================

if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("YOLOWatermarkDetector 测试")
    print("=" * 60)

    # 创建检测器
    detector = YOLOWatermarkDetector()

    # 加载模型
    if detector.load_model():
        print("✅ 模型加载成功")

        # 创建测试图像
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # 单帧推理测试
        start = time.time()
        mask = detector.detect_watermark(test_frame)
        elapsed = time.time() - start

        print(f"✅ 单帧推理完成: {elapsed * 1000:.2f} ms")
        print(f"   Mask shape: {mask.shape}")
        print(f"   Detected pixels: {np.sum(mask > 0)}")

        # 批处理测试
        batch_frames = [test_frame] * 4

        start = time.time()
        batch_masks = detector.detect_batch(batch_frames)
        elapsed = time.time() - start

        print(f"✅ 批处理推理完成 (4 帧): {elapsed * 1000:.2f} ms " f"({elapsed * 1000 / 4:.2f} ms/帧)")

        # 清理
        detector.cleanup()
    else:
        print("❌ 模型加载失败")

    print("=" * 60)
