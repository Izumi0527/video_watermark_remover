# 项目目录结构梳理与优化计划 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 详细梳理本仓库目录结构、识别历史遗留/冗余/不一致点，并给出分阶段、可回滚的目录结构优化执行方案（在不破坏现有功能的前提下优先低风险改进）。

**Architecture:** 采用“现状快照 → 职责映射 → 问题清单 → 目标结构草案 → 迁移与验证”的流水线推进；所有涉及**移动/删除**的改动必须先与负责人确认，并以自动化测试/冒烟启动作为安全网。

**Tech Stack:** Python 3.8+、PyQt6 GUI、OpenCV/Numpy/Pillow、pytest（含 pytest-qt）、setuptools/pyproject、PowerShell 脚本（`scripts/vwr.ps1`）。

---

## 0) 执行状态（截至 2026-03-20）

- [x] Task 1：冻结现状与建立基线（目录树快照已落盘，并于 2026-03-20 复核）
- [x] Task 2：配置与分发清单对齐
- [x] Task 3：清理空目录/重复入口（已删除根目录残留 `app/` 与无引用的 `src/app/ui/dialogs/` 占位包）
- [x] Task 4：测试目录重分层与归档
- [x] Task 5：可选的更大结构优化（已完成 `src/` 布局 + editable install + `video` 模块二次拆分 + 文档同步）
- [x] Task 6：调试稳定后移除 `video` 兼容层（已完成兼容层收口、运行态 smoke、`test unit -Quick` 门禁与回滚点整理）
- 备注：`src/app/core/video/` 已在 2026-03-19 完成一轮 `modes/`、`workers/`、`utils/`、`thread.py` + 兼容层落地；2026-03-20 已进一步完成旧平铺兼容层删除、视频测试入口迁移、`scripts/task6_runtime_smoke.py` 运行态 smoke、`scripts/vwr.ps1 test unit -Quick` 转绿与回滚点整理。

## 1) 当前目录结构（摘要快照）

> 注：本快照已于 2026-03-20 重新扫描并落盘，聚焦“代码/配置/脚本/测试/文档”；运行产物（`.venv`、`__pycache__`、`logs/` 等）仅在诊断中提及。

```text
video_watermark_remover/
  main.py                         # 薄启动器（转发到 app.entrypoints:main）
  pyproject.toml                  # 依赖/打包/工具配置（black/mypy/pytest 等）
  requirements.txt                # 依赖清单（与 pyproject 存在重复维护）
  requirements-dev.txt
  config.ini                      # 本地配置（.gitignore 已忽略）
  config.ini.example              # 配置模板（建议用于生成“用户配置目录”的 config.ini）
  LICENSE                         # 许可证（MIT）
  src/
    app/                          # 主 Python 包（setuptools package-dir={"": "src"}）
      assets/
        icons/
      config/
        config_manager.py
        validators.py
        preferences/              # 新版偏好设置包
        styles/                   # 样式/主题
        preferences_defaults.py   # 兼容旧路径的薄封装，真实实现已收口到 preferences/
        preferences_storage.py
        preferences_validator.py
        user_preferences_manager.py
      core/
        exceptions.py
        ai/                       # AI 检测/修复相关（YOLO/修复器/GPU 监控等）
        audio/                    # 音频抽取/合并/FFmpeg 处理
        video/                    # 视频处理主模块
          modes/                  # 单进程 / 多进程 / 流水线模式
          workers/                # 帧读取/处理/写入、分块与音频任务
          utils/                  # 路径与背压等工具
          thread.py               # 视频线程主实现（已收口为唯一线程入口）
      ui/
        main_window.py
        signal_handler.py
        components/               # 控件组合（panel/widget）
        widgets/                  # 可复用控件（含 advanced、batch 子目录）
        utils/
      utils/
        logger_setup.py
        metrics.py
        model_downloader.py
        utils.py
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
    future/unit/                  # 暂挂/未来阶段单测
    app/config/...                # 细分到 app/config 的单测
    core/ai/video/...             # 细分到 core 的单测
    ai_module_tests.py 等顶层文件  # 历史测试入口仍在，主分层未完全收敛
    test_data/                    # 测试素材（含 configs、视频/图片/模型样本）

  docs/
    agents/                       # 子代理编组与调度说明（当前工作区已存在）
    plans/                        # 计划文档
    complete-technical-documentation.md
    frontend_ui_analysis.md
    parameters_analysis.md
    yolo_model_upgrade.md

  models/                         # 大模型文件放置（当前 yolo11*.pt 在 .gitignore 中）
  discuss/                        # 讨论/优化记录
```

