# VWR Setup Dependency Shortcut Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 `.\scripts\vwr.ps1 setup` 在 `.venv` 依赖已满足时跳过重复依赖安装，但继续执行 editable install 与导入验证。

**Architecture:** 在 `scripts/vwr.ps1` 中新增“依赖状态签名 + 轻量探针健康检查”层。`setup` 先判断状态是否有效，命中后跳过 `uv pip install`，未命中时正常安装并刷新状态文件。测试通过 Python 驱动 PowerShell 临时脚本的方式校验函数行为。

**Tech Stack:** PowerShell 7、uv、pytest、Python `subprocess`

---

### Task 1: 为 setup 新增可测的依赖状态判定层

**Files:**
- Modify: `scripts/vwr.ps1`
- Create: `tests/unit/test_vwr_setup_dependency_shortcut.py`

**Step 1: 写失败测试**

新增两个测试：

- `test_dependency_state_matches_and_probe_passes_should_skip_install`
- `test_dependency_state_matches_but_probe_fails_should_require_install`

测试方式：

- 读取 `scripts/vwr.ps1`
- 去掉结尾命令分发块，生成临时 PowerShell 脚本
- 在脚本尾部注入假的 `uv` 函数与临时 requirements / state 文件
- 调用新的依赖判定函数并输出 JSON
- 断言跳过判定与探针结果符合预期

**Step 2: 运行测试确认失败**

Run:

```bash
.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q
```

Expected:

- 因 PowerShell 中尚不存在目标判定函数而失败

**Step 3: 写最小实现**

在 `scripts/vwr.ps1` 新增：

- 依赖签名函数
- 状态文件读写函数
- 探针包选择函数
- setup 依赖跳过判定函数

**Step 4: 运行测试确认通过**

Run:

```bash
.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q
```

Expected:

- 新增定向测试通过

**Step 5: 提交**

```bash
git add scripts/vwr.ps1 tests/unit/test_vwr_setup_dependency_shortcut.py
git commit -m "feat(scripts): 为 setup 增加依赖跳过判定"
```

### Task 2: 将依赖状态判定接入 setup 主流程

**Files:**
- Modify: `scripts/vwr.ps1`
- Modify: `scripts/README.md`
- Modify: `README.md`

**Step 1: 写失败测试**

补充回归断言：

- `Invoke-Setup` 命中状态时输出“跳过依赖安装”
- 未命中时仍调用安装流程
- 命中跳过后仍会执行 editable install

**Step 2: 运行测试确认失败**

Run:

```bash
.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q
```

Expected:

- 因 `Invoke-Setup` 尚未使用新判定层而失败

**Step 3: 写最小实现**

调整 `Invoke-Setup`：

- 先调用依赖状态判定
- 仅在需要时执行 `Invoke-UvPipInstall`
- 安装成功后刷新状态文件
- dev 成功时同步刷新 prod 状态

并更新文档说明：

- `setup` 命中有效依赖状态会跳过重新下载
- `setup -Dev` 在 dev 依赖有效时同样跳过

**Step 4: 运行测试确认通过**

Run:

```bash
.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q
```

Expected:

- 定向测试通过

**Step 5: 提交**

```bash
git add scripts/vwr.ps1 scripts/README.md README.md
git commit -m "docs(scripts): 更新 setup 依赖跳过说明"
```

### Task 3: 做定向验证并整理结果

**Files:**
- Modify: `docs/plans/2026-03-20-vwr-setup-dependency-shortcut-design.md`
- Modify: `docs/plans/2026-03-20-vwr-setup-dependency-shortcut.md`

**Step 1: 运行定向测试**

Run:

```bash
.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py tests/unit/test_powershell_script_encoding.py -q
```

Expected:

- 新增回归测试通过
- 既有 PowerShell 脚本文本回归不受影响

**Step 2: 记录验证结果**

在设计文档或计划文档中追加：

- 本次实际执行的命令
- 通过/失败情况
- 已知限制

**Step 3: 提交**

```bash
git add docs/plans/2026-03-20-vwr-setup-dependency-shortcut-design.md docs/plans/2026-03-20-vwr-setup-dependency-shortcut.md
git commit -m "docs(plans): 记录 setup 依赖跳过实施结果"
```

---

## 当前执行状态

- [x] Task 1 已完成：失败测试已落地，并验证过红灯到绿灯
- [x] Task 2 已完成：`Invoke-Setup` 已接入依赖跳过逻辑
- [x] Task 3 已完成：联合验证已通过并已记录结果

### 本次验证记录

- 首次红灯：`python -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q`
  - 结果：`6 failed`
  - 关键失败：`Test-SetupDependencyState` 尚不存在，`Invoke-Setup` 尚未接入跳过逻辑
- 最终绿灯：`python -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py tests/unit/test_powershell_script_encoding.py -q`
  - 结果：`13 passed`
