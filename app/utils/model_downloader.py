#!/usr/bin/env python3
"""
YOLO模型自动下载工具

支持从Hugging Face自动下载YOLOv11系列水印检测模型。
包含自动重试和指数退避机制。

"""

import hashlib
import logging
import socket
import time
import urllib.error
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
    包含自动重试、指数退避和超时控制。
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

    # 重试配置
    DEFAULT_MAX_RETRIES = 3  # 最大重试次数
    DEFAULT_TIMEOUT_SECONDS = 60  # 单次下载超时（秒）
    DEFAULT_BASE_DELAY = 2.0  # 基础退避延迟（秒）
    DEFAULT_MAX_DELAY = 30.0  # 最大退避延迟（秒）

    def __init__(
        self,
        model_dir: str = "./models",
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
    ):
        """
        初始化下载器

        Args:
            model_dir: 模型保存目录
            max_retries: 最大重试次数
            timeout: 单次下载超时（秒）
            base_delay: 基础退避延迟（秒）
            max_delay: 最大退避延迟（秒）
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

        # 重试配置
        self.max_retries = max_retries
        self.timeout = timeout
        self.base_delay = base_delay
        self.max_delay = max_delay

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        计算指数退避延迟时间

        Args:
            attempt: 当前尝试次数 (0-based)

        Returns:
            延迟秒数
        """
        delay = self.base_delay * (2**attempt)
        return min(delay, self.max_delay)

    def download_model(
        self, model_key: str, force: bool = False, progress_callback: Optional[Callable] = None
    ) -> Optional[Path]:
        """
        下载指定模型（带自动重试）

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

        model_info: Dict[str, Any] = self.MODELS[model_key]
        model_path: Path = self.model_dir / str(model_info["filename"])

        # 检查是否已存在
        if model_path.exists() and not force:
            self.logger.info(f"Model already exists: {model_path}")
            # 可选：验证文件完整性
            if self._verify_model(model_path, model_info.get("sha256")):
                return model_path
            else:
                self.logger.warning("Model file corrupted, re-downloading...")

        # 开始下载（带重试）
        self.logger.info(f"Downloading {model_info['description']}...")
        self.logger.info(f"  URL: {model_info['url']}")
        self.logger.info(f"  Size: ~{model_info['size_mb']}MB")
        self.logger.info(f"  Target: {model_path}")
        self.logger.info(f"  Max retries: {self.max_retries}, Timeout: {self.timeout}s")

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_backoff_delay(attempt - 1)
                    self.logger.info(f"  Retry {attempt}/{self.max_retries} after {delay:.1f}s delay...")
                    time.sleep(delay)

                # 执行单次下载尝试
                result = self._download_with_timeout(
                    model_info["url"],
                    model_path,
                    model_info["size_mb"],
                    progress_callback,
                )

                if result:
                    return model_path

            except (urllib.error.URLError, socket.timeout, OSError) as e:
                last_error = e
                self.logger.warning(f"  Attempt {attempt + 1} failed: {type(e).__name__}: {e}")

                # 清理不完整文件
                if model_path.exists():
                    try:
                        model_path.unlink()
                    except OSError:
                        pass

            except Exception as e:  # noqa: BLE001
                # 其他异常不重试
                last_error = e
                self.logger.error(f"  Unexpected error: {type(e).__name__}: {e}")
                break

        # 所有重试都失败
        self.logger.error(f"❌ Download failed after {self.max_retries + 1} attempts")
        if last_error:
            self.logger.error(f"  Last error: {last_error}")
        return None

    def _download_with_timeout(
        self,
        url: str,
        target_path: Path,
        expected_size_mb: int,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        带超时控制的单次下载

        Args:
            url: 下载URL
            target_path: 目标路径
            expected_size_mb: 预期文件大小MB
            progress_callback: 进度回调

        Returns:
            是否下载成功
        """
        # 设置全局超时
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(self.timeout)

        try:
            # 创建进度条
            progress_bar = DownloadProgressBar(expected_size_mb * 1024 * 1024)

            # 下载文件
            urllib.request.urlretrieve(url, target_path, reporthook=progress_bar.update)

            print()  # 换行
            self.logger.info(f"✅ Downloaded successfully: {target_path}")

            # 验证下载的文件
            if not target_path.exists() or target_path.stat().st_size == 0:
                raise OSError("Downloaded file is empty or missing")

            return True

        finally:
            # 恢复原超时设置
            socket.setdefaulttimeout(old_timeout)

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
