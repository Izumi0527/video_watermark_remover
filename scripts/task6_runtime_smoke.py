#!/usr/bin/env python3
# mypy: ignore-errors
"""Task 6 运行态 smoke 脚本。"""

from __future__ import annotations

import argparse
import os
import queue
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import Future
from pathlib import Path
from typing import Any


class DummyAIHandler:
    """轻量级 AI 处理器：不加载真实模型，直接回传输入帧。"""

    def __init__(self, *_args, **_kwargs) -> None:
        self.device_preference = "cpu"

    def load_models(self) -> bool:
        return True

    def update_device(self, device: str) -> None:
        self.device_preference = device

    def process_frame(self, frame, _params=None):
        return frame.copy(), {"watermark_areas_found": 0, "processing_time": 0.0}


class DummyFFmpegAudioProcessor:
    """关闭 FFmpeg 依赖，避免外部环境影响 smoke。"""

    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def is_available(self) -> bool:
        return False

    def process_video_with_audio_preservation(self, **_kwargs) -> bool:
        return True


class DummySignal:
    def __init__(self) -> None:
        self._callback = None

    def connect(self, callback) -> None:
        self._callback = callback

    def emit(self, *args, **kwargs) -> None:
        if self._callback is not None:
            self._callback(*args, **kwargs)


class DummyTimer:
    """替代 QTimer，避免依赖 Qt 事件循环驱动轮询。"""

    def __init__(self) -> None:
        self.timeout = DummySignal()

    def start(self, *_args, **_kwargs) -> None:
        return None

    def stop(self) -> None:
        return None


class InlineExecutor:
    """同步执行器，替代 ProcessPoolExecutor。"""

    def __init__(self, *_, initializer=None, initargs=(), **__) -> None:
        if initializer is not None:
            initializer(*initargs)

    def submit(self, fn, *args, **kwargs) -> Future:
        future: Future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as exc:  # noqa: BLE001
            future.set_exception(exc)
        return future

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:  # noqa: ARG002
        return None

    def __enter__(self) -> "InlineExecutor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        self.shutdown()


class DummyManager:
    """替代 multiprocessing.Manager，规避 Windows 权限波动。"""

    def Queue(self, maxsize: int = 0):  # noqa: N802
        return queue.Queue(maxsize=maxsize)

    def Event(self):  # noqa: N802
        return threading.Event()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_import_path(root: Path) -> None:
    src_dir = root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def create_runtime_dir(root: Path) -> Path:
    runtime_root = root / ".cache" / "task6-smoke"
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_dir = runtime_root / f"run_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}"
    runtime_dir.mkdir()
    return runtime_dir


