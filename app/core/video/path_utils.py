from __future__ import annotations

from pathlib import Path


def build_temp_path(output_path: str, tag: str) -> str:
    """
    基于输出路径生成同目录临时文件路径。

    设计目标：
    - 仅修改文件名，不修改目录结构
    - 保留原始扩展名（如 .mp4）
    - 避免使用字符串 replace 导致路径中 '.' 被意外替换

    Args:
        output_path: 最终输出文件路径
        tag: 临时标记（如 "temp_video"），会拼接为 "__temp_video"

    Returns:
        临时文件路径字符串
    """
    path = Path(output_path)
    normalized_tag = tag.strip()
    if not normalized_tag:
        normalized_tag = "temp"

    suffix = path.suffix
    tag_part = (
        normalized_tag if normalized_tag.startswith("__") else f"__{normalized_tag.lstrip('_')}"
    )

    if suffix:
        return str(path.with_name(f"{path.stem}{tag_part}{suffix}"))

    return str(path.with_name(f"{path.name}{tag_part}"))
