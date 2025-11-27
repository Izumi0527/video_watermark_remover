"""
模块语法烟囱测试：确保关键模块可编译，无 VSCode/Pylance 可见的语法级报错。

说明：
- 使用 py_compile 仅校验语法，不触发实际依赖加载（如 PyQt6、torch、cv2 等），适合快速发现拼写/缩进/未闭合字符串等问题。
- 选择核心入口、配置、工具、AI/视频/界面主模块作为覆盖面。
"""

import py_compile
from pathlib import Path

import pytest

# 按重要性列出的待编译模块路径（相对仓库根目录）
MODULE_PATHS = [
    "main.py",
    "app/config/config_manager.py",
    "app/utils/logger_setup.py",
    "app/utils/utils.py",
    "app/core/ai/ai_handler.py",
    "app/core/ai/yolo_detector.py",
    "app/core/video/video_processor.py",
    "app/ui/main_window.py",
]


@pytest.mark.parametrize("relative_path", MODULE_PATHS)
def test_module_can_be_compiled(relative_path):
    """关键模块应能通过语法编译，避免静态检查报错。"""
    path = Path(relative_path)
    assert path.exists(), f"文件不存在：{relative_path}"

    # doraise=True 确保任何语法问题直接抛出，便于定位
    py_compile.compile(path, doraise=True)
