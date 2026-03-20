from pathlib import Path
import importlib.util


NEW_PATH = Path("tests/integration/runtime/task6_runtime_smoke.py")
OLD_PATH = Path("scripts/task6_runtime_smoke.py")
DOC_PATH = Path("docs/plans/2026-03-18-project-structure-audit.md")


def test_task6_runtime_smoke_script_has_been_moved_under_tests() -> None:
    """Task 6 运行态 smoke 脚本应归档到 tests 目录下。"""

    assert NEW_PATH.exists(), f"缺少迁移后的 smoke 脚本：{NEW_PATH}"
    assert not OLD_PATH.exists(), f"旧脚本路径仍存在：{OLD_PATH}"


def test_task6_runtime_smoke_docs_reference_new_tests_path() -> None:
    """相关文档不应继续引用旧的 scripts 路径。"""

    content = DOC_PATH.read_text(encoding="utf-8")
    assert "tests/integration/runtime/task6_runtime_smoke.py" in content
    assert "scripts/task6_runtime_smoke.py" not in content


def test_task6_runtime_smoke_project_root_still_resolves_repo_root() -> None:
    """脚本迁移到 tests 后，仍应能定位仓库根目录。"""

    spec = importlib.util.spec_from_file_location("task6_runtime_smoke", NEW_PATH)
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.project_root().resolve() == Path.cwd().resolve()
