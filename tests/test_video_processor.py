#!/usr/bin/env python3
"""
视频处理器完整测试模块

提供VideoProcessorThread的全面测试：
1. 处理器初始化测试
2. 图像处理功能测试
3. 视频处理流程测试（使用模拟数据）
4. 信号发射测试
5. 错误处理测试

作者: Izumi0527
更新时间: 2025-09-06
版本: v2.0 (完整版)
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import cv2
import numpy as np

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.config_manager import ConfigManager
from app.core.video.video_processor import VideoProcessorThread

TEST_VIDEO_DIR = "test_videos"
TEST_IMAGE_DIR = "test_images"


class TestVideoProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        设置测试类 - 创建测试目录和测试数据
        """
        print("Setting up TestVideoProcessor class...")
        cls.temp_dir = tempfile.mkdtemp(prefix="video_processor_test_")
        cls.test_video_dir = os.path.join(cls.temp_dir, TEST_VIDEO_DIR)
        cls.test_image_dir = os.path.join(cls.temp_dir, TEST_IMAGE_DIR)

        os.makedirs(cls.test_video_dir, exist_ok=True)
        os.makedirs(cls.test_image_dir, exist_ok=True)

        # 创建测试图片
        cls._create_test_image()

        # 创建测试视频（小视频）
        cls._create_test_video()

    @classmethod
    def tearDownClass(cls):
        """
        清理测试类 - 删除临时文件和目录
        """
        print("Tearing down TestVideoProcessor class...")
        if hasattr(cls, "temp_dir") and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    @classmethod
    def _create_test_image(cls):
        """
        创建测试用的图片文件
        """
        # 创建一个简单的测试图片 (100x100 蓝色)
        test_image = np.full((100, 100, 3), (255, 0, 0), dtype=np.uint8)  # 蓝色背景

        # 添加一些"水印"区域 (白色矩形)
        cv2.rectangle(test_image, (20, 20), (40, 40), (255, 255, 255), -1)
        cv2.rectangle(test_image, (60, 60), (80, 80), (255, 255, 255), -1)

        cls.test_image_path = os.path.join(cls.test_image_dir, "test_image.jpg")
        cv2.imwrite(cls.test_image_path, test_image)

        # 验证文件存在
        assert os.path.exists(cls.test_image_path), "Test image creation failed"

    @classmethod
    def _create_test_video(cls):
        """
        创建测试用的小视频文件 (10帧)
        """
        cls.test_video_path = os.path.join(cls.test_video_dir, "test_video.mp4")

        # 视频参数
        width, height = 100, 100
        fps = 10
        frames = 10

        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(cls.test_video_path, fourcc, fps, (width, height))

        # 生成测试帧
        for i in range(frames):
            # 创建渐变色帧
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            color_value = int((i / frames) * 255)
            frame[:, :] = (color_value, 100, 200)  # BGR格式

            # 添加帧号标记
            cv2.putText(frame, f"F{i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 添加"水印"区域
            cv2.rectangle(frame, (70, 70), (90, 90), (255, 255, 255), -1)

            out.write(frame)

        out.release()

        # 验证文件存在
        assert os.path.exists(cls.test_video_path), "Test video creation failed"

    def setUp(self):
        """
        每个测试方法前的设置
        """
        print(f"Setting up for test: {self._testMethodName}")
        # 加载配置
        self.config = ConfigManager.load_config()

        # 设置测试参数
        self.ai_params_test = {"auto_detect": True, "detection_sensitivity": 0.5, "user_mask": None}

        # 创建输出路径
        self.test_output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(self.test_output_dir, exist_ok=True)

    def tearDown(self):
        """
        每个测试方法后的清理
        """
        print(f"Tearing down after test: {self._testMethodName}")
        # 清理输出文件
        if hasattr(self, "test_output_dir") and os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                file_path = os.path.join(self.test_output_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

    def test_processor_initialization(self):
        """
        测试VideoProcessorThread初始化
        """
        output_path = os.path.join(self.test_output_dir, "test_init_output.jpg")

        processor = VideoProcessorThread(
            input_path=self.test_image_path,
            output_path=output_path,
            ai_params=self.ai_params_test,
            config=self.config,
        )

        # 测试基本属性
        self.assertEqual(processor.input_path, self.test_image_path)
        self.assertEqual(processor.output_path, output_path)
        self.assertEqual(processor.ai_params, self.ai_params_test)
        self.assertEqual(processor.config, self.config)
        self.assertTrue(processor._is_running)
        self.assertIsNone(processor.ai_handler)

        # 测试FFmpeg处理器初始化
        self.assertIsNotNone(processor.ffmpeg_processor)

        print("✅ Processor initialization test passed")

    @patch("app.core.video.video_processor.AIHandler")
    def test_image_processing_success(self, mock_ai_handler_class):
        """
        测试图像处理成功流程
        """
        # 设置AI处理器模拟
        mock_ai_handler = Mock()
        mock_ai_handler.load_models.return_value = True
        mock_ai_handler.process_frame.return_value = (
            np.zeros((100, 100, 3), dtype=np.uint8),  # 处理后的图像
            {"watermark_areas_found": 2, "processing_time": 0.1, "inpainting_method": "telea"},
        )
        mock_ai_handler_class.return_value = mock_ai_handler

        # 创建处理器
        output_path = os.path.join(self.test_output_dir, "test_image_output.jpg")
        processor = VideoProcessorThread(
            input_path=self.test_image_path,
            output_path=output_path,
            ai_params=self.ai_params_test,
            config=self.config,
        )

        # 设置信号接收器
        progress_values = []
        status_messages = []
        finished_paths = []
        error_messages = []

        processor.progress.connect(lambda p: progress_values.append(p))
        processor.status.connect(lambda s: status_messages.append(s))
        processor.finished.connect(lambda f: finished_paths.append(f))
        processor.error.connect(lambda e: error_messages.append(e))

        # 运行处理
        processor.run()

        # 验证结果
        self.assertTrue(len(progress_values) > 0, "Progress signals should be emitted")
        self.assertTrue(len(status_messages) > 0, "Status messages should be emitted")
        self.assertEqual(len(finished_paths), 1, "Should emit one finished signal")
        self.assertEqual(len(error_messages), 0, "Should not emit error signals")
        self.assertEqual(finished_paths[0], output_path)
        self.assertTrue(os.path.exists(output_path), "Output file should be created")

        # 验证AI处理器调用
        mock_ai_handler.load_models.assert_called_once()
        mock_ai_handler.process_frame.assert_called_once()

        print("✅ Image processing success test passed")

    @patch("app.core.video.video_processor.AIHandler")
    def test_video_processing_success(self, mock_ai_handler_class):
        """
        测试视频处理成功流程
        """
        # 设置AI处理器模拟
        mock_ai_handler = Mock()
        mock_ai_handler.load_models.return_value = True
        mock_ai_handler.process_frame.return_value = (
            np.zeros((100, 100, 3), dtype=np.uint8),  # 处理后的帧
            {"watermark_areas_found": 1, "processing_time": 0.05, "inpainting_method": "ns"},
        )
        mock_ai_handler_class.return_value = mock_ai_handler

        # 创建处理器
        output_path = os.path.join(self.test_output_dir, "test_video_output.mp4")
        processor = VideoProcessorThread(
            input_path=self.test_video_path,
            output_path=output_path,
            ai_params=self.ai_params_test,
            config=self.config,
        )

        # 设置信号接收器
        progress_values = []
        status_messages = []
        finished_paths = []
        preview_updates = []

        processor.progress.connect(lambda p: progress_values.append(p))
        processor.status.connect(lambda s: status_messages.append(s))
        processor.finished.connect(lambda f: finished_paths.append(f))
        processor.preview_update.connect(lambda f: preview_updates.append(f))

        # 运行处理
        processor.run()

        # 验证结果
        self.assertTrue(len(progress_values) > 0, "Progress signals should be emitted")
        self.assertTrue(len(status_messages) > 0, "Status messages should be emitted")
        self.assertEqual(len(finished_paths), 1, "Should emit one finished signal")
        self.assertTrue(len(preview_updates) > 0, "Preview updates should be emitted")

        # 验证AI处理器调用（应该为每一帧调用）
        mock_ai_handler.load_models.assert_called_once()
        self.assertTrue(
            mock_ai_handler.process_frame.call_count >= 10, "Should process at least 10 frames"
        )

        print("✅ Video processing success test passed")

    @patch("app.core.video.video_processor.AIHandler")
    def test_ai_handler_load_failure(self, mock_ai_handler_class):
        """
        测试AI处理器加载失败
        """
        # 设置AI处理器模拟 - 加载失败
        mock_ai_handler = Mock()
        mock_ai_handler.load_models.return_value = False
        mock_ai_handler_class.return_value = mock_ai_handler

        # 创建处理器
        output_path = os.path.join(self.test_output_dir, "test_failure_output.jpg")
        processor = VideoProcessorThread(
            input_path=self.test_image_path,
            output_path=output_path,
            ai_params=self.ai_params_test,
            config=self.config,
        )

        # 设置信号接收器
        error_messages = []
        processor.error.connect(lambda e: error_messages.append(e))

        # 运行处理
        processor.run()

        # 验证错误处理
        self.assertEqual(len(error_messages), 1, "Should emit one error signal")
        self.assertIn("无法加载 AI 模型", error_messages[0])
        self.assertFalse(os.path.exists(output_path), "Output file should not be created")

        print("✅ AI handler load failure test passed")

    def test_invalid_input_file(self):
        """
        测试无效输入文件处理
        """
        # 使用不存在的文件
        invalid_input = os.path.join(self.test_output_dir, "nonexistent.jpg")
        output_path = os.path.join(self.test_output_dir, "test_invalid_output.jpg")

        processor = VideoProcessorThread(
            input_path=invalid_input,
            output_path=output_path,
            ai_params=self.ai_params_test,
            config=self.config,
        )

        # 设置信号接收器
        error_messages = []
        processor.error.connect(lambda e: error_messages.append(e))

        # 运行处理
        processor.run()

        # 验证错误处理
        self.assertTrue(len(error_messages) > 0, "Should emit error signals")

        print("✅ Invalid input file test passed")

    def test_stop_functionality(self):
        """
        测试停止功能
        """
        output_path = os.path.join(self.test_output_dir, "test_stop_output.jpg")
        processor = VideoProcessorThread(
            input_path=self.test_image_path,
            output_path=output_path,
            ai_params=self.ai_params_test,
            config=self.config,
        )

        # 测试停止前状态
        self.assertTrue(processor._is_running)

        # 调用停止
        processor.stop()

        # 测试停止后状态
        self.assertFalse(processor._is_running)

        print("✅ Stop functionality test passed")

    def test_unsupported_file_format(self):
        """
        测试不支持的文件格式
        """
        # 创建一个.txt文件作为不支持的格式
        unsupported_file = os.path.join(self.test_output_dir, "test.txt")
        with open(unsupported_file, "w") as f:
            f.write("test content")

        output_path = os.path.join(self.test_output_dir, "test_unsupported_output.txt")
        processor = VideoProcessorThread(
            input_path=unsupported_file,
            output_path=output_path,
            ai_params=self.ai_params_test,
            config=self.config,
        )

        # 设置信号接收器
        error_messages = []
        processor.error.connect(lambda e: error_messages.append(e))

        # 运行处理
        processor.run()

        # 验证错误处理
        self.assertTrue(len(error_messages) > 0, "Should emit error for unsupported format")
        self.assertTrue(any("不支持的文件格式" in msg for msg in error_messages))

        print("✅ Unsupported file format test passed")


if __name__ == "__main__":
    unittest.main()
