#!/usr/bin/env python3
"""
FFmpeg 回退命令参数策略测试。
"""

from __future__ import annotations

from types import SimpleNamespace


def _create_processor():
    from app.core.audio.ffmpeg_audio_processor import FFmpegAudioProcessor

    processor = FFmpegAudioProcessor()
    processor.logger = SimpleNamespace(
        info=lambda *_args, **_kwargs: None,
        debug=lambda *_args, **_kwargs: None,
        warning=lambda *_args, **_kwargs: None,
        error=lambda *_args, **_kwargs: None,
    )
    processor.detector = SimpleNamespace(
        is_available=lambda: True,
        get_ffmpeg_path=lambda: "ffmpeg",
    )
    return processor


def test_fallback_copy_avi_uses_codec_specific_flags_without_x264_params(monkeypatch) -> None:
    from app.core.audio import ffmpeg_audio_processor

    captured = {}

    def _fake_run(cmd, **_kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(ffmpeg_audio_processor.subprocess, "run", _fake_run)

    processor = _create_processor()
    assert processor._fallback_copy("C:/tmp/in.mp4", "C:/tmp/out.avi", "unit-test")

    cmd = captured["cmd"]
    assert "-c:v" in cmd
    assert "mpeg4" in cmd
    assert "-preset" not in cmd
    assert "-crf" not in cmd
    assert "-q:v" in cmd


def test_fallback_copy_webm_uses_vp9_style_flags(monkeypatch) -> None:
    from app.core.audio import ffmpeg_audio_processor

    captured = {}

    def _fake_run(cmd, **_kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(ffmpeg_audio_processor.subprocess, "run", _fake_run)

    processor = _create_processor()
    assert processor._fallback_copy("C:/tmp/in.mp4", "C:/tmp/out.webm", "unit-test")

    cmd = captured["cmd"]
    assert "-c:v" in cmd
    assert "libvpx-vp9" in cmd
    assert "-b:v" in cmd
    assert "-crf" in cmd
    assert "-preset" not in cmd