---

## 2) 结构诊断：不一致与可优化点（按优先级）

### A. “目录存在但为空/名不副实”
- [x] `src/app/services/` 已删除：原空目录问题已消除。
- [x] `src/app/ui/dialogs/` 已删除：复扫 `src` / `tests` 未发现有效引用，确认其仅为历史占位包。
- [x] `tests/integration/` 曾仅有 `__init__.py`：已将顶层 `tests/test_*.py` 归档至 `tests/integration/`，并新增 `tests/e2e/ps1/` 承载 PowerShell 端到端脚本。
- [x] `screenshot/` 目录已不存在：原“空目录 + 命名/忽略策略”问题已随目录清理一并消除。
- [x] `test_output/` 命名/忽略不一致：已补充 `.gitignore` 忽略 `test_output/`（是否保留目录本身仍待确认）。

### B. 配置目录与打包配置疑似脱节（影响分发/可维护性）
- [x] `.gitignore`、`MANIFEST.in`、`pyproject.toml` 中历史遗留引用 `configs/*.ini`：已移除历史引用；保留 `config.ini.example` 作为模板，并统一以“用户配置目录”为准。
- [x] `MANIFEST.in` 引用不存在文件：已对齐真实结构，避免 sdist 打包失败或分发包缺文件。

### C. 同一领域出现“新旧两套组织方式”的迹象
- [x] `src/app/config/preferences/` 已确认是唯一真实实现；同级 `preferences_defaults.py` / `preferences_storage.py` / `preferences_validator.py` / `user_preferences_manager.py` 仅保留兼容旧路径的薄封装，后续只需逐步迁移历史测试 / E2E 的旧导入即可彻底收口入口。

### D. 测试目录分层混杂（影响可读性与执行策略）
- [x] 顶层 `tests/test_*.py` 及 `tests/*.ps1` 散落：已归档到 `tests/integration/` 与 `tests/e2e/ps1/`。
- [ ] 统一一个“主分层”（unit/integration/e2e）并把“按模块细分”作为二级目录：尚未完全统一（`tests/app/...`、`tests/core/...` 以及顶层 `tests/ai_*` / `tests/phase3_*` / `tests/ui_component_tests.py` 等历史分层仍保留）。

### E. “运行产物目录”策略需要一致（避免误提交与污染仓库）
- [x] 已明确运行产物目录约定：`__pycache__/`、`.pytest_cache/`、`.mypy_cache/`、`.cache/`、`.uv-cache*`、`logs/`、`.venv/` 视为可删除的本地运行产物；`tests/test_data/` 等保留结构/样本入口不应误删。

---

## 3) 是否建议调整与优化？

建议做，但分两档推进：

1) **低风险整理（推荐先做）**：不改变导入路径/对外接口，仅对齐目录职责、归档测试、补齐 configs 目录与打包清单一致性、修正 `.gitignore` 与产物目录策略。
2) **可选结构重构（视收益再做）**：例如引入 `src/` 布局、将包名从 `app` 重命名为更语义化的包名、对 `core/video` 的流水线进一步拆分模块边界等；该档会影响导入路径/脚本入口，需更严格的回归测试与迁移策略。

---

## 4) 执行计划（分阶段，可回滚；后续执行前需要确认）

> 说明：本节为可执行清单与里程碑；截至 2026-03-18，Task 2 与 Task 4 已执行完成（详见第 6/7 节），其余任务保留为后续待办。

### Task 1：冻结现状与建立基线（可回滚点）（已完成，2026-03-20 复核）

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

**2026-03-20 复核结果**
- 已刷新第 1 节目录快照，补入根目录残留 `app/` 空目录树、`tests/future/unit/`、`docs/agents/` 等当前结构信息。
- 已复核 `.gitignore` 对 `__pycache__/`、`.pytest_cache/`、`.cache`、`.venv`、`logs/`、`test_output/` 的覆盖；当前未见未忽略的大体积运行产物，但根目录残留 `app/` 空目录树仍会影响导入行为，需在 Task 3 处理中清理。

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

