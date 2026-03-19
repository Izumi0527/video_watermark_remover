import importlib.util
import sys
import types


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
_install_runtime_stubs()


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
