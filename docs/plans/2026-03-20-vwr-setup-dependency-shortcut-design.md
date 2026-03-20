# `vwr.ps1 setup` 依赖跳过设计

**日期**：2026-03-20

**背景**

当前 `.\scripts\vwr.ps1 setup` 每次都会执行 `uv pip install -r requirements*.txt`。  
当 `.venv` 已存在且依赖未变化时，这会重复触发依赖解析与下载，影响本地开发效率。

**目标**

- 在 `.venv` 已存在、对应依赖集已满足时，跳过重复依赖安装。
- 保留现有 `setup` / `setup -Dev` 入口与 `editable install` 行为。
- 不把“虚拟环境存在”误判为“依赖完整”。

---

## 方案选择

本次采用 **方案 C（折中方案）**：

1. 以 `requirements.txt` / `requirements-dev.txt` 的内容签名作为主判据。
2. 结合轻量健康检查，避免状态文件存在但环境已被手动破坏时误跳过。
3. 即便跳过依赖安装，仍继续执行 `Install-EditableProject -NoDeps` 与导入验证。

---

## 设计要点

### 1. 依赖状态文件

在仓库内新增 setup 状态文件目录，例如：

- `.cache/setup-state/requirements.json`
- `.cache/setup-state/requirements-dev.json`

状态文件至少记录：

- 目标依赖集标识（prod / dev）
- 当前依赖签名
- Python 可执行文件路径
- Python 版本
- 记录时间

### 2. 依赖签名规则

对目标 requirements 文件生成稳定签名：

- `requirements.txt`：仅基于自身内容
- `requirements-dev.txt`：除自身内容外，还要递归纳入 `-r requirements.txt` 的内容

这样当基础依赖变更时，dev 状态也会失效。

### 3. 轻量健康检查

命中状态文件后，不直接跳过，而是再检查少量探针包是否可被当前 `.venv` 识别：

- prod：`PyQt6`、`numpy`、`Pillow`、`torch`
- dev：在 prod 基础上追加 `pytest`、`black`、`mypy`

如果任一探针包缺失，则判定状态失效，重新安装。

### 4. prod / dev 兼容策略

- `setup` 只要求 prod 状态有效。
- `setup -Dev` 要求 dev 状态有效。
- 执行 `setup -Dev` 成功后，同时刷新 prod 与 dev 两份状态文件。

这样普通 `setup` 可复用先前完整 dev 环境的状态。

### 5. 不变行为

以下行为保持不变：

- `.venv` 创建与 Python 版本校验
- `uv` 索引、镜像与缓存目录逻辑
- `Install-EditableProject -NoDeps`
- `Assert-ProjectImportable`

---

## 风险与控制

### 风险 1：状态文件存在但环境已损坏

控制：

- 追加探针包健康检查
- 探针失败时自动回退到重新安装

### 风险 2：`requirements-dev.txt` 仅记录自身签名，无法感知 `requirements.txt` 变化

控制：

- 递归解析 `-r` 引用并一并纳入签名

### 风险 3：误跳过 editable install

控制：

- 仅跳过 `Invoke-UvPipInstall`
- `Install-EditableProject -NoDeps` 仍每次执行

---

## 验证策略

1. 先新增脚本级单元回归测试，覆盖：
   - 状态文件命中且探针通过时返回“可跳过”
   - 状态文件命中但探针失败时返回“不可跳过”
2. 再实现脚本逻辑。
3. 最后执行定向 pytest 验证，并补充文档说明。

---

## 当前进展

- [x] 已新增 `tests/unit/test_vwr_setup_dependency_shortcut.py`
- [x] 已为 `scripts/vwr.ps1` 增加依赖状态签名、探针检查与状态文件读写
- [x] 已将依赖判定接入 `Invoke-Setup`
- [x] 已完成联合验证命令与结果摘要补录

### 联合验证结果

- 命令：`python -m pytest tests/unit/test_vwr_setup_dependency_shortcut.py tests/unit/test_powershell_script_encoding.py -q`
- 结果：`13 passed`
- 结论：新增依赖跳过逻辑已通过定向行为测试，且未破坏既有 PowerShell 脚本约束回归