### Task 3：清理空目录/重复入口（高风险操作点：删除/移动需确认）（已完成，2026-03-20）

**Files:**
- Deleted: 根目录残留 `app/` 空目录树（未跟踪，且已确认仅为历史运行产物/空壳目录）
- Deleted: `src/app/ui/dialogs/`（仅含 `__init__.py`，复扫 `src` / `tests` 无有效引用）
- Deferred: `src/app/config/*.py` 与 `src/app/config/preferences/*` 的兼容层收口/迁移（保留到后续独立任务）

**Step 1：扫描空目录与重复模块**
- Run：
  - `Get-ChildItem -Directory -Recurse | Where-Object { (Get-ChildItem -Force $_.FullName | Measure-Object).Count -eq 0 }`
  - `rg -n \"preferences_defaults|preferences_storage|preferences_validator|user_preferences_manager\" \"./src/app\" \"./tests\"`

**Step 2：与负责人确认删除/迁移清单**
- 已按“候选删除/迁移列表 + 影响范围 + 回滚方式”完成复核，并在本轮明确确认后执行目录清理。

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

### Task 5：可选的更大结构优化（仅在低风险整理完成后评估）（已完成一轮 `src/` 布局落地）

**候选方向（择一或不做）：**
- [x] `src/` 布局：已将 `app/` 移入 `src/app/`，并同步对齐 `pyproject.toml`、`main.py`、`app.entrypoints`、`scripts/vwr.ps1`、单测烟囱校验与 README / 脚本文档。
- 包名语义化：将 `app` 改为 `video_watermark_remover`（变更面较大，需谨慎）。
- [x] `src/app/core/video/` 进一步按职责拆分：新增 `modes/`、`workers/`、`utils/`、`thread.py`，旧平铺模块保留为兼容层，降低目录平铺与导入破坏面。

**验证基线：**
- GUI 冒烟：`python main.py` 能正常启动主窗口（Windows/Qt 环境）。
- 单测：`python -m pytest -q` 通过。

### Task 6：调试稳定后移除 `video` 兼容层（后置清理）（已完成，2026-03-20）

**目标：**
- 在 `modes/`、`workers/`、`utils/`、`thread.py` 已稳定运行、调用方与测试全部切到新入口后，删除旧平铺兼容层，让 `src/app/core/video/` 保持单一职责与清晰目录边界。

**Files：**
- Deleted: `src/app/core/video/audio_tasks.py`
- Deleted: `src/app/core/video/backpressure.py`
- Deleted: `src/app/core/video/chunk_worker.py`
- Deleted: `src/app/core/video/frame_processor.py`
- Deleted: `src/app/core/video/frame_reader.py`
- Deleted: `src/app/core/video/frame_writer.py`
- Deleted: `src/app/core/video/multiprocess_processor.py`
- Deleted: `src/app/core/video/path_utils.py`
- Deleted: `src/app/core/video/pipeline_processor.py`
- Deleted: `src/app/core/video/single_process_processor.py`
- Deleted: `src/app/core/video/video_processor.py`
- Modified: `src/app/core/video/thread.py`
- Modified: `src/app/ui/signal_handler.py`
- Modified: `src/app/ui/widgets/batch/batch_processor_thread.py`
- Modified: `tests/core/ai/video/*`、`tests/integration/*video*`、`tests/ai_*`、`tests/e2e/*`

