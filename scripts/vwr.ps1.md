# `vwr.ps1` 统一脚本入口使用说明（Windows PowerShell）

> 本仓库的自动化脚本已整合为单一入口：`.\scripts\vwr.ps1`。  
> 仅支持 **Windows PowerShell**（脚本会自动切换到项目根目录执行）。

---

## 1. 快速开始（推荐）

```powershell
# 1) 首次安装（创建 .venv + 安装依赖）
.\scripts\vwr.ps1 setup

# 2) 启动应用（带环境检查）
.\scripts\vwr.ps1 run
```

如你在国内网络环境，建议显式指定镜像与 PyTorch 后端以提升速度：

```powershell
# 典型国内加速：清华镜像 + CPU 版 PyTorch
.\scripts\vwr.ps1 setup -TorchBackend cpu -DefaultIndex "https://pypi.tuna.tsinghua.edu.cn/simple"
```

---

## 2. 通用用法

```powershell
.\scripts\vwr.ps1 <command> [arg1] [arg2] [options]
```

- `<command>`：子命令（见下文）。
- `arg1/arg2`：位置参数（当前主要用于 `test` 的测试类型；`arg2` 预留，暂未使用）。
- `-Verbose`：PowerShell 原生参数（脚本已启用 `CmdletBinding()`），用于输出更多调试信息。

查看内置帮助：

```powershell
.\scripts\vwr.ps1 help
.\scripts\vwr.ps1 help -Verbose
```

---

## 3. 子命令详解

### 3.1 `setup`：创建虚拟环境并安装依赖

功能：
- 自动安装/检测 `uv`
- 使用 `uv venv` 创建 `.venv`（默认 Python **3.12.10**）
- 安装 `requirements.txt` 或（`-Dev`）安装 `requirements-dev.txt`

> 提示：如果你本机已存在 `.venv` 且 Python 版本不是 3.12.10，执行 `setup` 时会提示是否重建虚拟环境；可添加 `-Force` 跳过确认。

常用示例：

```powershell
# 安装运行依赖
.\scripts\vwr.ps1 setup

# 安装开发依赖（pytest/black/mypy/bandit/pyinstaller 等）
.\scripts\vwr.ps1 setup -Dev

# 指定 Python 解释器（例如 3.12.10）
.\scripts\vwr.ps1 setup -Python "3.12.10"

# PyTorch 后端选择（建议无 GPU 时用 cpu）
.\scripts\vwr.ps1 setup -TorchBackend cpu

# 指定默认索引镜像（强烈建议国内网络使用）
.\scripts\vwr.ps1 setup -DefaultIndex "https://pypi.tuna.tsinghua.edu.cn/simple"

# 多索引策略（默认 first-index）
.\scripts\vwr.ps1 setup -IndexStrategy first-index
```

参数说明（节选）：
- `-Dev`：安装 `requirements-dev.txt`
- `-Python <selector>`：传给 `uv venv --python ...`
- `-TorchBackend <auto|cpu|cu118|cu121|cu124|...>`：传给 `uv pip install --torch-backend ...`
- `-DefaultIndex <url>`：传给 `uv pip install --default-index ...`
- `-IndexStrategy <first-index|unsafe-first-match|unsafe-best-match>`：传给 `uv pip install --index-strategy ...`

> 提示：脚本会在创建 `.venv` 前，自动删除旧的 `venv/`（不带点）目录，避免混用旧环境。

---

### 3.2 `run`：环境检查后启动 `main.py`

功能：
- 检查 `.venv`、关键依赖、FFmpeg、配置文件
- `-AutoFix` 时可自动执行 `setup`、并在**用户配置目录**自动生成 `config.ini`（来自 `config.ini.example`）
- 使用 `.venv\Scripts\python.exe` 启动 `main.py`

常用示例：

