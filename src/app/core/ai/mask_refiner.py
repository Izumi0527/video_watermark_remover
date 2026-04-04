#!/usr/bin/env python3
"""
掩码细化器。

用于收敛 YOLO 检测后的轻量掩码后处理逻辑，为后续复杂图片场景扩展预留统一入口。
"""

from __future__ import annotations

from typing import Optional, Sequence

import cv2
import numpy as np
from numpy.typing import NDArray


class MaskRefiner:
    """面向复杂 Logo 的轻量掩码细化器。"""

    def __init__(
        self,
        *,
        profile: str = "default",
        close_kernel: int = 5,
        erode_iterations: int = 0,
        dilate_iterations: int = 0,
    ) -> None:
        self.profile = str(profile or "default").strip().lower() or "default"
        self.close_kernel = max(0, int(close_kernel or 0))
        self.erode_iterations = max(0, int(erode_iterations or 0))
        self.dilate_iterations = max(0, int(dilate_iterations or 0))

    @staticmethod
    def _normalize_kernel_size(kernel_size: int) -> int:
        size = max(0, int(kernel_size or 0))
        if size <= 0:
            return 0
        return size if size % 2 == 1 else size + 1

    @staticmethod
    def _binarize_mask(mask: NDArray[np.uint8]) -> NDArray[np.uint8]:
        return np.where(np.asarray(mask, dtype=np.uint8) > 0, 255, 0).astype(np.uint8)

    def _resolve_close_kernel(self, frame_shape: Optional[Sequence[int]] = None) -> int:
        """解析复杂 Logo 场景下的基础闭运算核大小。"""
        kernel_size = self._normalize_kernel_size(self.close_kernel)
        if kernel_size <= 0:
            return 0

        if self.profile == "complex_logo":
            kernel_size = min(max(kernel_size, 5), 9)

        if frame_shape and len(frame_shape) >= 2:
            short_edge = min(int(frame_shape[0] or 0), int(frame_shape[1] or 0))
            if short_edge > 0:
                adaptive_cap = max(3, min(kernel_size, (short_edge // 8) | 1))
                kernel_size = min(kernel_size, adaptive_cap)

        return self._normalize_kernel_size(kernel_size)

    def _resolve_speckle_area_threshold(self, close_kernel: int) -> int:
        if self.profile != "complex_logo":
            return 0
        return max(2, min(8, max(close_kernel, 2)))

    def _remove_small_components(
        self,
        mask: NDArray[np.uint8],
        *,
        close_kernel: int,
    ) -> NDArray[np.uint8]:
        """移除离散小噪点，避免后续桥接把 speckles 放大成修复区域。"""
        if not np.any(mask):
            return mask

        min_area = self._resolve_speckle_area_threshold(close_kernel)
        if min_area <= 1:
            return mask

        binary = np.where(mask > 0, 255, 0).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        if count <= 1:
            return binary

        cleaned = np.zeros_like(binary)
        for label in range(1, int(count)):
            area = int(stats[label, cv2.CC_STAT_AREA] or 0)
            if area < min_area:
                continue
            cleaned[labels == label] = 255
        return cleaned

    @staticmethod
    def _extract_internal_holes(mask: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """提取内部孔洞的稳定核心，避免裂缝区域被误恢复成孔洞。"""
        if not np.any(mask):
            return np.zeros_like(mask, dtype=np.uint8)

        binary = np.where(mask > 0, 255, 0).astype(np.uint8)
        inverse = (binary == 0).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(inverse, connectivity=8)
        holes = np.zeros_like(binary, dtype=np.uint8)
        height, width = binary.shape[:2]
        core_threshold = 1.5
        for label in range(1, int(count)):
            left = int(stats[label, cv2.CC_STAT_LEFT] or 0)
            top = int(stats[label, cv2.CC_STAT_TOP] or 0)
            comp_width = int(stats[label, cv2.CC_STAT_WIDTH] or 0)
            comp_height = int(stats[label, cv2.CC_STAT_HEIGHT] or 0)
            area = int(stats[label, cv2.CC_STAT_AREA] or 0)
            touches_border = (
                left <= 0
                or top <= 0
                or (left + comp_width) >= width
                or (top + comp_height) >= height
            )
            if touches_border or area <= 0:
                continue

            component_mask = np.zeros_like(binary, dtype=np.uint8)
            component_mask[labels == label] = 255
            distance = cv2.distanceTransform(
                (component_mask > 0).astype(np.uint8),
                cv2.DIST_L2,
                3,
            )
            stable_core = np.where(distance >= core_threshold, 255, 0).astype(np.uint8)
            if not np.any(stable_core):
                continue

            safe_core = np.zeros_like(stable_core, dtype=np.uint8)
            inset = 2
            inner_top = top + inset
            inner_left = left + inset
            inner_bottom = top + comp_height - inset
            inner_right = left + comp_width - inset
            if inner_bottom > inner_top and inner_right > inner_left:
                safe_core[inner_top:inner_bottom, inner_left:inner_right] = stable_core[
                    inner_top:inner_bottom, inner_left:inner_right
                ]
            else:
                safe_core = stable_core
            if not np.any(safe_core):
                continue
            holes = np.maximum(holes, safe_core).astype(np.uint8)
        return holes

    @staticmethod
    def _restore_internal_holes(
        refined: NDArray[np.uint8],
        holes: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        if not np.any(holes):
            return refined
        restored = refined.copy()
        restored[holes > 0] = 0
        return restored

    @staticmethod
    def _fill_short_linear_gaps(  # noqa: C901
        mask: NDArray[np.uint8],
        *,
        max_gap: int,
        axis: str,
    ) -> NDArray[np.uint8]:
        """按行或按列补齐短缝，提升细长断边和开口轮廓的连续性。"""
        if max_gap <= 0:
            return mask

        filled = np.asarray(mask, dtype=np.uint8).copy()

        def _read_horizontal(major: int, minor: int) -> np.uint8:
            return filled[major, minor]

        def _write_horizontal(major: int, start: int, end: int) -> None:
            filled[major, start:end] = 255

        def _read_vertical(major: int, minor: int) -> np.uint8:
            return filled[minor, major]

        def _write_vertical(major: int, start: int, end: int) -> None:
            filled[start:end, major] = 255

        if axis == "horizontal":
            major_len, minor_len = filled.shape[0], filled.shape[1]
            read_value = _read_horizontal
            write_range = _write_horizontal
        else:
            major_len, minor_len = filled.shape[1], filled.shape[0]
            read_value = _read_vertical
            write_range = _write_vertical

        for major_index in range(major_len):
            active_positions = [
                minor_index
                for minor_index in range(minor_len)
                if int(read_value(major_index, minor_index)) > 0
            ]
            if len(active_positions) < 2:
                continue
            previous = active_positions[0]
            for current in active_positions[1:]:
                gap = int(current - previous - 1)
                if 0 < gap <= max_gap:
                    write_range(major_index, previous + 1, current)
                previous = current
        return filled

    def _bridge_complex_logo_cracks(
        self,
        mask: NDArray[np.uint8],
        *,
        close_kernel: int,
    ) -> NDArray[np.uint8]:
        """通过基础闭运算 + 多厚度桥接修补复杂 Logo 的裂缝与断边。"""
        if close_kernel <= 0:
            return mask

        regular_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (close_kernel, close_kernel),
        )
        candidates = [
            np.asarray(mask, dtype=np.uint8),
            np.asarray(cv2.morphologyEx(mask, cv2.MORPH_CLOSE, regular_kernel), dtype=np.uint8),
        ]

        bridge_span = max(3, close_kernel * 3)
        for minor_axis in (1, 3, max(5, close_kernel + 2)):
            horizontal_kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (bridge_span, minor_axis),
            )
            vertical_kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (minor_axis, bridge_span),
            )
            candidates.append(
                np.asarray(
                    cv2.morphologyEx(mask, cv2.MORPH_CLOSE, horizontal_kernel), dtype=np.uint8
                )
            )
            candidates.append(
                np.asarray(cv2.morphologyEx(mask, cv2.MORPH_CLOSE, vertical_kernel), dtype=np.uint8)
            )

        linear_gap_limit = max(2, close_kernel * 2)
        candidates.append(
            self._fill_short_linear_gaps(mask, max_gap=linear_gap_limit, axis="horizontal"),
        )
        candidates.append(
            self._fill_short_linear_gaps(mask, max_gap=linear_gap_limit, axis="vertical"),
        )

        return np.maximum.reduce(candidates).astype(np.uint8)

    def refine(
        self,
        raw_mask: Optional[NDArray[np.uint8]],
        frame_shape: Optional[Sequence[int]] = None,
    ) -> Optional[NDArray[np.uint8]]:
        """执行轻量掩码细化。"""
        if raw_mask is None:
            return None

        mask = np.asarray(raw_mask, dtype=np.uint8)
        if mask.ndim != 2:
            mask = np.squeeze(mask)
            if mask.ndim != 2:
                return np.asarray(raw_mask, dtype=np.uint8)

        if not np.any(mask):
            return self._binarize_mask(mask)

        refined = self._binarize_mask(mask)
        close_kernel = self._resolve_close_kernel(frame_shape)

        if self.erode_iterations > 0:
            fine_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            refined = np.asarray(
                cv2.erode(refined, fine_kernel, iterations=self.erode_iterations),
                dtype=np.uint8,
            )
        if self.dilate_iterations > 0:
            fine_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            refined = np.asarray(
                cv2.dilate(refined, fine_kernel, iterations=self.dilate_iterations),
                dtype=np.uint8,
            )

        refined = self._binarize_mask(refined)
        refined = self._remove_small_components(refined, close_kernel=close_kernel)
        baseline_mask = refined.copy()
        preserved_holes = self._extract_internal_holes(baseline_mask)

        if close_kernel > 0:
            if self.profile == "complex_logo":
                refined = self._bridge_complex_logo_cracks(baseline_mask, close_kernel=close_kernel)
                refined = np.maximum(refined, baseline_mask).astype(np.uint8)
                refined = self._restore_internal_holes(refined, preserved_holes)
            else:
                close_struct = cv2.getStructuringElement(
                    cv2.MORPH_ELLIPSE,
                    (close_kernel, close_kernel),
                )
                refined = np.asarray(
                    cv2.morphologyEx(baseline_mask, cv2.MORPH_CLOSE, close_struct),
                    dtype=np.uint8,
                )
                refined = np.maximum(refined, baseline_mask).astype(np.uint8)
        else:
            refined = baseline_mask

        refined = self._binarize_mask(refined)
        refined = self._remove_small_components(refined, close_kernel=close_kernel)
        if self.profile == "complex_logo":
            refined = self._restore_internal_holes(refined, preserved_holes)
        return self._binarize_mask(refined)
