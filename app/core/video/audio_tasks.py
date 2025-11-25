import logging
import subprocess
import threading


def async_audio_extractor(
    video_path: str,
    audio_output_path: str,
    completion_event: threading.Event,
    stop_event: threading.Event,
    logger: logging.Logger,
) -> bool:
    """
    异步提取音频到临时文件 (Phase 4 Stage 2.3).

    Args:
        video_path: 输入视频路径
        audio_output_path: 临时音频输出路径
        completion_event: 完成事件(成功时set)
        stop_event: 停止事件(用户取消时set)
        logger: 日志记录器

    Returns:
        bool: 是否成功提取音频
    """
    try:
        logger.info(f"Starting async audio extraction: {video_path}")

        ffmpeg_cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-vn",
            "-acodec",
            "copy",
            audio_output_path,
            "-y",
        ]

        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if stop_event.is_set():
            logger.info("Audio extraction cancelled by user")
            return False

        if result.returncode != 0:
            logger.warning(f"Audio extraction failed: {result.stderr}")
            return False

        completion_event.set()
        logger.info(f"Audio extraction completed: {audio_output_path}")
        return True

    except subprocess.TimeoutExpired:
        logger.warning("Audio extraction timeout (>60s)")
        return False

    except Exception as e:  # noqa: BLE001
        logger.error(f"Audio extraction error: {e}")
        return False