```powershell
# 标准启动（推荐）
.\scripts\vwr.ps1 run

# 自动修复常见问题（缺 .venv / 缺依赖 / 缺 config.ini）
.\scripts\vwr.ps1 run -AutoFix

# 跳过环境检查（不推荐）
.\scripts\vwr.ps1 run -SkipChecks
```

---

### 3.3 `quality`：代码质量检查（需开发依赖）

功能：
- Black：格式检查/格式化
- Flake8：风格检查
- MyPy：类型检查（`-Quick` 会跳过）
- Bandit：安全检查（`-Quick` 会跳过）

常用示例：

```powershell
# 运行所有检查
.\scripts\vwr.ps1 quality

# 自动格式化（Black）
.\scripts\vwr.ps1 quality -Fix

# 快速模式：跳过 MyPy + Bandit
.\scripts\vwr.ps1 quality -Quick

# 仅跑某一类检查
.\scripts\vwr.ps1 quality -Check format
.\scripts\vwr.ps1 quality -Check style
.\scripts\vwr.ps1 quality -Check type
.\scripts\vwr.ps1 quality -Check security
```

> 提示：`quality/test/coverage/ci` 需要先执行 `.\scripts\vwr.ps1 setup -Dev` 安装开发依赖。

---

### 3.4 `test`：运行测试

用法：

```powershell
.\scripts\vwr.ps1 test <type> [-Quick] [-Coverage] [-Performance] [-Report]
```

`<type>` 可选：
- `unit`：运行 `tests/unit`
- `integration`：运行 `pytest -m integration`
- `quality`：等价于 `.\scripts\vwr.ps1 quality`
- `audio` / `preferences` / `e2e`：运行对应的 PowerShell 测试脚本（位于 `tests/`）
- `all`：运行全部 pytest；非 `-Quick` 时会额外运行 PowerShell 端到端/音频/偏好测试

常用示例：

```powershell
# 单元测试（建议先跑这个）
.\scripts\vwr.ps1 test unit

# 快速单测（跳过标记 slow 的用例）
.\scripts\vwr.ps1 test unit -Quick

# 全量测试（会更慢）
.\scripts\vwr.ps1 test all

# 全量测试 + 覆盖率 + 性能基准（可选）
.\scripts\vwr.ps1 test all -Coverage -Performance -Report
```

关键说明：
- 若关键依赖（如 `torch/ultralytics`）缺失，脚本会直接给出明确提示，避免 pytest 在收集阶段报难以理解的 `ImportError`。  
  解决方式通常是：`.\scripts\vwr.ps1 setup -Dev`（必要时加 `-TorchBackend cpu` / `-DefaultIndex`）。

---

### 3.5 `coverage`：覆盖率报告（pytest-cov）

功能：
- 生成终端覆盖率输出（含 missing 行）
- 生成 HTML 覆盖率报告到：`logs/htmlcov/index.html`

常用示例：

```powershell
# 生成覆盖率报告
.\scripts\vwr.ps1 coverage

# 覆盖率不足时失败（用于 CI）
.\scripts\vwr.ps1 coverage -FailOnLow -MinCoverage 80

# 生成后自动打开 HTML 报告
.\scripts\vwr.ps1 coverage -OpenReport
```

---

### 3.6 `perf`：性能基准测试（生成 JSON 报告）

功能：
- 运行轻量 CPU 基准测试
- 可选记录 GPU/内存信息
- 输出 JSON 报告到 `logs/`（可自定义路径）

常用示例：

```powershell
# 默认性能测试（5 次迭代）
.\scripts\vwr.ps1 perf

# 快速模式
.\scripts\vwr.ps1 perf -Quick

# 自定义迭代次数
.\scripts\vwr.ps1 perf -Iterations 10

# 输出到指定文件
.\scripts\vwr.ps1 perf -PerfReportPath "logs/perf.json"

# 记录 GPU / 内存信息（需要环境支持）
.\scripts\vwr.ps1 perf -GPUProfile -MemoryProfile
```

---

