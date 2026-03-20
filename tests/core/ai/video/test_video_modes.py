import os
import shutil
import uuid
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from app.core.video import thread as video_thread
from app.core.video.modes import multiprocess as multiprocess_mode
from app.core.video.modes import pipeline as pipeline_mode
from app.core.video.workers import chunk as chunk_worker
from app.core.video.workers import frame_processor

RUNTIME_ROOT = Path(__file__).resolve().parents[4] / ".cache" / "tests" / "core-ai-video-modes"


def create_runtime_dir() -> Path:
    """创建项目内测试运行目录，避免 pytest tmp_path 清理权限波动。"""
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    runtime_dir = RUNTIME_ROOT / f"video_modes_{uuid.uuid4().hex}"
    runtime_dir.mkdir()
    return runtime_dir


class DummyAIHandler:
    """轻量级AI处理器，直接回传输入帧。"""

    def __init__(self, *_, **__):
        pass

    def load_models(self):
        return True

    def process_frame(self, frame, params=None):
        return frame.copy(), {"watermark_areas_found": 1, "processing_time": 0.0}


class DummyFFmpegAudioProcessor:
    """关闭音频合并，避免外部依赖。"""

    def __init__(self, *_args, **_kwargs):
        pass

    def is_available(self):
        return False

    def process_video_with_audio_preservation(self, **_kwargs):
        return True


class DummyFuture:
    def __init__(self, result):
        self._result = result

    def result(self, timeout=None):
        return self._result


class InlineExecutor:
    """同步执行器，用于替代 ProcessPoolExecutor，避免多进程开销。"""

    def __init__(self, *_, **__):
        pass

    def submit(self, fn, *args, **kwargs):
        return DummyFuture(fn(*args, **kwargs))

    def shutdown(self, wait=True):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


class DummySignal:
    def __init__(self):
        self._callback = None

    def connect(self, fn):
        self._callback = fn


class DummyTimer:
    """替换 QTimer，避免 Qt 事件循环依赖。"""

    def __init__(self):
        self.timeout = DummySignal()

    def start(self, *_args, **_kwargs):
        pass

    def stop(self):
        pass


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # 替换 AI 处理器和 FFmpeg 处理器
    monkeypatch.setattr(video_thread, "AIHandler", DummyAIHandler)
    monkeypatch.setattr(chunk_worker, "AIHandler", DummyAIHandler)
    monkeypatch.setattr(frame_processor, "AIHandler", DummyAIHandler)
    monkeypatch.setattr(video_thread, "FFmpegAudioProcessor", DummyFFmpegAudioProcessor)

    # 替换 QTimer
    monkeypatch.setattr(video_thread, "QTimer", DummyTimer)
    monkeypatch.setattr(multiprocess_mode, "QTimer", DummyTimer)
    monkeypatch.setattr(pipeline_mode, "QTimer", DummyTimer)

    # 替换多进程执行器为同步执行
    monkeypatch.setattr(multiprocess_mode, "ProcessPoolExecutor", InlineExecutor)
    monkeypatch.setattr(pipeline_mode, "ProcessPoolExecutor", InlineExecutor)

    yield


@pytest.fixture
def media():
    """创建极简测试图像与视频。"""
    runtime_dir = create_runtime_dir()
    img_path = runtime_dir / "test_image.jpg"
    vid_path = runtime_dir / "test_video.mp4"
    out_dir = runtime_dir / "outputs"
    out_dir.mkdir(exist_ok=True)

    # 生成测试图片
    img = np.full((32, 32, 3), 128, dtype=np.uint8)
    cv2.rectangle(img, (8, 8), (16, 16), (255, 255, 255), -1)
    cv2.imwrite(str(img_path), img)

    # 生成短视频（5帧）
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(vid_path), fourcc, 5, (32, 32))
    for i in range(5):
        frame = np.full((32, 32, 3), i * 20, dtype=np.uint8)
        cv2.putText(frame, f"F{i}", (2, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        writer.write(frame)
    writer.release()

    yield {"image": img_path, "video": vid_path, "out_dir": out_dir}
    shutil.rmtree(runtime_dir, ignore_errors=True)


def test_image_processing(media):
    """验证图片处理流程能输出文件。"""
    output_path = media["out_dir"] / "image_out.jpg"
    processor = video_thread.VideoProcessorThread(
        input_path=str(media["image"]),
        output_path=str(output_path),
        ai_params={},
        config=None,
        preloaded_ai_handler=DummyAIHandler(),
        enable_multiprocess=False,
    )
    processor._process_image()
    assert output_path.exists()


def test_video_single_process(media):
    """验证单进程视频处理流程。"""
    output_path = media["out_dir"] / "video_single.mp4"
    processor = video_thread.VideoProcessorThread(
        input_path=str(media["video"]),
        output_path=str(output_path),
        ai_params={},
        config=None,
        preloaded_ai_handler=DummyAIHandler(),
        enable_multiprocess=False,
    )
    processor._process_video_singleprocess()
    assert output_path.exists()


def test_video_multiprocess_chunk(media):
    """验证分块多进程模式（同步执行替代）。"""
    output_path = media["out_dir"] / "video_multiprocess.mp4"
    processor = video_thread.VideoProcessorThread(
        input_path=str(media["video"]),
        output_path=str(output_path),
        ai_params={},
        config=None,
        preloaded_ai_handler=DummyAIHandler(),
        enable_multiprocess=True,
        num_processes=2,
        use_pipeline=False,
    )
    processor._process_video_multiprocess()
    assert output_path.exists()


def test_video_pipeline(media):
    """验证流水线模式（同步执行替代）。"""
    output_path = media["out_dir"] / "video_pipeline.mp4"
    processor = video_thread.VideoProcessorThread(
        input_path=str(media["video"]),
        output_path=str(output_path),
        ai_params={},
        config=None,
        preloaded_ai_handler=DummyAIHandler(),
        enable_multiprocess=True,
        num_processes=2,
        use_pipeline=True,
    )
    processor._process_video_pipeline()
    assert output_path.exists()
