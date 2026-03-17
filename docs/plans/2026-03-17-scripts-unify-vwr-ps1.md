# 脚本整合为单入口 `vwr.ps1` Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `scripts/` 下分散的 PowerShell 脚本整合为单一入口 `scripts/vwr.ps1`，并同步更新 `README.md`/`docs` 引用，同时优化 `uv` 依赖安装体验（减少重复安装、提供镜像与 PyTorch 后端选择）。

**Architecture:** 新增一个“子命令”风格的 PowerShell CLI（`vwr.ps1 <command> [options]`），内部以函数分区实现 `setup/run/test/quality/coverage/perf/build/clean/ci/help` 等能力；删除旧脚本并在文档中统一改用 `vwr.ps1`。

**Tech Stack:** Windows PowerShell、`uv`、Python（`.venv`）、pytest/black/flake8/mypy/pyinstaller（开发依赖）。

---

### Task 1: 新增统一入口脚本骨架

**Files:**
- Create: `scripts/vwr.ps1`

**Step 1: 设计子命令与参数约定**
- 约定命令：`help/setup/run/test/quality/coverage/perf/build/clean/ci`
- 约定关键参数：
  - `setup`: `-Dev`, `-Python`, `-TorchBackend`, `-DefaultIndex`, `-IndexStrategy`
  - `run`: `-AutoFix`, `-SkipChecks`, `-Verbose`
  - `test`: `unit/integration/all/audio/e2e/preferences` + `-Quick`, `-Verbose`
  - `quality`: `-Fix`, `-Quick`, `-Verbose`
  - `coverage`: `-MinCoverage`, `-FailOnLow`, `-OpenReport`
  - `perf`: `-Quick`, `-Iterations`, `-MemoryProfile`, `-GPUProfile`
  - `build`: `-SkipTests`, `-Quick`
  - `clean`: `-Force`
  - `ci`: `-OutputFile`, `-ArtifactsDir`, `-TimeoutMinutes`

**Step 2: 编写通用工具函数**
- 项目根目录定位、日志与彩色输出、`.venv` 路径解析、`uv` 检测与安装（优先 winget、回退 pip）、依赖安装封装（`uv pip install --python ...`）。

---

### Task 2: 将旧脚本能力迁移为子命令

**Files:**
- Modify: `scripts/vwr.ps1`

**Step 1: 实现 `setup`**
- 创建 `.venv`（支持 `-Python`）
- 一次性安装依赖（默认 `requirements.txt`；`-Dev` 安装 `requirements-dev.txt`）
- `uv` 安装优化：支持 `--torch-backend`、`--default-index`、`--index-strategy`

**Step 2: 实现 `run`**
- 环境检查（可跳过），`config.ini` 自动修复（仅在 `-AutoFix`）
- 缺依赖时给出明确修复命令（必要时可在 `-AutoFix` 自动安装）
- 使用 `.venv\\Scripts\\python.exe` 启动 `main.py`

**Step 3: 实现 `quality/test/coverage/perf/build/clean/ci`**
- `quality`: `python -m black/flake8/mypy`
- `test`: `python -m pytest` + 兼容运行 `tests/*.ps1`（音频/偏好/端到端）
- `coverage`: 使用 `pytest --cov` 生成报告并检查阈值
- `perf`: 复用现有性能基准思路，产出 JSON 报告到 `logs/`
- `build`: 复用 PyInstaller 打包逻辑，支持跳过测试
- `clean`: 清理常见缓存/日志
- `ci`: 无交互输出 + 退出码 + 可选 JSON 结果文件

---

### Task 3: 同步更新文档引用（仅 Windows）

**Files:**
- Modify: `README.md`
- Modify: `docs/complete-technical-documentation.md`
- Modify: `tests/test_data/README.md`
- Create: `scripts/vwr.ps1.md`
- Modify: `scripts/README.md`

**Step 1: 替换所有旧脚本调用**
- `setup.ps1` → `.\scripts\vwr.ps1 setup`
- `start.ps1` → `.\scripts\vwr.ps1 run`
- `check-quality.ps1` → `.\scripts\vwr.ps1 quality`
- `test.ps1` → `.\scripts\vwr.ps1 test`
- 其它脚本同理替换为相应子命令

**Step 2: 删除 Linux/macOS 相关段落**
- 移除 `./scripts/*.sh` 说明（仓库当前不提供对应脚本）

---

### Task 4: 删除冗余脚本（保留单入口）

**Files:**
- Delete: `scripts/build.ps1`
- Delete: `scripts/check-quality.ps1`
- Delete: `scripts/ci-test.ps1`
- Delete: `scripts/clean-cache.ps1`
- Delete: `scripts/install.ps1`
- Delete: `scripts/run-tests.ps1`
- Delete: `scripts/setup.ps1`
- Delete: `scripts/start.ps1`
- Delete: `scripts/test-all.ps1`
- Delete: `scripts/test-coverage.ps1`
- Delete: `scripts/test-performance.ps1`
- Delete: `scripts/test.ps1`

---

### Task 5: 验证与回归

**Step 1: 基础可用性**
- Run: `.\scripts\vwr.ps1 help`
- Expected: 打印帮助与子命令列表，退出码 0

**Step 2: 快速测试（≤60s 目标）**
- Run: `.\scripts\vwr.ps1 test unit -Quick`
- Expected: pytest 正常执行；若环境未安装开发依赖，应提示运行 `.\scripts\vwr.ps1 setup -Dev`

**Step 3: 文档引用一致性**
- Run: `rg -n -S \"\\.\\\\scripts\\\\(setup|start|test|check-quality|test-all|test-coverage|test-performance|ci-test|clean-cache)\\.ps1\" README.md docs -g\"*.md\"`
- Expected: 无匹配结果
