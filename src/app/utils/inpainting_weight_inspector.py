#!/usr/bin/env python3
"""
U-Net 权重体检工具

用于判断候选权重文件是否能被当前仓库直接作为 GPU 修复 U-Net 权重加载。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import torch

from app.core.ai.dl_inpainter import UNetInpaintingModel

SUPPORTED_WEIGHT_EXTENSIONS = (".pt", ".pth", ".bin", ".ckpt")
KNOWN_UNSUPPORTED_EXTENSIONS = {
    ".safetensors": "当前加载器不支持 safetensors 格式",
    ".onnx": "当前加载器不支持 ONNX 格式",
    ".engine": "当前加载器不支持 TensorRT engine 格式",
    ".trt": "当前加载器不支持 TensorRT 格式",
}
WRAPPED_STATE_DICT_KEYS = ("state_dict", "model", "model_state_dict")
COMMON_STATE_DICT_PREFIXES = ("module.", "model.")


@dataclass(frozen=True)
class WeightInspectionResult:
    """单个候选文件的体检结果。"""

    path: Path
    status: str
    reason_code: str
    message: str
    is_directly_loadable: bool
    container_key: Optional[str] = None
    prefix_to_strip: Optional[str] = None
    missing_keys: tuple[str, ...] = ()
    unexpected_keys: tuple[str, ...] = ()
    shape_mismatches: tuple[str, ...] = ()

    def to_summary_line(self) -> str:
        """返回单行摘要，便于 CLI 输出与脚本消费。"""
        extras = [f"reason={self.reason_code}"]
        if self.container_key:
            extras.append(f"container_key={self.container_key}")
        if self.prefix_to_strip:
            extras.append(f"prefix_to_strip={self.prefix_to_strip}")
        if self.shape_mismatches:
            extras.append(f"shape_mismatches={','.join(self.shape_mismatches)}")
        if self.missing_keys:
            extras.append(f"missing_keys={','.join(self.missing_keys[:5])}")
        if self.unexpected_keys:
            extras.append(f"unexpected_keys={','.join(self.unexpected_keys[:5])}")
        return f"{self.status}: {self.path} ({'; '.join(extras)}) {self.message}"


class InpaintingWeightInspector:
    """基于当前仓库真实 U-Net 结构做兼容性体检。"""

    def __init__(self) -> None:
        reference_model = UNetInpaintingModel(in_channels=4, out_channels=3, base_channels=32)
        reference_state_dict = reference_model.state_dict()
        self.reference_shapes = {
            key: tuple(value.shape) for key, value in reference_state_dict.items()
        }
        self.reference_keys = tuple(reference_state_dict.keys())

    def inspect_file(self, path: Path | str) -> WeightInspectionResult:
        """检查单个候选文件。"""
        candidate_path = Path(path)
        if not candidate_path.exists():
            return WeightInspectionResult(
                path=candidate_path,
                status="missing",
                reason_code="file_not_found",
                message="文件不存在",
                is_directly_loadable=False,
            )

        if candidate_path.is_dir():
            return WeightInspectionResult(
                path=candidate_path,
                status="incompatible",
                reason_code="path_is_directory",
                message="目标是目录，请使用 scan_directory 或 CLI 目录模式",
                is_directly_loadable=False,
            )

        unsupported_message = KNOWN_UNSUPPORTED_EXTENSIONS.get(candidate_path.suffix.lower())
        if unsupported_message:
            return WeightInspectionResult(
                path=candidate_path,
                status="incompatible",
                reason_code="unsupported_format",
                message=unsupported_message,
                is_directly_loadable=False,
            )

        try:
            payload = torch.load(candidate_path, map_location="cpu")
        except Exception as exc:  # noqa: BLE001
            return WeightInspectionResult(
                path=candidate_path,
                status="load_error",
                reason_code="torch_load_failed",
                message=f"torch.load 读取失败: {exc}",
                is_directly_loadable=False,
            )

        candidates = self._extract_state_dict_candidates(payload)
        if not candidates:
            return WeightInspectionResult(
                path=candidate_path,
                status="incompatible",
                reason_code="state_dict_not_found",
                message="未识别到可分析的 state_dict 结构",
                is_directly_loadable=False,
            )

        best_result: Optional[WeightInspectionResult] = None
        for state_dict, container_key in candidates:
            result = self._analyze_state_dict(
                path=candidate_path,
                state_dict=state_dict,
                container_key=container_key,
            )
            if best_result is None or self._status_rank(result.status) < self._status_rank(
                best_result.status
            ):
                best_result = result
            if result.status == "compatible":
                return result

        assert best_result is not None
        return best_result

    def scan_directory(self, directory: Path | str, recursive: bool = True) -> list[WeightInspectionResult]:
        """扫描目录中的候选权重文件。"""
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            return []

        iterator: Iterable[Path]
        if recursive:
            iterator = root.rglob("*")
        else:
            iterator = root.glob("*")

        candidates = sorted(
            (
                path
                for path in iterator
                if path.is_file()
                and path.suffix.lower()
                in {*SUPPORTED_WEIGHT_EXTENSIONS, *KNOWN_UNSUPPORTED_EXTENSIONS.keys()}
            ),
            key=lambda item: str(item.relative_to(root)).lower(),
        )
        return [self.inspect_file(path) for path in candidates]

    def _extract_state_dict_candidates(
        self, payload: Any
    ) -> list[tuple[Mapping[str, Any], Optional[str]]]:
        """从顶层对象中抽取可分析的候选 state_dict。"""
        candidates: list[tuple[Mapping[str, Any], Optional[str]]] = []
        if self._looks_like_state_dict(payload):
            candidates.append((payload, None))

        if isinstance(payload, Mapping):
            for key in WRAPPED_STATE_DICT_KEYS:
                nested = payload.get(key)
                if self._looks_like_state_dict(nested):
                    candidates.append((nested, key))

        return candidates

    def _analyze_state_dict(
        self,
        path: Path,
        state_dict: Mapping[str, Any],
        container_key: Optional[str],
    ) -> WeightInspectionResult:
        """分析候选 state_dict 与参考 U-Net 权重的匹配关系。"""
        comparison = self._compare_state_dict(state_dict)
        if comparison["exact_match"]:
            if container_key is None:
                return WeightInspectionResult(
                    path=path,
                    status="compatible",
                    reason_code="direct_state_dict",
                    message="可被当前仓库直接加载",
                    is_directly_loadable=True,
                )

            return WeightInspectionResult(
                path=path,
                status="needs_unpacking",
                reason_code="wrapped_state_dict",
                message="需要先从包装 checkpoint 中解包出 state_dict",
                is_directly_loadable=False,
                container_key=container_key,
            )

        for prefix in COMMON_STATE_DICT_PREFIXES:
            if not any(key.startswith(prefix) for key in state_dict.keys()):
                continue

            stripped_state_dict = {
                key[len(prefix) :] if key.startswith(prefix) else key: value
                for key, value in state_dict.items()
            }
            stripped_comparison = self._compare_state_dict(stripped_state_dict)
            if stripped_comparison["exact_match"]:
                if container_key is None:
                    return WeightInspectionResult(
                        path=path,
                        status="needs_key_rewrite",
                        reason_code="prefixed_state_dict",
                        message="键名前缀需要清理后才能直接加载",
                        is_directly_loadable=False,
                        prefix_to_strip=prefix,
                    )

                return WeightInspectionResult(
                    path=path,
                    status="needs_unpacking",
                    reason_code="wrapped_state_dict",
                    message="需要先解包，再清理常见键名前缀后才能加载",
                    is_directly_loadable=False,
                    container_key=container_key,
                    prefix_to_strip=prefix,
                )

        reason_code = "structure_mismatch"
        if comparison["shape_mismatches"]:
            reason_code = "shape_mismatch"
        elif comparison["missing_keys"]:
            reason_code = "missing_keys"
        elif comparison["unexpected_keys"]:
            reason_code = "unexpected_keys"

        return WeightInspectionResult(
            path=path,
            status="incompatible",
            reason_code=reason_code,
            message="与当前仓库的 U-Net 结构不兼容",
            is_directly_loadable=False,
            container_key=container_key,
            missing_keys=tuple(comparison["missing_keys"]),
            unexpected_keys=tuple(comparison["unexpected_keys"]),
            shape_mismatches=tuple(comparison["shape_mismatches"]),
        )

    def _compare_state_dict(self, state_dict: Mapping[str, Any]) -> dict[str, Any]:
        """比较候选 state_dict 与参考模型的键名和 shape。"""
        candidate_keys = tuple(state_dict.keys())
        missing_keys = sorted(set(self.reference_keys) - set(candidate_keys))
        unexpected_keys = sorted(set(candidate_keys) - set(self.reference_keys))
        shape_mismatches: list[str] = []

        for key in set(self.reference_keys).intersection(candidate_keys):
            value = state_dict[key]
            if not isinstance(value, torch.Tensor):
                shape_mismatches.append(key)
                continue

            if tuple(value.shape) != self.reference_shapes[key]:
                shape_mismatches.append(key)

        return {
            "missing_keys": missing_keys,
            "unexpected_keys": unexpected_keys,
            "shape_mismatches": sorted(shape_mismatches),
            "exact_match": not missing_keys and not unexpected_keys and not shape_mismatches,
        }

    @staticmethod
    def _looks_like_state_dict(payload: Any) -> bool:
        """判断对象是否像一个可分析的 state_dict。"""
        return (
            isinstance(payload, Mapping)
            and bool(payload)
            and all(isinstance(key, str) for key in payload.keys())
            and all(isinstance(value, torch.Tensor) for value in payload.values())
        )

    @staticmethod
    def _status_rank(status: str) -> int:
        order = {
            "compatible": 0,
            "needs_unpacking": 1,
            "needs_key_rewrite": 2,
            "incompatible": 3,
            "load_error": 4,
            "missing": 5,
        }
        return order.get(status, 99)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="U-Net 权重体检工具")
    parser.add_argument("path", help="候选权重文件或目录路径")
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="目录扫描时仅检查当前目录，不递归子目录",
    )
    return parser


def _determine_exit_code(results: Sequence[WeightInspectionResult]) -> int:
    if not results:
        return 1
    if all(result.status == "compatible" for result in results):
        return 0
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    """命令行入口。"""
    parser = _build_argument_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    inspector = InpaintingWeightInspector()
    target_path = Path(args.path)

    try:
        if target_path.is_dir():
            results = inspector.scan_directory(target_path, recursive=not args.non_recursive)
            if not results:
                print(f"no_candidates: {target_path} (reason=empty_directory) 未发现候选权重文件")
                return 1
        else:
            results = [inspector.inspect_file(target_path)]

        for result in results:
            print(result.to_summary_line())
        return _determine_exit_code(results)
    except Exception as exc:  # noqa: BLE001
        print(f"execution_error: {target_path} (reason=unexpected_exception) {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