**执行前检查清单（全部满足后再启动 Task 6）**
- [x] **调用方迁移完成**：UI 生产调用方与 `tests/core/ai/video/test_video_modes.py` 已切换到 `thread` / `workers.*` / `modes.*` 新入口，不再依赖旧平铺兼容层模块名。
- [x] **导入扫描通过**：对 `src` / `tests` 的复扫显示，正式测试调用点已不再直接引用 `app.core.video.video_processor` 或旧平铺兼容层入口；当前命中主要位于兼容层自身实现与文档说明。
- [x] **UI 入口稳定**：`src/app/ui/signal_handler.py`、`src/app/ui/widgets/batch/batch_processor_thread.py` 已全部改用 `app.core.video.thread` / `app.core.video.modes.*` / `app.core.video.workers.*` / `app.core.video.utils.*`。
- [x] **测试入口稳定**：`tests/core/ai/video/test_video_modes.py`、`tests/integration/test_video_processor.py`、`tests/integration/test_pipeline_video.py`、`tests/integration/test_multiprocess_video.py`、`tests/e2e/test_phase5_gpu_e2e.py`、`tests/ai_processing_tests.py`、`tests/ai_module_tests.py`、`tests/e2e/ps1/test_end_to_end.ps1` 已迁移到新入口或改为新模块引用。
- [x] **兼容层仅剩过渡职责**：旧平铺兼容层 `audio_tasks.py`、`backpressure.py`、`chunk_worker.py`、`frame_processor.py`、`frame_reader.py`、`frame_writer.py`、`multiprocess_processor.py`、`path_utils.py`、`pipeline_processor.py`、`single_process_processor.py`、`video_processor.py` 已删除，正式入口已统一收敛到 `thread` / `modes.*` / `workers.*` / `utils.*`。
- [x] **调试记录闭环**：已通过 `scripts/task6_runtime_smoke.py --keep` 完成一轮运行态 smoke，覆盖 GUI 启动、单文件图片、单文件视频（单进程 / 分块模式 / 流水线模式）与批量处理，并记录运行目录与输出文件。
- [x] **质量链路为绿**：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1" quality -Quick` 已在当前工作区裸跑通过；根目录残留 `app/` namespace 目录已清理。
- [x] **单测链路为绿**：2026-03-20 复跑 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1" test unit -Quick` 已通过，结果为 `95 passed, 2 deselected`。
- [x] **视频定向测试为绿**：兼容层删除后的结构层验证 `$env:PYTHONPATH='src'; python -m pytest tests/core/ai/video/test_video_module_split.py -q` 为 `3 passed`；此前带完整视频依赖的 `tests/integration/test_multiprocess_video.py`、`tests/integration/test_pipeline_video.py`、`tests/integration/test_video_processor.py` 已在依赖齐全会话通过，当前轻量沙箱仅补做结构层复核。
- [x] **回滚点已准备**：已将 `docs/agents/` 纳入本次提交范围，Task 3/6 相关代码、测试、脚本与文档已整理为单一回滚点，可在本次提交后直接回退。
- [x] **已获删除确认**：本轮已明确确认执行方案 A，并已据此完成 Task 3 的目录删除；Task 6 最终兼容层删除时仍需按本轮确认记录复核影响面。

**Task 6 运行态调试记录（2026-03-20）**
- 执行命令：`$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe scripts/task6_runtime_smoke.py --keep`
- 调试方式：使用真实 `MainWindow` / `VideoProcessorThread` / `BatchProcessorThread` 入口，配合 `DummyAIHandler`、`DummyFFmpegAudioProcessor`、`DummyManager`、`InlineExecutor` 做轻量运行态 smoke；该记录用于验证入口、线程编排、模式切换与输出落盘，不替代真实模型集成测试。
- GUI 启动：`MainWindow` 已完成一轮 `show() → processEvents() → close()`。
- 单文件处理：图片、单进程视频、分块模式视频、流水线模式视频均生成输出文件。
- 批量处理：2 个样本文件（1 图 + 1 视频）均完成，状态为 `completed`。
- 运行目录：`C:/cascadeProjects/video_watermark_remover/.cache/task6-smoke/run_20260320_093108_87dba7f9191246ff8b4e3c547d38c01d`。
- 相关补充验证：`$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests/core/ai/video/test_video_modes.py -q` 为 `4 passed`。

