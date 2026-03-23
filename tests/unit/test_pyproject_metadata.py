from __future__ import annotations

import re
import tomllib
from pathlib import Path


def _load_project_metadata() -> dict:
    pyproject_path = Path("pyproject.toml")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return data["project"]


def test_project_license_uses_spdx_string() -> None:
    project = _load_project_metadata()

    assert project["license"] == "MIT"


def test_project_classifiers_do_not_use_deprecated_license_classifier() -> None:
    project = _load_project_metadata()

    assert "License :: OSI Approved :: MIT License" not in project["classifiers"]


def test_project_version_matches_package_version() -> None:
    project = _load_project_metadata()
    package_init = Path("src/app/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', package_init)

    assert match is not None
    assert project["version"] == match.group(1)


def test_application_version_display_reuses_package_version_constant() -> None:
    entrypoints_source = Path("src/app/entrypoints.py").read_text(encoding="utf-8")
    main_window_source = Path("src/app/ui/main_window.py").read_text(encoding="utf-8")

    assert re.search(r"from app import .*\b__version__\b", entrypoints_source) is not None
    assert "setApplicationVersion(__version__)" in entrypoints_source
    assert re.search(r"from \.\. import .*\b__version__\b", main_window_source) is not None
    assert "v{__version__}" in main_window_source


def test_project_urls_do_not_use_placeholder_repository() -> None:
    project = _load_project_metadata()
    urls = project["urls"]

    assert urls["Homepage"].startswith("https://github.com/Izumi0527/video_watermark_remover")
    assert all("yourusername" not in value for value in urls.values())