def generate_media(runtime_dir: Path) -> dict[str, Path]:
    import cv2
    import numpy as np

    out_dir = runtime_dir / "outputs"
    out_dir.mkdir(exist_ok=True)

    image_path = runtime_dir / "sample_image.jpg"
    video_path = runtime_dir / "sample_video.mp4"

    image = np.full((32, 32, 3), 128, dtype=np.uint8)
    cv2.rectangle(image, (8, 8), (16, 16), (255, 255, 255), -1)
    cv2.imwrite(str(image_path), image)

    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 5, (32, 32))
    for index in range(5):
        frame = np.full((32, 32, 3), index * 20, dtype=np.uint8)
        cv2.putText(frame, f"F{index}", (2, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        writer.write(frame)
    writer.release()

    return {
        "image": image_path,
        "video": video_path,
        "out_dir": out_dir,
    }


def patch_dependencies() -> None:
    from app.core.video import thread as video_thread
    from app.core.video.modes import multiprocess as multiprocess_mode
    from app.core.video.modes import pipeline as pipeline_mode
    from app.core.video.workers import chunk as chunk_worker
    from app.core.video.workers import frame_processor

    video_thread.AIHandler = DummyAIHandler
    video_thread.FFmpegAudioProcessor = DummyFFmpegAudioProcessor
    video_thread.QTimer = DummyTimer
    chunk_worker.AIHandler = DummyAIHandler
    frame_processor.AIHandler = DummyAIHandler
    multiprocess_mode.QTimer = DummyTimer
    pipeline_mode.QTimer = DummyTimer
    multiprocess_mode.ProcessPoolExecutor = InlineExecutor
    pipeline_mode.ProcessPoolExecutor = InlineExecutor
    multiprocess_mode.multiprocessing.Manager = DummyManager
    pipeline_mode.multiprocessing.Manager = DummyManager


def run_gui_startup() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from app.config.config_manager import ConfigManager
    from app.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    config = ConfigManager.load_config()
    window = MainWindow(config)
    window.show()
    app.processEvents()
    window.close()
    app.processEvents()


def run_processor(name: str, input_path: Path, output_path: Path, **kwargs: Any) -> None:
    from app.core.video.thread import VideoProcessorThread

    processor = VideoProcessorThread(
        input_path=str(input_path),
        output_path=str(output_path),
        ai_params={},
        config=None,
        preloaded_ai_handler=DummyAIHandler(),
        **kwargs,
    )

    if name == "image":
        processor._process_image()
    elif name == "single":
        processor._process_video_singleprocess()
    elif name == "multi":
        processor._process_video_multiprocess()
    elif name == "pipeline":
        processor._process_video_pipeline()
    else:
        raise ValueError(f"未知 smoke 模式: {name}")

    if not output_path.exists():
        raise RuntimeError(f"{name} smoke 未生成输出: {output_path}")


def run_batch(image_path: Path, video_path: Path, out_dir: Path) -> list[tuple[int, str, str]]:
    from app.ui.widgets.batch.batch_processor_thread import BatchProcessorThread, ProcessingStatus

    queue_items = [
        {"input_path": str(image_path), "output_path": str(out_dir / "batch_image.jpg")},
        {"input_path": str(video_path), "output_path": str(out_dir / "batch_video.mp4")},
    ]
    batch = BatchProcessorThread(
        queue=queue_items,
        ai_params={},
        config=None,
        preloaded_ai_handler=DummyAIHandler(),
        max_concurrent_files=2,
        auto_retry_failed=False,
    )

    batch_status: list[tuple[int, str, str]] = []
    batch.file_completed.connect(
        lambda index, path, status: batch_status.append(
            (index, path, getattr(status, "value", str(status)))
        )
    )
    batch.run()

    if len(batch_status) != 2:
        raise RuntimeError(f"批处理完成数异常: {batch_status}")
    if any(item[2] != ProcessingStatus.COMPLETED.value for item in batch_status):
        raise RuntimeError(f"批处理状态异常: {batch_status}")

    return batch_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Task 6 运行态 smoke 脚本")
    parser.add_argument("--keep", action="store_true", help="保留运行目录，便于人工核对输出文件")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = project_root()
    ensure_import_path(root)
    patch_dependencies()

    runtime_dir = create_runtime_dir(root)

    try:
        media = generate_media(runtime_dir)
        run_gui_startup()
        run_processor(
            "image",
            media["image"],
            media["out_dir"] / "image_out.jpg",
            enable_multiprocess=False,
        )
        run_processor(
            "single",
            media["video"],
            media["out_dir"] / "video_single.mp4",
            enable_multiprocess=False,
        )
        run_processor(
            "multi",
            media["video"],
            media["out_dir"] / "video_multi.mp4",
            enable_multiprocess=True,
            num_processes=2,
            use_pipeline=False,
        )
        run_processor(
            "pipeline",
            media["video"],
            media["out_dir"] / "video_pipeline.mp4",
            enable_multiprocess=True,
            num_processes=2,
            use_pipeline=True,
        )
        batch_status = run_batch(media["image"], media["video"], media["out_dir"])

        summary = {
            "gui_startup": True,
            "image_single_file": True,
            "video_single_process": True,
            "video_multiprocess": True,
            "video_pipeline": True,
            "batch_processing": True,
            "runtime_dir": str(runtime_dir),
            "batch_status": batch_status,
        }
        print(summary)

        if not args.keep:
            shutil.rmtree(runtime_dir, ignore_errors=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        print({"success": False, "runtime_dir": str(runtime_dir), "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