**Task 6 前置迁移小清单（测试引用）**
- [x] `tests/unit/test_path_utils.py`：已迁移为 `from app.core.video.utils.path import build_temp_path`，定向验证 `python -m pytest tests/unit/test_path_utils.py -q` 已通过。
- [x] `tests/core/ai/video/test_video_module_split.py`：已移除旧兼容层导入段，测试收敛为“新入口结构完整、导出一致、行为一致”，并通过 PyQt6/AI/FFmpeg stub 避免收集阶段加载重依赖。
- [x] `tests/core/ai/video/test_video_module_split.py`：将 `from app.core.video.multiprocess_processor import process_video_multiprocess` 迁移为 `from app.core.video.modes.multiprocess import process_video_multiprocess`。
- [x] `tests/core/ai/video/test_video_module_split.py`：将 `from app.core.video.pipeline_processor import process_video_pipeline` 迁移为 `from app.core.video.modes.pipeline import process_video_pipeline`。
- [x] `tests/core/ai/video/test_video_module_split.py`：将 `from app.core.video.single_process_processor import process_video_singleprocess` 迁移为 `from app.core.video.modes.single_process import process_video_singleprocess`。
- [x] `tests/core/ai/video/test_video_module_split.py`：将 `from app.core.video.path_utils import build_temp_path` 迁移为 `from app.core.video.utils.path import build_temp_path`。
- [x] `tests/core/ai/video/test_video_module_split.py`：完成迁移后，将该测试的目标从“旧新双入口兼容”收敛为“仅验证新入口结构完整、导出一致、行为一致”。
- [x] 迁移顺序建议：先改 `tests/unit/test_path_utils.py`，再在真正执行 Task 6 前最后一轮统一改 `tests/core/ai/video/test_video_module_split.py`。
- [x] 每迁移完一项即验证：`python -m pytest tests/unit/test_path_utils.py -q` 或 `python -m pytest tests/core/ai/video/test_video_module_split.py -q`。
- [x] `tests/core/ai/video/test_video_modes.py`：已改为 `app.core.video.thread` + `app.core.video.modes.*` + `app.core.video.workers.*` 新入口，定向验证 `python -m pytest tests/core/ai/video/test_video_modes.py -q` 已通过。
- [x] `tests/integration/test_multiprocess_video.py`、`tests/integration/test_pipeline_video.py`、`tests/integration/test_video_processor.py`：已迁移为 `workers.*` / `thread` 新入口，并将运行目录收敛到项目本地 `.cache/`，定向验证 `10 passed`。
- [x] `tests/ai_module_tests.py`、`tests/ai_processing_tests.py`、`tests/e2e/test_phase5_gpu_e2e.py`、`tests/e2e/ps1/test_end_to_end.ps1`：已改用 `app.core.video.thread` 或相关新入口；其中两条轻量验证 `-k video_processor_thread_import` / `-k test_video_processor_thread` 已通过。
- [x] `tests/core/ai/video/test_video_module_split.py`：已新增“旧平铺兼容层文件应不存在”断言，验证兼容层删除不会回退。

**Step 1：冻结迁移前置条件**
- 要求：仅在 GUI 手工调试、定向视频链路测试、`scripts/vwr.ps1 quality -Quick`、`scripts/vwr.ps1 test unit -Quick`、相关集成测试均稳定后执行。

**Step 2：扫描兼容层剩余引用**
- Run：
  - `rg -n "audio_tasks|backpressure|chunk_worker|frame_processor|frame_reader|frame_writer|multiprocess_processor|path_utils|pipeline_processor|single_process_processor" "src" "tests"`
- 目标：确认仍有哪些调用点依赖旧平铺模块。

**Step 3：将调用方切换到新子包入口**
- 示例：统一改为 `app.core.video.modes.*`、`app.core.video.workers.*`、`app.core.video.utils.*`、`app.core.video.thread`。

**Step 4：删除兼容层并收口导出**
- 删除旧平铺兼容文件；同步收敛 `src/app/core/video/__init__.py` 与 `src/app/core/video/video_processor.py` 的过渡导出，避免继续扩散双入口。

**Step 5：执行回归验证**
- Run：
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1" quality -Quick`
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1" test unit -Quick`
  - `python -m pytest tests/core/ai/video -q`
- 目标：确认删除兼容层后功能、导入链路、测试入口全部保持稳定。


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

## 6.1 已实施变更（2026-03-19）