### 3.7 `build`：PyInstaller 打包（输出到 `release/`）

功能：
- 确保安装 `PyInstaller`
- 默认会先跑单元测试（可 `-SkipTests` 跳过）
- 产物复制到 `release/` 并生成 `release/VERSION.txt`

常用示例：

```powershell
# 标准构建（会先跑 unit 测试）
.\scripts\vwr.ps1 build

# 跳过构建前测试
.\scripts\vwr.ps1 build -SkipTests

# 构建前测试使用 Quick（跳过 slow）
.\scripts\vwr.ps1 build -Quick
```

---

### 3.8 `clean`：清理缓存/日志

功能：
- 清理 `.mypy_cache`、`.pytest_cache`、`.coverage*`、`logs/*.log`
- 递归清理 `app/` 与 `tests/` 下的 `__pycache__`、`*.pyc`、`*.pyo`

常用示例：

```powershell
# 交互确认后清理
.\scripts\vwr.ps1 clean

# 强制清理（不询问）
.\scripts\vwr.ps1 clean -Force
```

---

### 3.9 `ci`：CI 模式（JSON 输出 + 退出码）

功能：
- 顺序执行：`quality` → `unit` → `coverage`（可跳过）→ `perf`（可跳过）
- 输出 JSON 结果到文件（默认 `ci-artifacts/ci-results.json`）
- 失败会返回非 0 退出码

常用示例：

```powershell
# 默认 CI（会跑 quality/unit/coverage/perf）
.\scripts\vwr.ps1 ci

# 快速 CI（加速）
.\scripts\vwr.ps1 ci -Quick

# 跳过覆盖率/性能
.\scripts\vwr.ps1 ci -SkipCoverage -SkipPerformance

# 自定义输出与制品目录
.\scripts\vwr.ps1 ci -OutputFile "ci-results.json" -ArtifactsDir "ci-artifacts" -TimeoutMinutes 45
```

---

## 4. `uv` 下载加速与镜像配置（强烈建议国内环境使用）

### 4.1 推荐做法（两种任选其一）

**方式 A：命令行显式指定（最直观）**

```powershell
.\scripts\vwr.ps1 setup -DefaultIndex "https://pypi.tuna.tsinghua.edu.cn/simple"
```

**方式 B：设置环境变量（一次设置，多次生效）**

```powershell
$env:UV_DEFAULT_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
.\scripts\vwr.ps1 setup
```

### 4.2 缓存目录（减少重复下载）

将缓存放在更快/空间更大的磁盘（例如 `D:`）：

```powershell
$env:UV_CACHE_DIR = "D:\uv-cache"
.\scripts\vwr.ps1 setup
```

脚本支持的相关环境变量：
- `VWR_UV_DEFAULT_INDEX` / `UV_DEFAULT_INDEX` / `PIP_INDEX_URL`
- `VWR_UV_CACHE_DIR` / `UV_CACHE_DIR`

> 脚本策略：若你未显式传入 `-DefaultIndex`，会依次尝试读取上述环境变量；在中国常见环境下还会自动选用镜像作为默认索引（可随时用 `-DefaultIndex` 覆盖）。

---

## 5. 常见问题（FAQ）

### 5.1 PowerShell 执行策略导致无法运行脚本？

建议在当前终端临时允许执行（不改系统策略）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\vwr.ps1 help
```

### 5.2 `test/quality/coverage/ci` 提示缺少 `pytest/black/...`？

这些属于开发依赖，请先安装：

```powershell
.\scripts\vwr.ps1 setup -Dev
```

### 5.3 安装 `torch/ultralytics` 很慢或经常失败？

优先尝试：

```powershell
.\scripts\vwr.ps1 setup -TorchBackend cpu -DefaultIndex "https://pypi.tuna.tsinghua.edu.cn/simple"
```

如你需要 CUDA 版本，请确保 CUDA/驱动版本匹配，并选择合适的 `-TorchBackend`（如 `cu121` 等）。
