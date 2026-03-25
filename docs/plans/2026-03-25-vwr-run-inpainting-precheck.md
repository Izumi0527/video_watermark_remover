# vwr.ps1 启动前深度修复模型体检 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `scripts/vwr.ps1 run` 的环境检查阶段补充深度修复模型体检，提前提示 LaMa / 旧 U-Net 的缺失、路径错误或可直接使用状态，但不阻止应用降级启动。

**Architecture:** 复用现有 `run` 启动前检查结构，把深度修复体检封装成独立 PowerShell 小函数，集中处理环境变量、配置项和常见候选路径的解析与提示；测试继续沿用 PowerShell harness，先锁定输出行为，再做最小脚本接入。

**Tech Stack:** PowerShell、pytest、subprocess

---

### Task 1: 锁定 run 启动前体检输出行为

**Files:**
- Modify: `tests/unit/test_vwr_setup_dependency_shortcut.py`
- Modify: `scripts/vwr.ps1`

**Step 1: Write the failing test**

新增脚本测试，覆盖三类场景：

- 未配置任何 LaMa / 旧 U-Net 资产时，输出下载提示与环境变量示例
- 已配置 LaMa 路径但文件不存在时，输出明确 warning
- 已存在有效 `big-lama.pt` 时，输出可直接使用的成功提示

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q -k "startup_precheck"`

Expected: FAIL，说明当前脚本尚未提供所需的启动前体检函数或输出。

**Step 3: Write minimal implementation**

实现：

- 在 `scripts/vwr.ps1` 中新增深度修复模型体检辅助函数
- 在 `Invoke-Run` 的环境检查阶段调用体检函数
- 保持“软检查”，仅提示，不直接阻止启动

**Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py -q -k "startup_precheck"`

Expected: PASS

**Step 5: Run direct script verification**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\vwr.ps1 run`

Expected: 在“环境检查”阶段先输出深度修复模型体检结果，再继续启动 `main.py`。
