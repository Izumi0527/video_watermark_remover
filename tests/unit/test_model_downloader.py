#!/usr/bin/env python3
"""
ModelDownloader 单元测试

测试YOLO模型自动下载功能，包括下载、验证、列表、删除等操作。

作者: Izumi0527
创建时间: 2025-11-22
"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.utils.model_downloader import DownloadProgressBar, ModelDownloader


class TestDownloadProgressBar:
    """测试下载进度条类"""

    def test_init(self):
        """测试进度条初始化"""
        progress = DownloadProgressBar(1024 * 1024)  # 1MB
        assert progress.total_size == 1024 * 1024
        assert progress.downloaded == 0

    def test_update(self, capsys):
        """测试进度更新"""
        progress = DownloadProgressBar(1000)
        progress.update(1, 100, 1000)

        captured = capsys.readouterr()
        assert "Progress:" in captured.out
        assert "10.0%" in captured.out

    def test_update_completion(self, capsys):
        """测试进度完成"""
        progress = DownloadProgressBar(1000)
        progress.update(10, 100, 1000)

        captured = capsys.readouterr()
        assert "100.0%" in captured.out


class TestModelDownloader:
    """测试模型下载器类"""

    @pytest.fixture
    def temp_model_dir(self):
        """创建临时模型目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def downloader(self, temp_model_dir):
        """创建测试用的ModelDownloader实例"""
        return ModelDownloader(str(temp_model_dir))

    def test_init(self, temp_model_dir):
        """测试初始化"""
        downloader = ModelDownloader(str(temp_model_dir))
        assert downloader.model_dir == temp_model_dir
        assert temp_model_dir.exists()

    def test_init_creates_directory(self):
        """测试自动创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir) / "models"
            downloader = ModelDownloader(str(model_dir))
            assert model_dir.exists()

    def test_models_available(self, downloader):
        """测试可用模型配置"""
        assert "yolo11x-watermark" in downloader.MODELS
        assert "yolo11x-watermark-corzent" in downloader.MODELS
        assert "yolo11s" in downloader.MODELS

        yolo11x = downloader.MODELS["yolo11x-watermark"]
        assert yolo11x["filename"] == "yolo11x-watermark.pt"
        assert yolo11x["size_mb"] == 114
        assert "url" in yolo11x
        assert "description" in yolo11x

        corzent = downloader.MODELS["yolo11x-watermark-corzent"]
        assert corzent["filename"] == "yolo11x-watermark-corzent.pt"
        assert corzent["size_mb"] > 0
        assert "url" in corzent
        assert "description" in corzent
        assert "sha256" in corzent

    def test_list_available_models(self, downloader):
        """测试列出可用模型"""
        models = downloader.list_available_models()

        assert "yolo11x-watermark" in models
        assert "yolo11x-watermark-corzent" in models
        assert "yolo11s" in models

        yolo11x = models["yolo11x-watermark"]
        assert yolo11x["description"] == "YOLOv11x专用水印检测模型（>99%准确率）"
        assert yolo11x["size_mb"] == 114
        assert yolo11x["filename"] == "yolo11x-watermark.pt"
        assert yolo11x["downloaded"] is False  # 初始状态未下载

        corzent = models["yolo11x-watermark-corzent"]
        assert "corzent" in corzent["description"].lower()
        assert corzent["size_mb"] > 0
        assert corzent["filename"] == "yolo11x-watermark-corzent.pt"
        assert corzent["downloaded"] is False  # 初始状态未下载

    def test_list_available_models_with_downloaded(self, downloader):
        """测试列出模型（包含已下载状态）"""
        # 创建一个假的模型文件
        fake_model = downloader.model_dir / "yolo11s.pt"
        fake_model.write_text("fake model")

        models = downloader.list_available_models()

        assert models["yolo11s"]["downloaded"] is True
        assert models["yolo11x-watermark"]["downloaded"] is False

    @patch("urllib.request.urlretrieve")
    def test_download_model_success(self, mock_urlretrieve, downloader):
        """测试成功下载模型"""

        # Mock下载函数
        def mock_download(url, path, reporthook=None):
            # 创建假的模型文件
            Path(path).write_bytes(b"fake model content")
            if reporthook:
                reporthook(1, 100, 100)  # 模拟进度回调

        mock_urlretrieve.side_effect = mock_download

        # 执行下载
        result = downloader.download_model("yolo11s")

        assert result is not None
        assert result.exists()
        assert result.name == "yolo11s.pt"
        assert result.read_bytes() == b"fake model content"

    @patch("urllib.request.urlretrieve")
    def test_download_model_verifies_sha256_after_download(self, mock_urlretrieve, temp_model_dir):
        """
        测试：下载完成后会进行 SHA256 校验

        说明：
        - 使用 `yolo11x-watermark-corzent` 作为带 sha256 的示例模型。
        - 写入假内容必然导致校验失败，期望返回 None 且清理文件。
        """

        def mock_download(url, path, reporthook=None):
            Path(path).write_bytes(b"fake model content")

        mock_urlretrieve.side_effect = mock_download

        downloader = ModelDownloader(str(temp_model_dir), max_retries=0)
        result = downloader.download_model("yolo11x-watermark-corzent")

        assert result is None
        assert not (downloader.model_dir / "yolo11x-watermark-corzent.pt").exists()

    def test_download_model_invalid_key(self, downloader):
        """测试下载无效模型"""
        result = downloader.download_model("invalid-model")
        assert result is None

    def test_download_model_already_exists(self, downloader):
        """测试下载已存在的模型（不强制）"""
        # 创建已存在的模型文件
        model_path = downloader.model_dir / "yolo11s.pt"
        model_path.write_bytes(b"existing model")

        # 不强制下载，应直接返回现有路径
        result = downloader.download_model("yolo11s", force=False)

        assert result == model_path
        assert result.read_bytes() == b"existing model"

    @patch("urllib.request.urlretrieve")
    def test_download_model_force_redownload(self, mock_urlretrieve, downloader):
        """测试强制重新下载"""
        # 创建已存在的模型文件
        model_path = downloader.model_dir / "yolo11s.pt"
        model_path.write_bytes(b"old model")

        # Mock下载函数
        def mock_download(url, path, reporthook=None):
            Path(path).write_bytes(b"new model")

        mock_urlretrieve.side_effect = mock_download

        # 强制重新下载
        result = downloader.download_model("yolo11s", force=True)

        assert result is not None
        assert result.read_bytes() == b"new model"

    @patch("urllib.request.urlretrieve")
    def test_download_model_network_error(self, mock_urlretrieve, downloader):
        """测试网络错误"""
        mock_urlretrieve.side_effect = Exception("Network error")

        result = downloader.download_model("yolo11s")
        assert result is None

    @patch("urllib.request.urlretrieve")
    def test_download_model_empty_file(self, mock_urlretrieve, downloader):
        """测试下载空文件"""

        def mock_download(url, path, reporthook=None):
            Path(path).write_bytes(b"")  # 空文件

        mock_urlretrieve.side_effect = mock_download

        result = downloader.download_model("yolo11s")
        assert result is None
        # 空文件应被删除
        assert not (downloader.model_dir / "yolo11s.pt").exists()

    def test_verify_model_no_sha256(self, downloader):
        """测试验证模型（无SHA256）"""
        model_path = downloader.model_dir / "test.pt"
        model_path.write_bytes(b"test content")

        # 没有SHA256时，只检查文件存在且非空
        assert downloader._verify_model(model_path, None) is True

    def test_verify_model_with_sha256(self, downloader):
        """测试验证模型（有SHA256）"""
        model_path = downloader.model_dir / "test.pt"
        content = b"test content"
        model_path.write_bytes(content)

        # 计算正确的SHA256
        sha256_hash = hashlib.sha256(content).hexdigest()

        assert downloader._verify_model(model_path, sha256_hash) is True

    def test_verify_model_sha256_mismatch(self, downloader):
        """测试SHA256不匹配"""
        model_path = downloader.model_dir / "test.pt"
        model_path.write_bytes(b"test content")

        wrong_sha256 = "0" * 64  # 错误的SHA256

        assert downloader._verify_model(model_path, wrong_sha256) is False

    def test_verify_model_not_exists(self, downloader):
        """测试验证不存在的文件"""
        model_path = downloader.model_dir / "nonexistent.pt"
        assert downloader._verify_model(model_path, None) is False

    def test_remove_model_success(self, downloader):
        """测试删除模型成功"""
        # 创建模型文件
        model_path = downloader.model_dir / "yolo11s.pt"
        model_path.write_bytes(b"model content")

        # 删除模型
        result = downloader.remove_model("yolo11s")

        assert result is True
        assert not model_path.exists()

    def test_remove_model_not_exists(self, downloader):
        """测试删除不存在的模型"""
        result = downloader.remove_model("yolo11s")
        assert result is False

    def test_remove_model_invalid_key(self, downloader):
        """测试删除无效模型"""
        result = downloader.remove_model("invalid-model")
        assert result is False

    def test_remove_model_permission_error(self, downloader):
        """测试删除模型时权限错误"""
        model_path = downloader.model_dir / "yolo11s.pt"
        model_path.write_bytes(b"model content")

        # Mock unlink抛出异常
        with patch.object(Path, "unlink", side_effect=PermissionError("Permission denied")):
            result = downloader.remove_model("yolo11s")
            assert result is False


# ==================== 集成测试 ====================


@pytest.mark.integration
class TestModelDownloaderIntegration:
    """集成测试（需要网络连接）"""

    @pytest.fixture
    def temp_model_dir(self):
        """创建临时模型目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def downloader(self, temp_model_dir):
        """创建测试用的ModelDownloader实例"""
        return ModelDownloader(str(temp_model_dir))

    @pytest.mark.slow
    @pytest.mark.skip(reason="需要网络连接，跳过以加快测试速度")
    def test_real_download_yolo11s(self, downloader):
        """真实下载yolo11s模型（需要网络）"""
        result = downloader.download_model("yolo11s")

        assert result is not None
        assert result.exists()
        assert result.stat().st_size > 10 * 1024 * 1024  # 应该>10MB

    @pytest.mark.slow
    @pytest.mark.skip(reason="需要网络连接且文件较大，跳过以加快测试速度")
    def test_real_download_yolo11x_watermark(self, downloader):
        """真实下载yolo11x-watermark模型（需要网络）"""
        result = downloader.download_model("yolo11x-watermark")

        assert result is not None
        assert result.exists()
        assert result.stat().st_size > 100 * 1024 * 1024  # 应该>100MB


# ==================== 命令行测试 ====================


@pytest.mark.cli
class TestModelDownloaderCLI:
    """测试命令行工具"""

    @pytest.fixture
    def temp_model_dir(self):
        """创建临时模型目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_cli_list(self, temp_model_dir, capsys):
        """测试CLI列表功能"""
        downloader = ModelDownloader(str(temp_model_dir))

        # 模拟命令行参数
        import sys

        sys.argv = ["model_downloader.py", "list"]

        # 直接调用功能（不启动main）
        models = downloader.list_available_models()

        assert len(models) >= 2
        assert "yolo11s" in models
        assert "yolo11x-watermark" in models

    @patch("urllib.request.urlretrieve")
    def test_cli_download(self, mock_urlretrieve, temp_model_dir):
        """测试CLI下载功能"""

        def mock_download(url, path, reporthook=None):
            Path(path).write_bytes(b"downloaded model")

        mock_urlretrieve.side_effect = mock_download

        downloader = ModelDownloader(str(temp_model_dir))
        result = downloader.download_model("yolo11s")

        assert result is not None
        assert result.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
