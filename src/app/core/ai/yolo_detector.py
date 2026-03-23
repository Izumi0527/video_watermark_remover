#!/usr/bin/env python3
"""
YOLO水印检测器

基于 YOLOv11 的深度学习水印检测，支持多模型切换和自动下载。

"""

from __future__ import annotations

import logging
from configparser import ConfigParser
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Sequence

import cv2
import numpy as np
from numpy.typing import NDArray

from ...config.config_manager import ConfigManager
from ...utils.model_downloader import ModelDownloader
from ..exceptions import DetectionError
from .gpu_monitor import ensure_gpu_memory, get_safe_batch_size

if TYPE_CHECKING:
    from ultralytics import YOLO  # type: ignore[import-not-found]
    from ultralytics.engine.results import Results  # type: ignore[import-not-found]


class YOLOWatermarkDetector:
    """
    基于 YOLOv11 的水印检测器（纯 GPU）

    特性:
    - 纯 GPU pipeline（预处理 → 推理 → 后处理）
    - 支持批处理检测
    - 自动 boxes → mask 转换
    - 多模型支持（yolo11s/yolo11x-watermark/yolo11x-watermark-corzent/custom）
    - 自动模型下载功能
    - 配置文件驱动
    """

    def __init__(
        self,
        config: Optional[ConfigParser] = None,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        device: Optional[str] = None,
    ):
        """
        初始化 YOLO 检测器

        Args:
            config: 配置对象（默认使用默认配置）
            model_path: 模型路径（覆盖配置文件，用于向后兼容）
            conf_threshold: 置信度阈值（覆盖配置文件）
            iou_threshold: IoU 阈值（覆盖配置文件）
            device: 设备 ('cuda' or 'cpu', None=自动检测)
        """
        self.logger = logging.getLogger(__name__)
        self.model: Optional["YOLO"] = None

        # 加载配置（如果未提供则加载默认配置）
        config = config or ConfigManager.load_config()

        # 设备检测
        if device is None:
            # 说明：避免在模块导入阶段强依赖 torch，降低在部分 Windows/Qt 环境下触发
            # WinError 1114（DLL 初始化失败）的概率；仅在确需自动检测时再尝试导入。
            try:
                import torch

                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"PyTorch 初始化失败，默认使用 CPU: {e}")
                self.device = "cpu"
        else:
            self.device = device

        # 从配置读取YOLO参数（支持参数覆盖）
        self.model_type = config.get("YOLO", "model_type", fallback="yolo11x-watermark")
        self.custom_model_path = config.get("YOLO", "custom_model_path", fallback="")
        self.conf_threshold = (
            conf_threshold
            if conf_threshold is not None
            else config.getfloat("YOLO", "conf_threshold", fallback=0.25)
        )
        self.iou_threshold = (
            iou_threshold
            if iou_threshold is not None
            else config.getfloat("YOLO", "iou_threshold", fallback=0.45)
        )
        self.batch_size = config.getint("YOLO", "batch_size", fallback=8)
        self.auto_download = config.getboolean("YOLO", "auto_download_model", fallback=True)
        self.model_dir = Path(config.get("Paths", "default_model_dir", fallback="./models"))
        # 掩码生成参数：用于改善 C（边界不准：偏移/过大/过小）
        # 说明：当前模型输出为检测框（boxes），需要通过 bbox→mask 生成修复区域。
        # 这里将固定 padding 改为“自适应 padding + 可配置微调”，避免不同分辨率/水印尺寸下边界失真。
        self.mask_padding_px = max(0, config.getint("YOLO", "mask_padding_px", fallback=4))
        self.mask_padding_ratio = max(
            0.0, config.getfloat("YOLO", "mask_padding_ratio", fallback=0.02)
        )
        self.mask_padding_max = max(0, config.getint("YOLO", "mask_padding_max", fallback=24))
        self.mask_erode_iterations = max(
            0, config.getint("YOLO", "mask_erode_iterations", fallback=0)
        )
        self.mask_dilate_iterations = max(
            0, config.getint("YOLO", "mask_dilate_iterations", fallback=0)
        )
        self.mask_close_kernel = max(0, config.getint("YOLO", "mask_close_kernel", fallback=5))

        # 确定模型路径（优先级：参数 > 配置 > 自动选择）
        if model_path:
            # 向后兼容：直接使用传入的model_path
            self.model_path = model_path
            self.logger.info(f"Using custom model path from parameter: {model_path}")
        else:
            # 根据配置选择模型
            self.model_path = self._resolve_model_path()

        self.logger.info("YOLOWatermarkDetector v2.0 initialized")
        self.logger.info(f"  - Device: {self.device}")
        self.logger.info(f"  - Model Type: {self.model_type}")
        self.logger.info(f"  - Model Path: {self.model_path}")
        self.logger.info(f"  - Conf Threshold: {self.conf_threshold}")
        self.logger.info(f"  - IoU Threshold: {self.iou_threshold}")
        self.logger.info(f"  - Batch Size: {self.batch_size}")

    def _resolve_model_path(self) -> str:  # noqa: C901
        """
        根据配置解析模型路径

        Returns:
            模型文件路径

        Raises:
            DetectionError: 模型路径无效或模型不存在
        """
        # 情况1：使用自定义模型路径
        if self.model_type == "custom":
            if not self.custom_model_path:
                raise DetectionError("model_type=custom 但未指定 custom_model_path")

            custom_path = Path(self.custom_model_path)
            if custom_path.exists():
                return str(custom_path)
            else:
                raise DetectionError(f"自定义模型文件不存在: {self.custom_model_path}")

        # 情况2：使用预定义模型（yolo11s / yolo11x-watermark / yolo11x-watermark-corzent）
        if self.model_type not in ["yolo11s", "yolo11x-watermark", "yolo11x-watermark-corzent"]:
            raise DetectionError(
                f"未知的model_type: {self.model_type}，"
                f"支持的类型: yolo11s, yolo11x-watermark, yolo11x-watermark-corzent, custom"
            )

        # 获取模型文件名
        downloader = ModelDownloader(str(self.model_dir))
        model_info = downloader.MODELS.get(self.model_type)
        if not model_info:
            raise DetectionError(f"未找到模型配置: {self.model_type}")

        model_file = self.model_dir / model_info["filename"]

        # 检查模型是否存在
        if not model_file.exists():
            if self.auto_download:
                self.logger.warning(f"模型文件不存在: {model_file}")
                self.logger.info(f"自动下载 {self.model_type} 模型...")

                # 自动下载模型
                downloaded_path = downloader.download_model(self.model_type, force=False)
                if not downloaded_path:
                    if self.model_type == "yolo11x-watermark-corzent":
                        self.logger.warning("corzent 版本模型下载失败，自动降级到默认模型 yolo11x-watermark")
                        self.model_type = "yolo11x-watermark"
                        return self._resolve_model_path()
                    raise DetectionError(f"模型下载失败: {self.model_type}")

                self.logger.info(f"✅ 模型下载成功: {downloaded_path}")
                return str(downloaded_path)
            else:
                if self.model_type == "yolo11x-watermark-corzent":
                    self.logger.warning(f"corzent 版本模型文件不存在且自动下载已禁用：{model_file}")
                    self.logger.info("自动降级到默认模型 yolo11x-watermark")
                    self.model_type = "yolo11x-watermark"
                    return self._resolve_model_path()
                raise DetectionError(
                    f"模型文件不存在且自动下载已禁用: {model_file}\n" f"请手动下载或设置 auto_download_model=yes"
                )

        return str(model_file)

    def load_model(self) -> bool:
        """
        加载 YOLO 模型到 GPU/CPU

        Returns:
            bool: 加载是否成功
        """
        try:
            from ultralytics import YOLO

            self.logger.info(f"Loading YOLO model from: {self.model_path}")

            # 加载模型
            model = YOLO(self.model_path)

            # 移动到设备
            model.to(self.device)
            self.model = model

            self.logger.info("✅ YOLO model loaded successfully")
            self.logger.info(f"  - Model Type: {self.model_type}")
            self.logger.info(f"  - Device: {self.device}")
            self.logger.info(f"  - Conf threshold: {self.conf_threshold}")
            self.logger.info(f"  - IoU threshold: {self.iou_threshold}")
            self.logger.info(f"  - Batch size: {self.batch_size}")

            return True

        except FileNotFoundError:
            self.logger.error(f"❌ Model file not found: {self.model_path}")

            # 如果是预定义模型且auto_download开启，尝试下载
            if (
                self.model_type in ["yolo11s", "yolo11x-watermark", "yolo11x-watermark-corzent"]
                and self.auto_download
            ):
                self.logger.info("Attempting to download missing model...")
                try:
                    downloader = ModelDownloader(str(self.model_dir))
                    downloaded_path = downloader.download_model(self.model_type, force=False)
                    if downloaded_path:
                        self.model_path = str(downloaded_path)
                        # 递归调用load_model重新加载
                        return self.load_model()
                except Exception as e:
                    self.logger.error(f"Failed to download model: {e}")
                    return False

            # 模型下载失败或auto_download未开启，直接返回False
            self.logger.error(
                "Model loading failed. Please ensure model file exists or enable auto_download_model."
            )
            return False

        except Exception as e:
            self.logger.error(f"❌ Failed to load YOLO model: {e}")
            return False

    def detect_watermark(self, frame: NDArray[np.uint8]) -> Optional[NDArray[np.uint8]]:
        """
        检测水印区域（纯 GPU pipeline）

        Args:
            frame: 输入图像 (H, W, 3) BGR uint8

        Returns:
            二值掩码 (H, W) uint8, 255=水印, 0=干净
            None if detection fails
        """
        model = self.model
        if model is None:
            self.logger.warning("YOLO model not loaded")
            return None

        if frame is None or frame.size == 0:
            self.logger.warning("Invalid input frame")
            return None

        try:
            # GPU 显存检查（仅在 GPU 模式下）
            if self.device == "cuda":
                if not ensure_gpu_memory(min_free_mb=300):
                    self.logger.warning("Insufficient GPU memory for detection")
                    # 不抛出异常，让检测继续（可能会触发 CUDA OOM）

            # YOLO 推理（纯 GPU）
            results: Sequence["Results"] = model(
                frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
                device=self.device,
            )

            # Results → Mask 转换（优先使用分割 masks，若无则回退到 boxes）
            mask = self._result_to_mask(results[0], frame.shape)

            return mask

        except Exception as e:
            self.logger.error(f"YOLO detection failed: {e}")
            raise DetectionError(f"YOLO 检测失败: {e}")

    def detect_batch(self, frames: List[NDArray[np.uint8]]) -> List[Optional[NDArray[np.uint8]]]:
        """
        批量检测水印（GPU 优势）

        使用 GPU 显存监控自动调整批大小，防止 OOM

        Args:
            frames: 帧列表 [(H, W, 3) BGR uint8]

        Returns:
            掩码列表 [(H, W) uint8]
        """
        model = self.model
        if model is None:
            self.logger.warning("YOLO model not loaded")
            return [None] * len(frames)

        if not frames or len(frames) == 0:
            return []

        try:
            # GPU 显存自适应批大小
            if self.device == "cuda" and len(frames) > 0:
                frame_size = frames[0].shape[:2]  # (H, W)
                safe_batch_size = get_safe_batch_size(self.batch_size, frame_size)

                if safe_batch_size < len(frames):
                    self.logger.info(
                        f"Adaptive batch size: processing {len(frames)} frames "
                        f"in batches of {safe_batch_size}"
                    )
                    # 分批处理
                    all_masks = []
                    for i in range(0, len(frames), safe_batch_size):
                        batch = frames[i : i + safe_batch_size]

                        # 确保有足够显存
                        ensure_gpu_memory(min_free_mb=300)

                        # 批量推理
                        results: Sequence["Results"] = model(
                            batch,
                            conf=self.conf_threshold,
                            iou=self.iou_threshold,
                            verbose=False,
                            device=self.device,
                        )

                        # 转换掩码
                        for j, result in enumerate(results):
                            mask = self._result_to_mask(result, batch[j].shape)
                            all_masks.append(mask)

                    return all_masks

            # 标准批量推理（GPU 并行）
            results = model(
                frames,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
                device=self.device,
            )

            # 批量转换 Boxes → Mask
            masks = []
            for i, result in enumerate(results):
                mask = self._result_to_mask(result, frames[i].shape)
                masks.append(mask)

            return masks

        except Exception as e:
            self.logger.error(f"Batch detection failed: {e}")
            raise DetectionError(f"批量检测失败: {e}")

    def _compute_axis_padding(self, axis_len: int) -> int:
        """
        计算单个轴方向的自适应 padding。

        规则：
        - 最小 padding：mask_padding_px
        - 动态 padding：axis_len * mask_padding_ratio
        - 最大 padding：mask_padding_max
        """
        dynamic_pad = int(round(axis_len * self.mask_padding_ratio))
        pad = max(self.mask_padding_px, dynamic_pad)
        if self.mask_padding_max > 0:
            pad = min(pad, self.mask_padding_max)
        return max(0, pad)

    def _compute_box_padding(self, box_w: int, box_h: int) -> tuple[int, int]:
        """
        计算检测框在 x/y 两个方向的 padding（避免长条框在短边方向被过度扩张）。
        """
        return self._compute_axis_padding(box_w), self._compute_axis_padding(box_h)

    def _postprocess_mask(self, mask: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        对掩码做轻量后处理，用于微调边界与连接断裂区域。
        """
        if mask is None or not np.any(mask):
            return mask

        # 细粒度膨胀/腐蚀（可用于“略扩大/略收缩”边界）
        fine_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        if self.mask_erode_iterations > 0:
            mask = np.asarray(cv2.erode(mask, fine_kernel, iterations=self.mask_erode_iterations))
        if self.mask_dilate_iterations > 0:
            mask = np.asarray(cv2.dilate(mask, fine_kernel, iterations=self.mask_dilate_iterations))

        # 闭运算：连接近邻区域、填补小孔洞（kernel 尺寸应为奇数）
        k = int(self.mask_close_kernel)
        if k > 0:
            if k % 2 == 0:
                k += 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
            mask = np.asarray(cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel))

        return mask

    def _masks_to_mask(  # noqa: C901
        self, masks: Any, frame_shape: Sequence[int]
    ) -> Optional[NDArray[np.uint8]]:
        """
        将 YOLO 分割 masks 转换为二值 mask（若模型为 segmentation，则边界更精准）。
        """
        h, w = frame_shape[:2]
        out: NDArray[np.uint8] = np.zeros((h, w), dtype=np.uint8)

        if masks is None:
            return None

        # 优先尝试使用 masks.data（通常为 (N, H, W) 的张量）
        data = getattr(masks, "data", None)
        if data is not None:
            try:
                arr = data.detach().cpu().numpy()
            except Exception:  # noqa: BLE001
                try:
                    arr = np.asarray(data)
                except Exception:  # noqa: BLE001
                    arr = None

            if arr is not None:
                if arr.ndim == 3:
                    merged = (np.sum(arr, axis=0) > 0).astype(np.uint8) * 255
                elif arr.ndim == 2:
                    merged = (arr > 0).astype(np.uint8) * 255
                else:
                    merged = None

                if merged is not None:
                    if merged.shape != (h, w):
                        merged = cv2.resize(merged, (w, h), interpolation=cv2.INTER_NEAREST)
                    return self._postprocess_mask(np.asarray(merged, dtype=np.uint8))

        # 兜底：使用 masks.xy（多边形点集，坐标通常为原图像素坐标）
        polys = getattr(masks, "xy", None)
        if polys:
            for poly in polys:
                if poly is None or len(poly) == 0:
                    continue
                pts = np.round(np.asarray(poly)).astype(np.int32)
                if pts.ndim != 2 or pts.shape[1] != 2:
                    continue
                cv2.fillPoly(out, [pts], 255)
            return self._postprocess_mask(out)

        return None

    def _result_to_mask(self, result: Any, frame_shape: Sequence[int]) -> NDArray[np.uint8]:
        """
        将单帧推理结果转换为二值 mask：
        - 若存在 segmentation masks，优先使用（边界更准）
        - 否则使用检测框 boxes，并做自适应 padding 与后处理
        """
        masks = getattr(result, "masks", None)
        seg_mask = self._masks_to_mask(masks, frame_shape)
        if seg_mask is not None and np.any(seg_mask):
            return seg_mask
        return self._boxes_to_mask(getattr(result, "boxes", None), frame_shape)

    def _boxes_to_mask(  # noqa: C901
        self, boxes: Any, frame_shape: Sequence[int]
    ) -> NDArray[np.uint8]:
        """
        将 YOLO bounding boxes 转换为二值 mask

        Args:
            boxes: YOLO boxes 对象
            frame_shape: 帧形状 (H, W, C)

        Returns:
            二值 mask (H, W) uint8
        """
        h, w = frame_shape[:2]
        mask: NDArray[np.uint8] = np.zeros((h, w), dtype=np.uint8)

        if boxes is None or len(boxes) == 0:
            return mask

        # 兼容 ultralytics Boxes：优先一次性取出 xyxy，避免循环中频繁 cpu() 开销
        xyxy_arr = None
        try:
            xyxy_arr = boxes.xyxy.detach().cpu().numpy()
        except Exception:  # noqa: BLE001
            xyxy_arr = None

        if xyxy_arr is None:
            # 兜底：逐个 box 读取
            coords_list = []
            for box in boxes:
                coords = None
                try:
                    coords = box.xyxy[0].detach().cpu().numpy()
                except Exception:  # noqa: BLE001
                    coords = None
                if coords is None or len(coords) < 4:
                    continue
                coords_list.append(coords[:4])
            if coords_list:
                xyxy_arr = np.asarray(coords_list, dtype=np.float32)

        if xyxy_arr is None or xyxy_arr.size == 0:
            return mask

        # 遍历所有检测框，生成 mask
        for coord in xyxy_arr:
            x1_f, y1_f, x2_f, y2_f = (
                float(coord[0]),
                float(coord[1]),
                float(coord[2]),
                float(coord[3]),
            )

            # 起点用 floor，终点用 ceil，确保覆盖完整目标
            x1 = int(np.floor(x1_f))
            y1 = int(np.floor(y1_f))
            x2 = int(np.ceil(x2_f))
            y2 = int(np.ceil(y2_f))

            box_w = max(0, x2 - x1)
            box_h = max(0, y2 - y1)
            pad_x, pad_y = self._compute_box_padding(box_w, box_h)

            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(w - 1, x2 + pad_x)
            y2 = min(h - 1, y2 + pad_y)

            if x2 <= x1 or y2 <= y1:
                continue

            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

        return self._postprocess_mask(mask)

    def cleanup(self):
        """清理 GPU 内存"""
        if self.device != "cuda":
            return

        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                self.logger.debug("GPU memory cache cleared")
        except Exception as e:  # noqa: BLE001
            self.logger.debug(f"GPU cleanup skipped: {e}")


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
        if mask is not None:
            print(f"   Mask shape: {mask.shape}")
            print(f"   Detected pixels: {np.sum(mask > 0)}")
        else:
            print("   未生成掩码，检测返回 None")

        # 批处理测试
        batch_frames = [test_frame] * 4

        start = time.time()
        batch_masks = detector.detect_batch(batch_frames)
        elapsed = time.time() - start

        print(f"✅ 批处理推理完成 (4 帧): {elapsed * 1000:.2f} ms " f"({elapsed * 1000 / 4:.2f} ms/帧)")
        detected_counts = [int(np.sum(mask > 0)) for mask in batch_masks if mask is not None]
        if detected_counts:
            print(f"   掩码像素统计: {detected_counts}")
        else:
            print("   批处理未返回有效掩码")

        # 清理
        detector.cleanup()
    else:
        print("❌ 模型加载失败")

    print("=" * 60)
