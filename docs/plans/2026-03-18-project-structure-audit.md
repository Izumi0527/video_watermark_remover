# 项目目录结构梳理与优化计划 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 详细梳理本仓库目录结构、识别历史遗留/冗余/不一致点，并给出分阶段、可回滚的目录结构优化执行方案（在不破坏现有功能的前提下优先低风险改进）。

**Architecture:** 采用“现状快照 → 职责映射 → 问题清单 → 目标结构草案 → 迁移与验证”的流水线推进；所有涉及**移动/删除**的改动必须先与负责人确认，并以自动化测试/冒烟启动作为安全网。

**Tech Stack:** Python 3.8+、PyQt6 GUI、OpenCV/Numpy/Pillow、pytest（含 pytest-qt）、setuptools/pyproject、PowerShell 脚本（`scripts/vwr.ps1`）。

---

## 0) 执行状态（截至 2026-03-18）

- [ ] Task 1：冻结现状与建立基线（未落盘目录树快照）
- [x] Task 2：配置与分发清单对齐
- [ ] Task 3：清理空目录/重复入口（待确认后执行）
- [x] Task 4：测试目录重分层与归档
- [ ] Task 5：可选的更大结构优化

## 1) 当前目录结构（摘要快照）

> 注：本快照聚焦“代码/配置/脚本/测试/文档”，运行产物（`.venv`、`__pycache__`、`logs/` 等）仅在诊断中提及。

```text
video_watermark_remover/
  main.py                         # GUI/入口（pyproject scripts 指向 main:main）
  pyproject.toml                  # 依赖/打包/工具配置（black/mypy/pytest 等）
  requirements.txt                # 依赖清单（与 pyproject 存在重复维护）
  requirements-dev.txt
  config.ini                      # 本地配置（.gitignore 已忽略）
  config.ini.example              # 配置模板（建议用于生成“用户配置目录”的 config.ini）
  LICENSE                         # 许可证（MIT）
  app/                            # 主 Python 包（setuptools packages=["app"]）
    assets/
      icons/
    config/
      config_manager.py
      validators.py
      preferences/                # 新版偏好设置包
      styles/                     # 样式/主题
      preferences_defaults.py     # 疑似历史遗留（与 preferences/ 重叠）
      preferences_storage.py
      preferences_validator.py
      user_preferences_manager.py
    core/
      exceptions.py
      ai/                         # AI 检测/修复相关（YOLO/修复器/GPU 监控等）
      audio/                      # 音频抽取/合并/FFmpeg 处理
      video/                      # 视频帧读写/流水线/多进程处理
    ui/
      main_window.py
      signal_handler.py
      components/                 # 控件组合（panel/widget）
      widgets/                    # 可复用控件（含 advanced、batch 子目录）
      utils/
      dialogs/                    # 当前为空（仅 __init__.py）
    utils/
      logger_setup.py
      metrics.py
      model_downloader.py
      utils.py
    services/                     # 当前为空目录

  scripts/
    vwr.ps1                       # 统一的开发/运行脚本入口
    README.md                     # 脚本文档统一入口（含 vwr.ps1 详细说明）
    vwr.ps1.md                    # 兼容占位：内容已合并到 README.md

  tests/
    conftest.py
    unit/                         # 单测目录（存在部分单测）
    integration/                  # 集成测试目录（已归档 test_*.py）
    e2e/                          # 端到端测试目录
      ps1/                        # PowerShell 端到端脚本
    app/config/...                # 细分到 app/config 的单测
    core/ai/video/...             # 细分到 core 的单测
    test_data/                    # 测试素材（含 configs、视频/图片/模型样本）

  docs/
    plans/                        # 计划文档
    complete-technical-documentation.md
    frontend_ui_analysis.md
    parameters_analysis.md
    yolo_model_upgrade.md

  models/                         # 大模型文件放置（当前 yolo11*.pt 在 .gitignore 中）
  discuss/                        # 讨论/优化记录
  screenshot/                     # 当前为空（疑似产物目录）
  test_output/                    # 当前为空（命名与 .gitignore 的 .test_output/ 不一致）
```

---

## 2) 结构诊断：不一致与可优化点（按优先级）

### A. “目录存在但为空/名不副实”
- [ ] `app/services/`、`app/ui/dialogs/` 为空：需要确认是否保留作为未来扩展点；若确认无用可删除（删除属于高风险操作，需要明确确认）。
- [x] `tests/integration/` 曾仅有 `__init__.py`：已将顶层 `tests/test_*.py` 归档至 `tests/integration/`，并新增 `tests/e2e/ps1/` 承载 PowerShell 端到端脚本。
- [ ] `screenshot/` 当前为空：若为运行产物目录，建议统一命名与 `.gitignore` 策略并明确约定。
- [x] `test_output/` 命名/忽略不一致：已补充 `.gitignore` 忽略 `test_output/`（是否保留目录本身仍待确认）。

### B. 配置目录与打包配置疑似脱节（影响分发/可维护性）
- [x] `.gitignore`、`MANIFEST.in`、`pyproject.toml` 中历史遗留引用 `configs/*.ini`：已移除历史引用；保留 `config.ini.example` 作为模板，并统一以“用户配置目录”为准。
- [x] `MANIFEST.in` 引用不存在文件：已对齐真实结构，避免 sdist 打包失败或分发包缺文件。

