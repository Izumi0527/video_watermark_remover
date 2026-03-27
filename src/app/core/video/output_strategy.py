#!/usr/bin/env python3
"""
输出路径与编码策略。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from ...config.advanced_params import AdvancedParamsSnapshot

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
}
_IMAGE_OUTPUT_SUFFIXES = {
    "jpg": ".jpg",
    "png": ".png",
    "bmp": ".bmp",
    "tiff": ".tiff",
}
_VIDEO_WRITER_CODECS = {
    ".avi": ("XVID", "MJPG", "mp4v"),
    ".webm": ("VP80", "XVID", "mp4v"),
    ".mov": ("mp4v", "avc1", "XVID"),
    ".m4v": ("mp4v", "avc1", "XVID"),
    ".mkv": ("mp4v", "XVID", "MJPG"),
}
_DEFAULT_VIDEO_CODECS = ("mp4v", "XVID", "MJPG")
_FFMPEG_OUTPUT_CODECS = {
    ".avi": {"video_codec": "mpeg4", "audio_codec": "libmp3lame"},
    ".webm": {"video_codec": "libvpx-vp9", "audio_codec": "libopus"},
}
_DEFAULT_FFMPEG_OUTPUT_CODECS = {"video_codec": "libx264", "audio_codec": "aac"}
_IMAGE_WRITE_OPTION_NAMES = {
    "jpeg_quality": "IMWRITE_JPEG_QUALITY",
    "png_compression": "IMWRITE_PNG_COMPRESSION",
}


_RUNTIME_OUTPUT_PARAM_KEYS = {
    "output_format",
    "compression_quality",
    "add_suffix",
    "add_timestamp",
    "preserve_audio",
}


def _resolve_snapshot(ai_params: Mapping[str, Any] | None = None) -> AdvancedParamsSnapshot:
    normalized_ai_params: dict[str, Any] = {}
    if ai_params:
        normalized_ai_params = {
            key: value for key, value in ai_params.items() if key in _RUNTIME_OUTPUT_PARAM_KEYS
        }
    return AdvancedParamsSnapshot.from_dict(normalized_ai_params)


def _is_image_suffix(suffix: str) -> bool:
    return suffix.lower() in _IMAGE_EXTENSIONS


def _is_video_suffix(suffix: str) -> bool:
    return suffix.lower() in _VIDEO_EXTENSIONS


def resolve_output_path(
    input_path: str,
    ai_params: Mapping[str, Any] | None = None,
    *,
    generated_at: datetime | None = None,
) -> str:
    source_path = Path(str(input_path))
    snapshot = _resolve_snapshot(ai_params)
    output_config = snapshot.resolve_output_config()

    target_suffix = source_path.suffix.lower()
    if _is_image_suffix(target_suffix) and output_config.output_format != "keep":
        target_suffix = _IMAGE_OUTPUT_SUFFIXES.get(output_config.output_format, target_suffix)

    stem = source_path.stem
    if output_config.add_suffix:
        stem = f"{stem}_processed"
    if output_config.add_timestamp:
        current_time = generated_at or datetime.now()
        stem = f"{stem}_{current_time.strftime('%Y%m%d_%H%M%S')}"

    resolved_suffix = target_suffix or source_path.suffix
    resolved_path = source_path.with_name(f"{stem}{resolved_suffix}")
    if str(resolved_path).lower() == str(source_path).lower():
        resolved_path = source_path.with_name(f"{source_path.stem}_processed{resolved_suffix}")
    return str(resolved_path)


def build_image_write_options(
    output_path: str,
    ai_params: Mapping[str, Any] | None = None,
) -> tuple[str, int] | None:
    snapshot = _resolve_snapshot(ai_params)
    output_config = snapshot.resolve_output_config()
    suffix = Path(str(output_path)).suffix.lower()

    if suffix in {".jpg", ".jpeg"}:
        return ("jpeg_quality", output_config.compression_quality)
    if suffix == ".png":
        compression = int(round((100 - output_config.compression_quality) * 9 / 99))
        return ("png_compression", max(0, min(9, compression)))
    return None


def build_image_write_params(
    output_path: str,
    ai_params: Mapping[str, Any] | None = None,
    *,
    cv2_module: Any | None = None,
) -> list[int]:
    option = build_image_write_options(output_path, ai_params)
    if option is None:
        return []

    if cv2_module is None:
        import cv2 as imported_cv2_module

        cv2_module = imported_cv2_module

    option_name, value = option
    constant_name = _IMAGE_WRITE_OPTION_NAMES[option_name]
    return [getattr(cv2_module, constant_name), value]


def resolve_video_writer_codecs(output_path: str) -> tuple[str, ...]:
    suffix = Path(str(output_path)).suffix.lower()
    return _VIDEO_WRITER_CODECS.get(suffix, _DEFAULT_VIDEO_CODECS)


def create_video_writer(
    output_path: str,
    fps: float,
    frame_size: tuple[int, int],
    *,
    cv2_module: Any | None = None,
):
    if cv2_module is None:
        import cv2 as imported_cv2_module

        cv2_module = imported_cv2_module
    real_cv2_module: Any = cv2_module

    last_writer = None
    for codec in resolve_video_writer_codecs(output_path):
        writer = real_cv2_module.VideoWriter(
            output_path,
            real_cv2_module.VideoWriter_fourcc(*codec),
            fps,
            frame_size,
        )
        last_writer = writer
        if writer.isOpened():
            return writer, codec
        if hasattr(writer, "release"):
            writer.release()
    return last_writer, None


def resolve_ffmpeg_output_codecs(output_path: str) -> dict[str, str]:
    suffix = Path(str(output_path)).suffix.lower()
    return dict(_FFMPEG_OUTPUT_CODECS.get(suffix, _DEFAULT_FFMPEG_OUTPUT_CODECS))


def resolve_ffmpeg_reencode_args(output_path: str) -> list[str]:
    suffix = Path(str(output_path)).suffix.lower()
    if suffix == ".avi":
        return ["-q:v", "5"]
    if suffix == ".webm":
        return ["-b:v", "0", "-crf", "30"]
    return ["-preset", "medium", "-crf", "23"]


def should_preserve_audio(ai_params: Mapping[str, Any] | None = None) -> bool:
    snapshot = _resolve_snapshot(ai_params)
    return snapshot.resolve_output_config().preserve_audio


__all__ = [
    "build_image_write_options",
    "build_image_write_params",
    "create_video_writer",
    "resolve_ffmpeg_output_codecs",
    "resolve_ffmpeg_reencode_args",
    "resolve_output_path",
    "resolve_video_writer_codecs",
    "should_preserve_audio",
]
