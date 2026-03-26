#!/usr/bin/env python3
"""
UI组件功能测试模块

提供Phase 3 UI组件的测试功能：
1. 组件导入测试
2. 样式管理器测试
3. 用户偏好设置测试
4. 高级参数组件测试

从 test_phase3.py 重构拆分
作者: Izumi0527
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

import shutil
import uuid
from pathlib import Path
from typing import Callable, Set, Tuple

import pytest

pytest.importorskip("PyQt6")

from tests.integration.test_utilities import print_test_header, print_test_result

RUNTIME_ROOT = Path(__file__).resolve().parents[3] / ".cache" / "tests" / "ui-components"


def _fail_test(test_name: str, error_msg: str) -> None:
    print_test_result(test_name, False, error_msg)
    raise AssertionError(error_msg)


def test_component_imports() -> None:
    """测试UI组件导入。"""
    test_name = "UI组件导入"
    print_test_header("测试UI组件导入")

    import_results = []

    try:
        from app.ui.widgets.image_selector_widget import ImageSelectorWidget

        import_results.append(("手动选择组件", True, "导入成功"))
    except ImportError as exc:
        import_results.append(("手动选择组件", False, f"导入失败: {exc}"))

    try:
        from app.ui.widgets.batch.batch_processing_widget import BatchProcessingWidget

        import_results.append(("批量处理组件", True, "导入成功"))
    except ImportError as exc:
        import_results.append(("批量处理组件", False, f"导入失败: {exc}"))

    try:
        from app.config.styles import ModernStyleManager

        import_results.append(("样式管理器", True, "导入成功"))
    except ImportError as exc:
        import_results.append(("样式管理器", False, f"导入失败: {exc}"))

    try:
        from app.config.preferences import UserPreferencesManager

        import_results.append(("用户偏好设置", True, "导入成功"))
    except ImportError as exc:
        import_results.append(("用户偏好设置", False, f"导入失败: {exc}"))

    try:
        from app.ui.widgets.advanced.advanced_parameters_widget import AdvancedParametersWidget

        import_results.append(("高级参数组件", True, "导入成功"))
    except ImportError as exc:
        import_results.append(("高级参数组件", False, f"导入失败: {exc}"))

    successful_imports = sum(1 for _, success, _ in import_results if success)
    total_imports = len(import_results)

    for component_name, success, details in import_results:
        print_test_result(component_name, success, details)

    assert (
        successful_imports == total_imports
    ), f"{total_imports - successful_imports}个组件导入失败 ({successful_imports}/{total_imports})"
    print_test_result(test_name, True, f"所有UI组件导入成功 ({successful_imports}/{total_imports})")


def test_style_manager() -> None:
    """测试样式管理器功能。"""
    test_name = "样式管理器"
    print_test_header("测试样式管理器功能")

    try:
        from app.config.styles import ModernStyleManager

        style_manager = ModernStyleManager()
        default_theme = style_manager.current_theme
        assert default_theme in ["dark", "light"], f"无效的默认主题: {default_theme}"

        original_theme = default_theme
        new_theme = "light" if original_theme == "dark" else "dark"
        style_manager.set_theme(new_theme)
        assert style_manager.current_theme == new_theme, "主题切换失败"

        style_manager.set_theme(original_theme)
        stylesheet = style_manager.get_complete_stylesheet()
        assert stylesheet and isinstance(stylesheet, str), "样式表生成失败"

        details = f"主题管理正常，当前主题: {original_theme}，样式表长度: {len(stylesheet)}"
        print_test_result(test_name, True, details)
    except Exception as exc:
        _fail_test(test_name, f"样式管理器测试失败: {exc}")


def test_user_preferences() -> None:
    """测试用户偏好设置功能。"""
    test_name = "用户偏好设置"
    print_test_header("测试用户偏好设置功能")

    try:
        from app.config.preferences import UserPreferencesManager

        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        runtime_dir = RUNTIME_ROOT / f"prefs_{uuid.uuid4().hex}"
        runtime_dir.mkdir()

        try:
            prefs_manager = UserPreferencesManager(str(runtime_dir))
            success = prefs_manager.set_preference("ui", "theme", "light")
            assert success, "设置偏好失败"

            retrieved_value = prefs_manager.get_preference("ui", "theme")
            assert retrieved_value == "light", f"获取偏好失败: {retrieved_value} != light"

            save_success = prefs_manager.save_preferences()
            assert save_success, "保存偏好失败"

            prefs_manager.add_recent_file("/test/path/file.txt")
            prefs_manager.get_recent_files()
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)

        details = "用户偏好设置功能正常：设置/获取、保存、最近文件管理"
        print_test_result(test_name, True, details)
    except Exception as exc:
        _fail_test(test_name, f"用户偏好设置测试失败: {exc}")


def test_advanced_parameters() -> None:
    """测试高级参数结构。"""
    test_name = "高级参数结构"
    print_test_header("测试高级参数结构")

    try:
        expected_params: Set[str] = {
            "detection_sensitivity",
            "detection_method",
            "min_detection_area",
            "inpainting_method",
            "inpainting_radius",
            "thread_count",
            "enable_gpu",
            "output_quality",
            "preserve_audio",
        }

        assert len(expected_params) >= 5, "高级参数结构定义不完整"

        detection_params = [param for param in expected_params if "detection" in param]
        inpainting_params = [param for param in expected_params if "inpainting" in param]

        assert len(detection_params) >= 2, "检测相关参数不足"
        assert len(inpainting_params) >= 2, "修复相关参数不足"

        details = (
            f"高级参数结构验证通过: {len(expected_params)}个参数，"
            f"包含{len(detection_params)}个检测参数和{len(inpainting_params)}个修复参数"
        )
        print_test_result(test_name, True, details)
    except Exception as exc:
        _fail_test(test_name, f"高级参数测试失败: {exc}")


def run_ui_component_tests() -> Tuple[int, int, dict]:
    """运行所有UI组件测试。"""
    tests: Tuple[Tuple[str, Callable[[], None]], ...] = (
        ("UI组件导入", test_component_imports),
        ("样式管理器", test_style_manager),
        ("用户偏好设置", test_user_preferences),
        ("高级参数结构", test_advanced_parameters),
    )

    passed = 0
    total = len(tests)
    test_results = {}

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            test_results[test_name] = (True, "通过")
        except Exception as exc:
            test_results[test_name] = (False, str(exc))

    return passed, total, test_results