### C. 同一领域出现“新旧两套组织方式”的迹象
- [ ] `app/config/preferences/` 已存在包结构，但同目录还有 `preferences_defaults.py` / `preferences_storage.py` / `preferences_validator.py` / `user_preferences_manager.py` 等：需要确认它们与 `preferences/` 的关系，避免后续维护产生重复逻辑与入口混乱。

### D. 测试目录分层混杂（影响可读性与执行策略）
- [x] 顶层 `tests/test_*.py` 及 `tests/*.ps1` 散落：已归档到 `tests/integration/` 与 `tests/e2e/ps1/`。
- [ ] 统一一个“主分层”（unit/integration/e2e）并把“按模块细分”作为二级目录：尚未完全统一（`tests/app/...`、`tests/core/...` 等历史分层仍保留）。

### E. “运行产物目录”策略需要一致（避免误提交与污染仓库）
- [ ] 当前存在 `__pycache__`（根目录与包内）、`.venv/`、`logs/` 等，虽已被 `.gitignore` 覆盖，但建议在文档中明确“哪些目录是可删除的运行产物、哪些是必须保留的占位目录”。

---

## 3) 是否建议调整与优化？

建议做，但分两档推进：

1) **低风险整理（推荐先做）**：不改变导入路径/对外接口，仅对齐目录职责、归档测试、补齐 configs 目录与打包清单一致性、修正 `.gitignore` 与产物目录策略。
2) **可选结构重构（视收益再做）**：例如引入 `src/` 布局、将包名从 `app` 重命名为更语义化的包名、对 `core/video` 的流水线进一步拆分模块边界等；该档会影响导入路径/脚本入口，需更严格的回归测试与迁移策略。

---

## 4) 执行计划（分阶段，可回滚；后续执行前需要确认）

> 说明：本节为可执行清单与里程碑；截至 2026-03-18，Task 2 与 Task 4 已执行完成（详见第 6/7 节），其余任务保留为后续待办。

### Task 1：冻结现状与建立基线（可回滚点）（未完成）

**Files:**
- Modify: `docs/plans/2026-03-18-project-structure-audit.md`
- (Optional) Create: `docs/structure/current-tree.txt`

**Step 1：生成目录树快照（深度建议 3）并保存到文档**
- Run（PowerShell）：
  - `Get-ChildItem -Force -Recurse | Select-Object FullName`
- 产出：把“代码/配置/脚本/测试/文档”相关路径整理成快照（避免把 `.venv/`、`__pycache__/` 等噪声写入）。

**Step 2：确认 `.gitignore` 对关键产物目录的覆盖**
- Run：
  - `git status --porcelain`
- 期望：无未忽略的大体积产物被纳入版本控制。

### Task 2：配置与分发清单对齐（低风险）（已完成）

**Files:**
- Modify: `pyproject.toml`
- Modify: `MANIFEST.in`
- Modify: `.gitignore`
- Modify: `scripts/vwr.ps1`
- Modify: `README.md`
- Modify: `config.ini.example`
- Create: `LICENSE`

**Step 1：确认当前配置加载逻辑使用的默认路径**
- Run：
  - `rg -n \"config\\.ini|configs/|default_config\" \"./app\" \"./main.py\"`

**Step 2：确定“推荐的配置路径契约”**
- 推荐契约：以 `ConfigManager.get_config_path()` 返回的“用户配置目录”为准；仓库中的 `config.ini.example` 仅作为模板与示例。

**Step 3：对齐 `pyproject.toml` 的 package-data 与 `MANIFEST.in`**
- 目标：打包时包含默认配置与必要资源，不引用不存在文件。

**Step 4：补充文档说明**
- 在 `README.md` 写清楚：
  - 默认配置路径
  - 用户如何复制与覆盖配置
  - 不应提交的本地配置文件

**Step 5：同步脚本 AutoFix 行为**
- `scripts/vwr.ps1 run -AutoFix`：从 `config.ini.example` 生成配置文件到“用户配置目录”，并在输出中打印实际路径。

### Task 3：清理空目录/重复入口（高风险操作点：删除/移动需确认）（未开始）

**Files:**
- Potential Delete: `app/services/`（若确认不再需要）
- Potential Delete: `app/ui/dialogs/`（若确认不再需要）
- Potential Refactor: `app/config/*.py` 与 `app/config/preferences/*` 的职责合并/迁移

**Step 1：扫描空目录与重复模块**
- Run：
  - `Get-ChildItem -Directory -Recurse | Where-Object { (Get-ChildItem -Force $_.FullName | Measure-Object).Count -eq 0 }`
  - `rg -n \"preferences_defaults|preferences_storage|preferences_validator|user_preferences_manager\" \"./app\"`

**Step 2：与负责人确认删除/迁移清单**
- 输出“候选删除/迁移列表 + 影响范围 + 回滚方式”，得到明确确认后再执行。

### Task 4：测试目录重分层与归档（中风险：移动文件需确认）（已完成）