- `app/` → `src/app/`：完成 `src/` 布局迁移，降低“从工作目录误导入本地包”的风险。
- `main.py`：改为薄启动器，实际入口转发到 `app.entrypoints:main`。
- `pyproject.toml`：补充 `package-dir={"": "src"}`，将 `project.scripts` / `project.gui-scripts` 对齐到 `app.entrypoints:main`。
- `MANIFEST.in`：补充 `main.py`，确保分发包仍包含根入口薄启动器。
- `scripts/vwr.ps1`：`setup` 自动执行 editable install，并在 `run/test/quality/build` 前做项目可导入校验；2026-03-20 已进一步补齐项目级缓存/TEMP/pytest basetemp 兜底，并在清理根目录残留 `app/` 后恢复裸跑 `quality -Quick`。
- `src/app/core/ai/__init__.py`：改为惰性导入，避免 Windows 下 pytest 收集阶段触发 `torch` 的 `WinError 1114`。
- `README.md`、`scripts/README.md`：同步 `src/app` 布局、editable install、薄启动器与脚本真实行为说明（对应本轮 Task 1.6）。
- `pyproject.toml`、`requirements-dev.txt`、`scripts/vwr.ps1`：补齐 Black 参数与版本对齐（`23.12.1`），消除脚本质量检查与 pre-commit 钩子不一致的问题。
- `src/app/core/video/`：完成第二轮结构化拆分，正式入口已收敛到 `thread.py`、`modes/`、`workers/`、`utils/`；2026-03-20 已删除全部旧平铺兼容层文件。
- `src/app/core/video/workers/chunk.py`、`src/app/core/video/workers/frame_processor.py`、`src/app/core/video/thread.py`：通过 AI / FFmpeg / 视频模式惰性解析，避免测试收集或轻量导入阶段过早拉起重依赖。
- `tests/core/ai/video/test_video_module_split.py`：新增并持续增强视频模块拆分结构测试，验证新子包入口可用、导出一致、旧兼容层文件已删除，并通过 PyQt6 / AI / FFmpeg / cv2 / numpy stub 避免轻量环境误报。
- `scripts/task6_runtime_smoke.py`：新增 Task 6 运行态 smoke 脚本，固化 GUI 启动、单文件图片、单文件视频三模式与批量处理的轻量回归入口。
- `docs/agents/*`：纳入项目专属子代理协作基线，统一多子代理调度角色、写入边界与输出协议，避免后续会话与审计文档脱节。
- 阶段性验证（2026-03-19 记录）：`tests/core/ai/video/test_video_modes.py`、`tests/unit/test_path_utils.py`、`scripts/vwr.ps1 quality -Quick`、`scripts/vwr.ps1 test unit -Quick` 曾在当时会话中通过。
- 复核补充（2026-03-20）：已完成 `video_processor.py` 纯兼容入口收口、`tests/core/ai/video/test_video_modes.py` 与 `tests/integration/*video*` 的入口迁移、`tests/ai_module_tests.py` / `tests/ai_processing_tests.py` / `tests/e2e/*` 的视频入口更新，以及根目录残留 `app/`、`src/app/ui/dialogs/` 清理。
- 最终收口（2026-03-20）：已删除 `src/app/core/video/` 下全部旧平铺兼容层文件，并新增“旧兼容层文件应不存在”的结构测试；`tests/unit/test_module_syntax_smoke.py` 与 `tests/phase3_core_tests.py` 已同步切换到新结构路径。
- 回归补丁（2026-03-20）：`src/app/core/video/thread.py` 已恢复惰性导入边界，避免导入 `VideoProcessorThread` 时提前拉起 `cv2` 相关模块；`tests/core/ai/video/test_video_module_split.py` 已补充 `cv2` / `numpy` stub，使结构测试可在轻量依赖环境下稳定执行。
- 验证更新（2026-03-20）：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1" quality -Quick` 已通过；当前轻量沙箱下 `$env:PYTHONPATH='src'; python -m pytest tests/core/ai/video/test_video_module_split.py -q` 为 `3 passed`、`$env:PYTHONPATH='src'; python -m pytest tests/unit/test_module_syntax_smoke.py -q` 为 `9 passed`、`$env:PYTHONPATH='src'; python -m pytest tests/phase3_core_tests.py -q -k file_structure` 为 `1 passed`；此前带完整视频依赖的 `tests/integration/test_multiprocess_video.py`、`tests/integration/test_pipeline_video.py`、`tests/integration/test_video_processor.py` 已在依赖齐全会话通过。
- 运行态补充（2026-03-20）：已新增 `scripts/task6_runtime_smoke.py`，并通过 `--keep` 实跑覆盖 GUI 启动、单文件图片、单文件视频（单进程 / 分块模式 / 流水线模式）与批量处理；最新运行目录为 `C:/cascadeProjects/video_watermark_remover/.cache/task6-smoke/run_20260320_092931_04c60cc639a143e4b54f61c7e376c82c`。

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
