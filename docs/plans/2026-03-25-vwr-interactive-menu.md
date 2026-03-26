# vwr.ps1 纯交互式菜单 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `scripts/vwr.ps1` 改为纯交互式 PowerShell 菜单入口，并增强缓存/临时文件清理能力。

**Architecture:** 保留现有 `Invoke-*` 业务函数，移除对外 `<command>` 子命令分发；新增菜单与输入辅助函数，由菜单收集参数后直接调用现有函数。`clean` 改为分级清理，并统一管理缓存/临时目录目标。

**Tech Stack:** PowerShell、pytest、subprocess

---

### Task 1: 锁定纯交互入口行为

**Files:**
- Create: `tests/unit/test_vwr_interactive_menu.py`
- Modify: `scripts/vwr.ps1`

**Step 1: Write the failing test**

新增以下测试：

- 无参数运行脚本时显示主菜单
- 输入 `H` 时显示帮助
- 输入 `0` 时正常退出
- 传入旧式尾参时提示“当前脚本已改为纯交互模式”

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "menu or interactive"`

Expected: FAIL，说明脚本当前仍走旧 CLI 或尚未提供菜单函数。

**Step 3: Write minimal implementation**

- 在 `scripts/vwr.ps1` 中新增主菜单与帮助菜单函数
- 增加“检测旧式尾参并拒绝执行”的入口逻辑

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "menu or interactive"`

Expected: PASS

### Task 2: 锁定菜单驱动到业务函数的映射

**Files:**
- Create: `tests/unit/test_vwr_interactive_menu.py`
- Modify: `scripts/vwr.ps1`

**Step 1: Write the failing test**

为以下菜单路径分别新增测试：

- `setup` 默认选项
- `run` 自动修复
- `test` 选择 `unit + Quick`
- `clean` 选择 `all`

测试方式：重载 `Read-Host` 提供输入队列，重载目标 `Invoke-*` 函数记录收到的状态。

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "dispatch"`

Expected: FAIL，说明菜单尚未把输入映射到对应动作。

**Step 3: Write minimal implementation**

- 新增通用读取函数、布尔选择函数、枚举选择函数
- 菜单选择后设置相应脚本变量并调用现有 `Invoke-*`

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "dispatch"`

Expected: PASS

### Task 3: 锁定增强清理范围

**Files:**
- Create: `tests/unit/test_vwr_interactive_menu.py`
- Modify: `scripts/vwr.ps1`

**Step 1: Write the failing test**

新增测试覆盖：

- `Resolve-CleanTargets basic`
- `Resolve-CleanTargets temp`
- `Resolve-CleanTargets all`
- `Resolve-CleanTargets deep`
- `clean` 扫描 `src/` 与 `tests/` 的 `__pycache__` / `*.pyc` / `*.pyo`
- 不误删 `.venv` / `models` / `release`

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "clean"`

Expected: FAIL，说明当前清理目标范围仍不完整。

**Step 3: Write minimal implementation**

- 新增清理目标解析函数
- `Invoke-Clean` 支持按范围执行
- 默认清理级别改为 `all`

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q -k "clean"`

Expected: PASS

### Task 4: 同步更新脚本说明

**Files:**
- Modify: `scripts/README.md`
- Modify: `README.md`

**Step 1: Update docs**

- 去掉旧的 `.\scripts\vwr.ps1 help/setup/run/...` 快速用法
- 改为“直接运行脚本进入菜单”
- 补充清理级别说明

**Step 2: Verify docs**

Run: `rg -n -F ".\\scripts\\vwr.ps1 help" README.md scripts/README.md`

Expected: 无结果

### Task 5: 运行最终验证

**Files:**
- Modify: `scripts/vwr.ps1`
- Create: `tests/unit/test_vwr_interactive_menu.py`

**Step 1: Run unit verification**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_interactive_menu.py -q`

Expected: PASS

**Step 2: Run direct script verification**

Run: `@("H","0") -join [Environment]::NewLine | powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1"`

Expected: 输出主菜单、帮助信息，并正常退出。
