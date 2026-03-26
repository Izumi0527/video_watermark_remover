# vwr.ps1 纳入 .uv-cache 深度清理 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将仓库根目录的 `.uv-cache` 纳入 `scripts/vwr.ps1 clean` 的 `deep` 清理层，补齐当前仅覆盖 `.cache/uv` 的缺口。

**Architecture:** 复用现有 `Resolve-CleanTargets` 分层结构，把 `.uv-cache` 作为工具缓存目录加入 `deep` 层；先通过失败测试锁定行为，再做最小实现，并同步脚本文档说明。

**Tech Stack:** PowerShell、pytest

---

### Task 1: 锁定 .uv-cache 属于 deep clean

**Files:**
- Modify: `tests/unit/test_vwr_interactive_menu.py`
- Modify: `scripts/vwr.ps1`

**Step 1: Write the failing test**

- 断言 `Resolve-CleanTargets -Scope "deep"` 包含 `.uv-cache`
- 断言 `Invoke-Clean -Scope "deep"` 会删除 `.uv-cache`

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "uv_cache"`

Expected: FAIL，说明当前 `deep clean` 尚未覆盖 `.uv-cache`。

**Step 3: Write minimal implementation**

- 在 `Resolve-CleanTargets` 的 `deep` 层加入 `.uv-cache`

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "uv_cache"`

Expected: PASS

### Task 2: 同步文档与回归验证

**Files:**
- Modify: `scripts/README.md`

**Step 1: Update docs**

- 在 `scripts/README.md` 的 `deep` 清理说明中补充 `.uv-cache`

**Step 2: Run regression**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py tests/unit/test_vwr_setup_dependency_shortcut.py -q`

Expected: PASS
