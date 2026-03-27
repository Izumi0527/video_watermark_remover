#!/usr/bin/env python3
"""
输出策略纯函数回归测试。
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


def test_resolve_output_path_applies_suffix_timestamp_and_format_for_image() -> None:
    from app.core.video.output_strategy import resolve_output_path

    output_path = resolve_output_path(
        "C:/tmp/sample.png",
        {
            "output_format": "jpg",
            "add_suffix": True,
            "add_timestamp": True,
        },
        generated_at=datetime(2026, 3, 27, 12, 34, 56),
    )

    assert _normalize(output_path) == "C:/tmp/sample_processed_20260327_123456.jpg"


def test_resolve_output_path_keeps_video_extension_when_requested_format_is_image_only() -> None:
    from app.core.video.output_strategy import resolve_output_path

    output_path = resolve_output_path(
        "C:/tmp/clip.mp4",
        {
            "output_format": "png",
            "add_suffix": True,
            "add_timestamp": False,
        },
    )

    assert _normalize(output_path) == "C:/tmp/clip_processed.mp4"


def test_resolve_output_path_avoids_overwriting_input_when_suffix_and_timestamp_disabled() -> None:
    from app.core.video.output_strategy import resolve_output_path

    output_path = resolve_output_path(
        "C:/tmp/clip.mp4",
        {
            "output_format": "keep",
            "add_suffix": False,
            "add_timestamp": False,
        },
    )

    assert _normalize(output_path) == "C:/tmp/clip_processed.mp4"


def test_build_image_write_options_maps_quality_for_jpg_and_png() -> None:
    from app.core.video.output_strategy import build_image_write_options

    jpg_options = build_image_write_options(
        "C:/tmp/sample.jpg",
        {"compression_quality": 91},
    )
    png_options = build_image_write_options(
        "C:/tmp/sample.png",
        {"compression_quality": 91},
    )

    assert jpg_options == ("jpeg_quality", 91)
    assert png_options == ("png_compression", 1)


def test_resolve_ffmpeg_output_codecs_tracks_container_suffix() -> None:
    from app.core.video.output_strategy import resolve_ffmpeg_output_codecs

    assert resolve_ffmpeg_output_codecs("C:/tmp/out.mp4") == {
        "video_codec": "libx264",
        "audio_codec": "aac",
    }
    assert resolve_ffmpeg_output_codecs("C:/tmp/out.avi") == {
        "video_codec": "mpeg4",
        "audio_codec": "libmp3lame",
    }


def test_output_strategy_ignores_legacy_output_fields() -> None:
    from app.core.video.output_strategy import build_image_write_options, resolve_output_path

    output_path = resolve_output_path(
        "C:/tmp/clip.mp4",
        {
            "add_processed_suffix": False,
            "output_quality": "low",
        },
    )
    image_write_options = build_image_write_options(
        "C:/tmp/frame.jpg",
        {
            "output_quality": "low",
        },
    )

    assert _normalize(output_path) == "C:/tmp/clip_processed.mp4"
    assert image_write_options == ("jpeg_quality", 85)


def test_should_preserve_audio_only_reads_current_field() -> None:
    from app.core.video.output_strategy import should_preserve_audio

    assert should_preserve_audio({"preserve_audio": False}) is False
    assert should_preserve_audio({"processing": {"preserve_audio": False}}) is True


def test_runtime_output_whitelist_covers_output_config_fields() -> None:
    from app.config.advanced_params import ResolvedOutputConfig
    from app.core.video import output_strategy

    expected_fields = {field.name for field in fields(ResolvedOutputConfig)}
    assert output_strategy._RUNTIME_OUTPUT_PARAM_KEYS == expected_fields
