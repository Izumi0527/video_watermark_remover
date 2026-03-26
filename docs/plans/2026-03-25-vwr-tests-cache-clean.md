# vwr.ps1 纳入 tests/.cache 清理 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `tests/.cache` 纳入 `scripts/vwr.ps1 clean` 的 `temp/all/deep` 清理层级，确保测试运行缓存可以被统一清理。

**Architecture:** 复用现有 `Resolve-CleanTargets` 目标列表扩展方式，把 `tests/.cache` 视为测试运行时缓存目录接入 `temp` 层；先通过失败测试锁定行为，再做最小实现，并同步清理说明文档。

**Tech Stack:** PowerShell、pytest

---

### Task 1: 锁定 tests/.cache 的清理层级

**Files:**
- Modify: `tests/unit/test_vwr_interactive_menu.py`
- Modify: `scripts/vwr.ps1`

**Step 1: Write the failing test**

- 断言 `Resolve-CleanTargets -Scope "all"` 包含 `tests/.cache`
- 断言 `Invoke-Clean -Scope "all"` 会删除 `tests/.cache`

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "tests_cache"`

Expected: FAIL，说明当前 `clean` 尚未覆盖 `tests/.cache`。

**Step 3: Write minimal implementation**

- 在 `Resolve-CleanTargets` 的 `temp` 层加入 `tests/.cache`

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "tests_cache"`

Expected: PASS

### Task 2: 同步文档与回归验证

**Files:**
- Modify: `scripts/README.md`
- Modify: `tests/unit/test_vwr_interactive_menu.py`

**Step 1: Update docs**

- 在 `scripts/README.md` 的清理说明中补充 `tests/.cache`

**Step 2: Run regression**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py tests/unit/test_vwr_setup_dependency_shortcut.py -q`

Expected: PASS
