#!/usr/bin/env python3
"""
YOLO模型自动下载工具

支持从Hugging Face自动下载YOLOv11系列水印检测模型。

"""

import hashlib
import logging
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class DownloadProgressBar:
    """下载进度条"""

    def __init__(self, total_size: int):
        """
        初始化进度条

        Args:
            total_size: 文件总大小（字节）
        """
        self.total_size = total_size
        self.downloaded = 0
        self.logger = logging.getLogger(__name__)

    def update(self, block_num: int, block_size: int, total_size: int):
        """
        更新进度

        Args:
            block_num: 当前块编号
            block_size: 块大小
            total_size: 总大小
        """
        self.downloaded = min(block_num * block_size, total_size)
        if total_size > 0:
            percent = self.downloaded / total_size * 100
            downloaded_mb = self.downloaded / 1024 / 1024
            total_mb = total_size / 1024 / 1024
            print(
                f"\r  Progress: {percent:.1f}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)",
                end="",
                flush=True,
            )


class ModelDownloader:
    """
    YOLO模型自动下载器

    支持从Hugging Face下载预训练的YOLO水印检测模型。
    """

    # 可用模型配置
    MODELS: Dict[str, Dict[str, Any]] = {
        "yolo11x-watermark": {
            "url": "https://huggingface.co/spaces/fancyfeast/joycaption-watermark-detection/resolve/main/yolo11x-train28-best.pt",
            "filename": "yolo11x-watermark.pt",
            "size_mb": 114,
            "description": "YOLOv11x专用水印检测模型（>99%准确率）",
            "sha256": None,  # 可选：添加SHA256校验
        },
        "yolo11s": {
            "url": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt",
            "filename": "yolo11s.pt",
            "size_mb": 19,
            "description": "YOLOv11s通用检测模型（COCO数据集）",
            "sha256": None,
        },
    }

    def __init__(self, model_dir: str = "./models"):
        """
        初始化下载器

        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def download_model(
        self, model_key: str, force: bool = False, progress_callback: Optional[Callable] = None
    ) -> Optional[Path]:
        """
        下载指定模型

        Args:
            model_key: 模型标识 (yolo11x-watermark/yolo11s)
            force: 是否强制重新下载
            progress_callback: 进度回调函数

        Returns:
            模型文件路径，失败返回None
        """
        if model_key not in self.MODELS:
            self.logger.error(f"Unknown model: {model_key}")
            self.logger.info(f"Available models: {list(self.MODELS.keys())}")
            return None

        model_info = self.MODELS[model_key]
        model_path = self.model_dir / model_info["filename"]

        # 检查是否已存在
        if model_path.exists() and not force:
            self.logger.info(f"Model already exists: {model_path}")
            # 可选：验证文件完整性
            if self._verify_model(model_path, model_info.get("sha256")):
                return model_path
            else:
                self.logger.warning("Model file corrupted, re-downloading...")

        # 开始下载
        self.logger.info(f"Downloading {model_info['description']}...")
        self.logger.info(f"  URL: {model_info['url']}")
        self.logger.info(f"  Size: ~{model_info['size_mb']}MB")
        self.logger.info(f"  Target: {model_path}")

        try:
            # 创建进度条
            progress_bar = DownloadProgressBar(model_info["size_mb"] * 1024 * 1024)

            # 下载文件
            urllib.request.urlretrieve(
                model_info["url"], model_path, reporthook=progress_bar.update
            )

            print()  # 换行
            self.logger.info(f"✅ Downloaded successfully: {model_path}")

            # 验证下载的文件
            if not model_path.exists() or model_path.stat().st_size == 0:
                raise Exception("Downloaded file is empty or missing")

            return model_path

        except Exception as e:
            self.logger.error(f"❌ Download failed: {e}")
            if model_path.exists():
                model_path.unlink()  # 删除不完整文件
            return None

    def _verify_model(self, model_path: Path, expected_sha256: Optional[str]) -> bool:
        """
        验证模型文件完整性

        Args:
            model_path: 模型文件路径
            expected_sha256: 期望的SHA256哈希值

        Returns:
            是否验证通过
        """
        if not model_path.exists():
            return False

        # 如果没有提供SHA256，只检查文件是否存在且非空
        if expected_sha256 is None:
            return model_path.stat().st_size > 0

        # 计算SHA256
        sha256_hash = hashlib.sha256()
        with open(model_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        calculated = sha256_hash.hexdigest()
        if calculated != expected_sha256:
            self.logger.error(f"SHA256 mismatch: expected {expected_sha256}, got {calculated}")
            return False

        return True

    def list_available_models(self) -> dict:
        """
        列出所有可用模型

        Returns:
            模型信息字典
        """
        return {
            key: {
                "description": info["description"],
                "size_mb": info["size_mb"],
                "filename": info["filename"],
                "downloaded": (self.model_dir / info["filename"]).exists(),
            }
            for key, info in self.MODELS.items()
        }

    def remove_model(self, model_key: str) -> bool:
        """
        删除已下载的模型

        Args:
            model_key: 模型标识

        Returns:
            是否删除成功
        """
        if model_key not in self.MODELS:
            self.logger.error(f"Unknown model: {model_key}")
            return False

        model_path = self.model_dir / self.MODELS[model_key]["filename"]

        if not model_path.exists():
            self.logger.warning(f"Model file not found: {model_path}")
            return False

        try:
            model_path.unlink()
            self.logger.info(f"Model removed: {model_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove model: {e}")
            return False


# ==================== 命令行工具 ====================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="YOLO模型下载工具")
    parser.add_argument(
        "action",
        choices=["download", "list", "remove"],
        help="操作类型: download(下载), list(列表), remove(删除)",
    )
    parser.add_argument("model", nargs="?", help="模型标识 (yolo11x-watermark/yolo11s)")
    parser.add_argument("--force", action="store_true", help="强制重新下载")
    parser.add_argument("--model-dir", default="./models", help="模型保存目录")

    args = parser.parse_args()

    downloader = ModelDownloader(args.model_dir)

    if args.action == "list":
        print("\n=== 可用模型列表 ===")
        models = downloader.list_available_models()
        for key, info in models.items():
            status = "✅ 已下载" if info["downloaded"] else "❌ 未下载"
            print(f"\n{key}:")
            print(f"  描述: {info['description']}")
            print(f"  大小: {info['size_mb']}MB")
            print(f"  文件名: {info['filename']}")
            print(f"  状态: {status}")

    elif args.action == "download":
        if not args.model:
            print("❌ 错误: 请指定要下载的模型")
            print("可用模型:", list(downloader.MODELS.keys()))
        else:
            result = downloader.download_model(args.model, force=args.force)
            if result:
                print(f"\n✅ 下载成功: {result}")
            else:
                print("\n❌ 下载失败")

    elif args.action == "remove":
        if not args.model:
            print("❌ 错误: 请指定要删除的模型")
        else:
            if downloader.remove_model(args.model):
                print(f"✅ 删除成功: {args.model}")
            else:
                print(f"❌ 删除失败: {args.model}")
