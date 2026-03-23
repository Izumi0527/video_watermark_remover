import importlib.util
import sys
import types
from configparser import ConfigParser
from pathlib import Path


def _install_pyqt6_stub() -> None:
    if importlib.util.find_spec("PyQt6") is not None:
        return

    pyqt6 = types.ModuleType("PyQt6")
    qtcore = types.ModuleType("PyQt6.QtCore")

    class _DummySignal:
        def __init__(self, *_args, **_kwargs):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in self._callbacks:
                callback(*args, **kwargs)

    class _DummyQThread:
        def __init__(self, *_args, **_kwargs):
            pass

        def isRunning(self):
            return False

        def wait(self, *_args, **_kwargs):
            return True

        def start(self):
            return None

    class _DummyTimer:
        def __init__(self, *_args, **_kwargs):
            self.timeout = _DummySignal()

        def start(self, *_args, **_kwargs):
            return None

        def stop(self):
            return None

    qtcore.QThread = _DummyQThread
    qtcore.QTimer = _DummyTimer
    qtcore.pyqtSignal = lambda *_args, **_kwargs: _DummySignal()

    pyqt6.QtCore = qtcore
    sys.modules["PyQt6"] = pyqt6
    sys.modules["PyQt6.QtCore"] = qtcore


def _install_cv2_stub() -> None:
    if importlib.util.find_spec("cv2") is not None:
        return

    sys.modules["cv2"] = types.ModuleType("cv2")


def _install_numpy_stub() -> None:
    if importlib.util.find_spec("numpy") is not None:
        return

    numpy_module = types.ModuleType("numpy")
    numpy_typing_module = types.ModuleType("numpy.typing")

    class _DummyNDArray:
        def __class_getitem__(cls, _item):
            return object

    numpy_module.uint8 = int
    numpy_typing_module.NDArray = _DummyNDArray
    sys.modules["numpy"] = numpy_module
    sys.modules["numpy.typing"] = numpy_typing_module


def _install_runtime_stubs() -> None:
    ai_handler_module = types.ModuleType("app.core.ai.ai_handler")

    class _DummyAIHandler:
        def __init__(self, *_args, **_kwargs):
            self.device_preference = "auto"

        def load_models(self):
            return True

        def update_device(self, *_args, **_kwargs):
            return None

        def process_frame(self, frame, *_args, **_kwargs):
            return frame, {"watermark_areas_found": 0, "processing_time": 0.0}

    ai_handler_module.AIHandler = _DummyAIHandler
    sys.modules["app.core.ai.ai_handler"] = ai_handler_module

    ffmpeg_module = types.ModuleType("app.core.audio.ffmpeg_audio_processor")

    class _DummyFFmpegAudioProcessor:
        def __init__(self, *_args, **_kwargs):
            pass

        def is_available(self):
            return False

        def process_video_with_audio_preservation(self, **_kwargs):
            return True

    ffmpeg_module.FFmpegAudioProcessor = _DummyFFmpegAudioProcessor
    sys.modules["app.core.audio.ffmpeg_audio_processor"] = ffmpeg_module


_install_pyqt6_stub()
_install_cv2_stub()
_install_numpy_stub()
_install_runtime_stubs()


COMPAT_LAYER_FILES = [
    "src/app/core/video/audio_tasks.py",
    "src/app/core/video/backpressure.py",
    "src/app/core/video/chunk_worker.py",
    "src/app/core/video/frame_processor.py",
    "src/app/core/video/frame_reader.py",
    "src/app/core/video/frame_writer.py",
    "src/app/core/video/multiprocess_processor.py",
    "src/app/core/video/path_utils.py",
    "src/app/core/video/pipeline_processor.py",
    "src/app/core/video/single_process_processor.py",
    "src/app/core/video/video_processor.py",
]


def test_new_video_subpackages_expose_core_entries() -> None:
    from app.core.video.modes.multiprocess import process_video_multiprocess
    from app.core.video.modes.pipeline import process_video_pipeline
    from app.core.video.modes.single_process import process_video_singleprocess
    from app.core.video.thread import VideoProcessorThread
    from app.core.video.utils.path import build_temp_path
    from app.core.video.workers.audio import async_audio_extractor
    from app.core.video.workers.chunk import process_video_chunk
    from app.core.video.workers.frame_processor import frame_processor_worker
    from app.core.video.workers.frame_reader import frame_reader_worker
    from app.core.video.workers.frame_writer import frame_writer_worker

    assert VideoProcessorThread.__name__ == "VideoProcessorThread"
    assert process_video_singleprocess.__name__ == "process_video_singleprocess"
    assert process_video_multiprocess.__name__ == "process_video_multiprocess"
    assert process_video_pipeline.__name__ == "process_video_pipeline"
    assert async_audio_extractor.__name__ == "async_audio_extractor"
    assert process_video_chunk.__name__ == "process_video_chunk"
    assert frame_reader_worker.__name__ == "frame_reader_worker"
    assert frame_processor_worker.__name__ == "frame_processor_worker"
    assert frame_writer_worker.__name__ == "frame_writer_worker"
    assert build_temp_path("demo.mp4", "temp_video").endswith("demo__temp_video.mp4")


def test_video_entrypoints_are_consistent() -> None:
    from app.core.video import VideoProcessorThread as package_thread
    from app.core.video.modes.multiprocess import process_video_multiprocess
    from app.core.video.modes.pipeline import process_video_pipeline
    from app.core.video.modes.single_process import process_video_singleprocess
    from app.core.video.thread import VideoProcessorThread as thread_thread
    from app.core.video.utils.path import build_temp_path

    assert package_thread is thread_thread
    assert process_video_singleprocess.__name__ == "process_video_singleprocess"
    assert process_video_multiprocess.__name__ == "process_video_multiprocess"
    assert process_video_pipeline.__name__ == "process_video_pipeline"
    assert build_temp_path("demo.mp4", "temp_video").endswith("demo__temp_video.mp4")


def test_video_processor_thread_injects_inpainting_model_path_from_config() -> None:
    from app.core.video.thread import VideoProcessorThread

    config = ConfigParser()
    config["Models"] = {"inpainting_model_path": "models/unet-stage1.pth"}

    processor = VideoProcessorThread(
        input_path="demo.mp4",
        output_path="out.mp4",
        ai_params={"auto_detect": True},
        config=config,
    )

    assert processor.ai_params["inpainting_model_path"] == "models/unet-stage1.pth"


def test_ai_handler_refresh_check_detects_new_inpainting_model_path() -> None:
    from app.core.video import thread as video_thread

    existing_handler = types.SimpleNamespace(
        ai_params={"auto_detect": True, "device": "auto"},
    )

    assert (
        video_thread._ai_handler_needs_refresh(
            existing_handler,
            {
                "auto_detect": True,
                "device": "auto",
                "inpainting_model_path": "models/unet-stage1.pth",
            },
        )
        is True
    )


def test_legacy_flat_compat_layers_are_removed() -> None:
    missing_compat_files = [
        relative_path for relative_path in COMPAT_LAYER_FILES if not Path(relative_path).exists()
    ]
    assert len(missing_compat_files) == len(COMPAT_LAYER_FILES), "以下旧兼容层文件仍未删除：" + ", ".join(
        sorted(set(COMPAT_LAYER_FILES) - set(missing_compat_files))
    )
