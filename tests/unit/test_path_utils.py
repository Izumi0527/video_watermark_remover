from pathlib import Path

from app.core.video.path_utils import build_temp_path


def test_build_temp_path_keeps_directory_with_dots() -> None:
    output_path = "C:/tmp/v1.2.3/foo.mp4"
    temp_path = build_temp_path(output_path, "temp_video")
    assert Path(temp_path).parent.as_posix() == Path(output_path).parent.as_posix()
    assert Path(temp_path).name == "foo__temp_video.mp4"


def test_build_temp_path_keeps_filename_with_multiple_dots() -> None:
    output_path = "C:/tmp/my.video.sample.mp4"
    temp_path = build_temp_path(output_path, "temp_merged")
    assert Path(temp_path).parent.as_posix() == Path(output_path).parent.as_posix()
    assert Path(temp_path).name == "my.video.sample__temp_merged.mp4"


def test_build_temp_path_without_suffix() -> None:
    output_path = "C:/tmp/output"
    temp_path = build_temp_path(output_path, "temp_pipeline")
    assert Path(temp_path).name == "output__temp_pipeline"
