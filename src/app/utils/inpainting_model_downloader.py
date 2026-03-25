#!/usr/bin/env python3
"""
修复模型资源辅助工具。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional


_ENV_FALLBACKS: dict[str, tuple[str, ...]] = {
    "lama_model_path": ("VWR_LAMA_MODEL_PATH",),
    "lama_model_dir": ("VWR_LAMA_MODEL_PATH",),
    "inpainting_model_path": ("VWR_INPAINTING_MODEL_PATH",),
}
_PROJECT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "lama_model_path": ("models/big-lama.pt", "models/lama/big-lama.pt"),
    "lama_model_dir": ("models/big-lama.pt", "models/lama/big-lama.pt"),
}
_MODEL_DIR_CANDIDATES: dict[str, tuple[str, ...]] = {
    "lama_model_path": ("big-lama.pt", "lama/big-lama.pt"),
    "lama_model_dir": ("big-lama.pt", "lama/big-lama.pt"),
}


def resolve_inpainting_asset_ref(
    ai_params: Optional[dict[str, Any]],
    config: Any,
    option_names: Iterable[str],
    *,
    sections: tuple[str, ...] = ("Models", "models"),
) -> Optional[str]:
    """按优先级从 ai_params / config / env / 常见候选路径中解析修复资源引用。"""
    merged_params = dict(ai_params or {})

    for option_name in option_names:
        normalized = _normalize_asset_ref(merged_params.get(option_name))
        if normalized:
            return normalized

    if config is not None and hasattr(config, "has_option"):
        for option_name in option_names:
            for section in sections:
                try:
                    if config.has_option(section, option_name):
                        normalized = _normalize_asset_ref(config.get(section, option_name))
                        if normalized:
                            return normalized
                except Exception:
                    continue

    for option_name in option_names:
        for env_name in _ENV_FALLBACKS.get(option_name, ()): 
            normalized = _normalize_asset_ref(os.environ.get(env_name))
            if normalized:
                return normalized

    for option_name in option_names:
        candidate = _resolve_builtin_candidate(config, option_name)
        if candidate is not None:
            return str(candidate)

    return None


def _resolve_builtin_candidate(config: Any, option_name: str) -> Optional[Path]:
    for candidate in _iter_builtin_candidates(config, option_name):
        if candidate.exists():
            return candidate
    return None


def _iter_builtin_candidates(config: Any, option_name: str) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()

    def _append(path: Path) -> None:
        marker = str(path).lower()
        if marker in seen:
            return
        seen.add(marker)
        candidates.append(path)

    for root in _iter_project_roots():
        for relative_path in _PROJECT_CANDIDATES.get(option_name, ()): 
            _append((root / relative_path).expanduser())

    for model_dir in _iter_default_model_dirs(config):
        for relative_path in _MODEL_DIR_CANDIDATES.get(option_name, ()): 
            _append((model_dir / relative_path).expanduser())

    return candidates


def _iter_project_roots() -> list[Path]:
    roots: list[Path] = []
    try:
        roots.append(Path.cwd())
    except Exception:
        pass

    try:
        roots.append(Path(__file__).resolve().parents[3])
    except Exception:
        pass

    return roots


def _iter_default_model_dirs(config: Any) -> list[Path]:
    default_model_dir = _get_config_option(config, ("Paths", "paths"), ("default_model_dir",))
    if not default_model_dir:
        return []
    return [Path(default_model_dir).expanduser()]


def _get_config_option(
    config: Any,
    sections: tuple[str, ...],
    option_names: tuple[str, ...],
) -> Optional[str]:
    if config is None or not hasattr(config, "has_option"):
        return None

    for option_name in option_names:
        for section in sections:
            try:
                if config.has_option(section, option_name):
                    raw_value = config.get(section, option_name)
                    normalized = str(raw_value).strip()
                    if normalized:
                        return normalized
            except Exception:
                continue
    return None


def _normalize_asset_ref(raw_value: Any) -> Optional[str]:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    return str(Path(normalized).expanduser())
