# vwr.ps1 LaMa TorchScript 链接提示 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `scripts/vwr.ps1` 中补充可直接使用的 TorchScript `big-lama.pt` 下载链接与环境变量提示，帮助用户快速配置 `VWR_LAMA_MODEL_PATH`。

**Architecture:** 优先把链接与说明收敛成单独的小函数，避免把 URL 和提示文案散落在 `Show-Help`、`Invoke-Run` 多处；测试先锁定帮助输出与提示函数，再做最小脚本改动。

**Tech Stack:** PowerShell、pytest、subprocess

---

### Task 1: 锁定 vwr 帮助输出中的 LaMa 链接提示

**Files:**
- Modify: `tests/unit/test_vwr_setup_dependency_shortcut.py`
- Modify: `scripts/vwr.ps1`
- Modify: `scripts/README.md`

**Step 1: Write the failing test**

新增两个断言：

- `scripts/vwr.ps1 help` 输出中包含 TorchScript `big-lama.pt` 下载链接
- 脚本内部的 LaMa 提示函数会输出 `VWR_LAMA_MODEL_PATH` 设置提示

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q -k "lama_torchscript or vwr_help"`

Expected: FAIL，提示当前脚本尚未提供相关函数或帮助文案。

**Step 3: Write minimal implementation**

实现：

- 在 `scripts/vwr.ps1` 中新增 LaMa TorchScript 链接/提示函数
- `Show-Help` 中调用该函数
- `scripts/README.md` 同步补一段配置说明

**Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q -k "lama_torchscript or vwr_help"`

Expected: PASS

**Step 5: Run direct script verification**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\vwr.ps1 help`

Expected: 输出中包含 `big-lama.pt` 下载链接和 `VWR_LAMA_MODEL_PATH` 示例。
