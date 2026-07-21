"""偏好配置测试的内存文件系统夹具。"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

import app.config.preferences.manager as preferences_manager_module
import app.config.preferences.storage as preferences_storage_module
import app.config.preferences.validator as preferences_validator_module


class _MemoryTextFile(io.StringIO):
    """将文本写回内存文件系统的简易文件对象。"""

    def __init__(self, fs: "PreferenceMemoryFS", path: str, mode: str, initial_value: str = ""):
        super().__init__(initial_value)
        self._fs = fs
        self._path = path
        self._mode = mode
        if "a" in mode:
            self.seek(0, io.SEEK_END)

    def close(self) -> None:
        if not self.closed and any(flag in self._mode for flag in ("w", "a", "+")):
            self._fs.files[self._path] = self.getvalue()
            self._fs.ensure_parent_dirs(self._path)
        super().close()


class PreferenceMemoryFS:
    """为偏好测试提供最小内存文件系统实现。"""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.directories: set[str] = set()

    @staticmethod
    def normalize(path: str | Path) -> str:
        return str(Path(path)).replace("\\", "/")

    def ensure_parent_dirs(self, path: str | Path) -> None:
        current = Path(path).parent
        visited: set[str] = set()
        while True:
            normalized = self.normalize(current)
            if normalized in {"", "."} or normalized in visited:
                break
            visited.add(normalized)
            self.directories.add(normalized)
            if current == current.parent:
                break
            current = current.parent

    def mkdir(self, path: str | Path, parents: bool = False, exist_ok: bool = False) -> None:
        del exist_ok
        normalized = self.normalize(path)
        if parents:
            self.ensure_parent_dirs(path)
        self.directories.add(normalized)

    def exists(self, path: str | Path) -> bool:
        normalized = self.normalize(path)
        return normalized in self.files or normalized in self.directories

    def write_text(self, path: str | Path, content: str) -> None:
        normalized = self.normalize(path)
        self.ensure_parent_dirs(path)
        self.files[normalized] = content

    def open(self, file, mode: str = "r", encoding: str | None = None, *args, **kwargs):
        del encoding, args, kwargs
        if "b" in mode:
            raise AssertionError("偏好配置测试不需要二进制文件模式")

        normalized = self.normalize(file)
        if "r" in mode and normalized not in self.files:
            raise FileNotFoundError(normalized)

        if any(flag in mode for flag in ("w", "a", "+")):
            self.ensure_parent_dirs(file)

        initial_value = ""
        if "r" in mode or "a" in mode:
            initial_value = self.files.get(normalized, "")
        return _MemoryTextFile(self, normalized, mode, initial_value)

    def os_path_exists(self, path: str) -> bool:
        return self.exists(path)


@pytest.fixture(autouse=True)
def preference_memory_fs(monkeypatch: pytest.MonkeyPatch) -> PreferenceMemoryFS:
    """将偏好测试的文件操作切换到内存文件系统，避免环境写盘权限波动。"""

    fs = PreferenceMemoryFS()

    monkeypatch.setattr(
        preferences_storage_module.Path,
        "mkdir",
        lambda self, parents=False, exist_ok=False: fs.mkdir(
            self, parents=parents, exist_ok=exist_ok
        ),
        raising=False,
    )
    monkeypatch.setattr(
        preferences_storage_module.Path,
        "exists",
        lambda self: fs.exists(self),
        raising=False,
    )
    monkeypatch.setattr(preferences_storage_module, "open", fs.open, raising=False)
    monkeypatch.setattr(preferences_manager_module, "open", fs.open, raising=False)
    monkeypatch.setattr(preferences_validator_module.os.path, "exists", fs.os_path_exists)
    return fs
