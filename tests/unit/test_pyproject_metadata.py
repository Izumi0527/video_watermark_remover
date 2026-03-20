from __future__ import annotations

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