**Files:**
- Potential Move: `tests/test_*.py` → `tests/integration/` 或 `tests/e2e/`
- Potential Move: `tests/*.ps1` → `tests/e2e/ps1/`
- Potential Refactor: `pyproject.toml`（pytest testpaths/markers 可能需要对齐）

**Step 1：为测试目录设定单一“主分层”并形成约定**
- 推荐：
  - `tests/unit/...`
  - `tests/integration/...`
  - `tests/e2e/...`
  - `tests/test_data/...` 保持不变

**Step 2：先做“无语义变更”的移动（仅路径变更）**
- 要求：每次移动后都执行一次最小子集测试，避免一次性大搬迁。

**Step 3：验证执行耗时与稳定性**
- Run：
  - `python -m pytest -q`
- 目标：单测在合理时间内完成（若超过 60s，需拆分 slow 标记或分组运行）。

### Task 5：可选的更大结构优化（仅在低风险整理完成后评估）（未开始）

**候选方向（择一或不做）：**
- `src/` 布局：将 `app/` 移入 `src/app/`，避免“从工作目录误导入本地包”的典型坑。
- 包名语义化：将 `app` 改为 `video_watermark_remover`（变更面较大，需谨慎）。
- `app/core/video/` 进一步按职责拆分（IO、pipeline、process、utils），减少“一个目录下聚集过多概念”的维护成本。

**验证基线：**
- GUI 冒烟：`python main.py` 能正常启动主窗口（Windows/Qt 环境）。
- 单测：`python -m pytest -q` 通过。

---

## 5) 交付物与验收标准（面向后续执行）

**交付物：**
- 目录结构梳理文档（本文件）
- 已对齐的 `pyproject.toml` / `MANIFEST.in` / `.gitignore` / `README.md` / `scripts/vwr.ps1` / `config.ini.example`
- 新增的 `LICENSE`
- （如实施）重整后的测试目录与可稳定执行的测试命令

**验收标准：**
- 目录职责清晰，新增/移动/删除均可追溯（有确认记录与回滚点）
- 运行产物目录不会误提交
- 打包配置与实际文件一致（不引用不存在文件）
- 关键测试通过，且单测耗时可控（必要时标记 slow 并默认跳过）

---

## 6) 已实施变更（2026-03-18）

> 说明：以下变更均为“低风险对齐”，未涉及大规模文件移动与删除。

- `pyproject.toml`：改为自动发现 `app*` 包，并将 `main.py` 作为 `py-modules` 纳入打包；修正 package-data（仅保留 `app/assets`）。
- `MANIFEST.in`：移除不存在文件引用，补充脚本/文档/资源；显式排除 `models/*.pt`，避免将大模型打包进 sdist。
- `LICENSE`：补齐 MIT License 文件，修复 README 徽章链接。
- `.gitignore`：移除历史遗留的 `configs/*.ini` 规则；补充忽略 `test_output/`。
- `scripts/vwr.ps1`：`run -AutoFix` 从 `config.ini.example` 生成配置到“用户配置目录”，并打印实际路径。
- `README.md`、`config.ini.example`、`scripts/README.md`（原 `scripts/vwr.ps1.md`）：更新配置文件位置与生成方式说明，减少误导。
- `tests/`：将顶层“集成/端到端脚本”归档到 `tests/integration/`、`tests/e2e/ps1/`，并同步 `scripts/vwr.ps1` 与 `tests/test_data/README.md` 的引用路径。

---

## 7) 已完成的高风险操作（2026-03-18）

### 7.1 测试目录搬迁（批量移动文件）

**新增目录：**
- `tests/e2e/ps1/`：归档 PowerShell 端到端脚本
- `tests/e2e/`：归档较重的 Python 端到端测试（如 GPU e2e）

**已移动文件：**
- `tests/test_audio_processing.ps1` → `tests/e2e/ps1/test_audio_processing.ps1`
- `tests/test_end_to_end.ps1` → `tests/e2e/ps1/test_end_to_end.ps1`
- `tests/test_user_preferences.ps1` → `tests/e2e/ps1/test_user_preferences.ps1`
- `tests/test_phase5_gpu_e2e.py` → `tests/e2e/test_phase5_gpu_e2e.py`

**已归档到集成测试目录（`tests/integration/`）：**
- `tests/test_aihandler_gpu_integration.py`
- `tests/test_batch_processing.py`
- `tests/test_dl_inpainter_gpu.py`
- `tests/test_multiprocess_video.py`
- `tests/test_mvp.py`
- `tests/test_phase3.py`
- `tests/test_pipeline_video.py`
- `tests/test_utilities.py`
- `tests/test_video_preview.py`
- `tests/test_video_processor.py`
- `tests/test_yolo_detector.py`
- `tests/test_yolo_pipeline.py`

**注意：**
- 以上部分测试/脚本包含“手工运行脚本化”的路径逻辑（如 `sys.path.insert(...)`）。当前仍可在仓库根目录运行 pytest；若后续希望支持“从任意目录直接运行单个脚本/用例”，可再统一改为“向上查找 `pyproject.toml` 作为仓库根目录”的实现。
