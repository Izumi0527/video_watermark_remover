# 测试目录主分层统一与历史测试归位计划 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `tests/` 统一收敛到 `unit/integration/e2e` 主分层，并把历史遗留的根目录测试入口、`tests/app/**`、`tests/core/**` 下沉到按模块划分的二级目录，完成审计文档中“测试目录分层混杂”这一唯一剩余未完成项。

**Architecture:** 采用“先按测试性质分类、再小批量迁移、最后清理空目录与同步文档”的低风险路径。纯 pytest 且局部逻辑明确的测试归入 `unit/**`；依赖 `cv2`、`PyQt6`、文件系统、视频流程编排或历史场景编排的测试归入 `integration/**`；PowerShell 端到端脚本继续保留在 `e2e/**`。不改业务实现，只调整测试路径、导入关系、历史 runner/support 安置方式与文档说明。

**Tech Stack:** Python 3.8+、pytest、pytest-qt、PyQt6、OpenCV/Numpy、PowerShell（`scripts/vwr.ps1`）。

---

## 完成定义

- `tests/app/**`、`tests/core/**` 两套历史顶层分层被清空并移除。
- 根目录历史测试文件 `tests/ai_*`、`tests/phase3_*`、`tests/ui_component_tests.py` 全部迁入二级目录。
- 活跃测试入口仅保留在 `tests/unit/**`、`tests/integration/**`、`tests/e2e/**` 三个主分层下。
- `tests/integration/test_utilities.py`、`tests/test_data/**`、`tests/conftest.py` 保持稳定锚点，不随迁移改名。
- `tests/TESTING_GUIDE.md`、`scripts/vwr.ps1`、`docs/plans/2026-03-18-project-structure-audit.md` 中涉及旧路径的说明同步完成。

## 分类准则

- `tests/unit/**`：无外部进程依赖、无真实视频/GUI流程依赖、以局部模块行为和导入边界为主的测试。
- `tests/integration/**`：依赖 `cv2` / `PyQt6` / 文件写入 / 视频流程 / 跨模块协作的测试。
- `tests/e2e/**`：PowerShell 脚本、命令行或人工验收导向场景。
- `tests/future/**`：仅保留“未来阶段/暂挂”测试；不再接收本次要迁移的活跃历史入口。

## 目标结构（迁移完成后）

```text
tests/
  conftest.py
  test_data/
  unit/
    app/
      config/
        preferences/
          test_preferences_package.py
        styles/
          test_styles_package.py
    core/
      ai/
        video/
          test_video_module_split.py
  integration/
    test_utilities.py
    ai/
      test_ai_module.py
      test_ai_processing.py
    core/
      ai/
        video/
          test_video_modes.py
    ui/
      test_ui_components.py
    legacy_phase3/
      __init__.py
      core_checks.py
      feature_checks.py
      runner.py
      support.py
      test_phase3.py
  e2e/
    ps1/
      ...
  future/
    unit/
      test_config_manager_phase3.py
      test_image_inpainter_phase3.py
```

## 文件迁移映射

- `tests/app/config/preferences/test_preferences_package.py` → `tests/unit/app/config/preferences/test_preferences_package.py`
- `tests/app/config/styles/test_styles_package.py` → `tests/unit/app/config/styles/test_styles_package.py`
- `tests/core/ai/video/test_video_module_split.py` → `tests/unit/core/ai/video/test_video_module_split.py`
- `tests/core/ai/video/test_video_modes.py` → `tests/integration/core/ai/video/test_video_modes.py`
- `tests/ai_module_tests.py` → `tests/integration/ai/test_ai_module.py`
- `tests/ai_processing_tests.py` → `tests/integration/ai/test_ai_processing.py`
- `tests/ui_component_tests.py` → `tests/integration/ui/test_ui_components.py`
- `tests/phase3_core_tests.py` → `tests/integration/legacy_phase3/core_checks.py`
- `tests/phase3_feature_tests.py` → `tests/integration/legacy_phase3/feature_checks.py`
- `tests/phase3_test_runner.py` → `tests/integration/legacy_phase3/runner.py`
- `tests/phase3_test_utilities.py` → `tests/integration/legacy_phase3/support.py`
- `tests/integration/test_phase3.py` → `tests/integration/legacy_phase3/test_phase3.py`

---

### Task 1: 迁移配置类单测到 `unit/app/config`

**Files:**
- Create: `tests/unit/app/config/preferences/test_preferences_package.py`
- Create: `tests/unit/app/config/styles/test_styles_package.py`
- Delete: `tests/app/config/preferences/test_preferences_package.py`
- Delete: `tests/app/config/styles/test_styles_package.py`
- Remove when empty: `tests/app/config/preferences/`
- Remove when empty: `tests/app/config/styles/`
- Remove when empty: `tests/app/config/`
- Remove when empty: `tests/app/`

**Step 1: 迁移文件并保持内容不变**

- 直接移动两个 pytest 风格文件，不调整测试语义。
- 保持文件名不变，只改变所在目录。

**Step 2: 复核依赖是否仍可解析**

- 确认 `from app.config import preferences` 与 `from app.config import styles` 不依赖旧测试路径。
- 若新增目录需要占位文件，优先只补最小必要的 `__init__.py`；默认不新增。

**Step 3: 运行聚焦验证**

Run:
```powershell
pytest tests/unit/app/config/preferences/test_preferences_package.py tests/unit/app/config/styles/test_styles_package.py -q
```

Expected:
- `test_preferences_package.py` 通过。
- `test_styles_package.py` 在缺少 `PyQt6` 时允许 `SKIPPED`，有环境时应 `PASSED`。

**Step 4: 清理空目录**

- 删除已经空置的 `tests/app/**` 目录。
- 确认 `rg -n "tests/app/config" tests docs scripts` 无有效旧路径引用。

**Step 5: 提交**

```bash
git add tests/unit/app tests/app docs/plans
git commit -m "test(test-structure): 迁移配置类测试到 unit 分层"
```

---

### Task 2: 拆分 `video` 测试到 `unit` 与 `integration`

**Files:**
- Create: `tests/unit/core/ai/video/test_video_module_split.py`
- Create: `tests/integration/core/ai/video/test_video_modes.py`
- Delete: `tests/core/ai/video/test_video_module_split.py`
- Delete: `tests/core/ai/video/test_video_modes.py`
- Remove when empty: `tests/core/ai/video/`
- Remove when empty: `tests/core/ai/`
- Remove when empty: `tests/core/`

**Step 1: 先迁移导入边界测试**

- 移动 `test_video_module_split.py` 到 `tests/unit/core/ai/video/`。
- 保持兼容层删除断言、模块导出断言与 stub 逻辑不变。

**Step 2: 再迁移流程级 smoke 测试**

- 移动 `test_video_modes.py` 到 `tests/integration/core/ai/video/`。
- 保持 `cv2`/`numpy`/临时运行目录策略不变。

**Step 3: 运行分层验证**

Run:
```powershell
pytest tests/unit/core/ai/video/test_video_module_split.py -q
pytest tests/integration/core/ai/video/test_video_modes.py -q
```

Expected:
- `test_video_module_split.py` 必须 `PASSED`。
- `test_video_modes.py` 在缺少 `cv2` 时允许整体 `SKIPPED`，有环境时应通过。

**Step 4: 清理旧分层目录**

- 删除空置的 `tests/core/**`。
- 确认 `rg -n "tests/core/ai/video" tests docs scripts` 仅剩新路径或计划文档说明。

**Step 5: 提交**

```bash
git add tests/unit/core tests/integration/core tests/core
git commit -m "test(test-structure): 拆分 video 测试到 unit 与 integration"
```

---

### Task 3: 归位顶层 AI / UI 历史测试到 `integration`

**Files:**
- Create: `tests/integration/ai/test_ai_module.py`
- Create: `tests/integration/ai/test_ai_processing.py`
- Create: `tests/integration/ui/test_ui_components.py`
- Delete: `tests/ai_module_tests.py`
- Delete: `tests/ai_processing_tests.py`
- Delete: `tests/ui_component_tests.py`

**Step 1: 迁移 AI 历史测试文件**

- `tests/ai_module_tests.py` 改放到 `tests/integration/ai/test_ai_module.py`。
- `tests/ai_processing_tests.py` 改放到 `tests/integration/ai/test_ai_processing.py`。
- 保留其依赖 `tests.integration.test_utilities` 的方式，不再使用根目录散落入口。

**Step 2: 迁移 UI 历史测试文件并修正工具导入**

- `tests/ui_component_tests.py` 改放到 `tests/integration/ui/test_ui_components.py`。
- 将 `from test_utilities import ...` 统一改为 `from tests.integration.test_utilities import ...`。

**Step 3: 标准化最小 pytest 断言**

- 对仍以 `return (bool, message)` 为主的历史测试，优先改成 `assert success, detail` 风格。
- 不扩展测试范围，只把“脚本式返回值”收口为标准 pytest 断言，避免迁移后继续产生 `PytestReturnNotNoneWarning`。

**Step 4: 运行聚焦验证**

Run:
```powershell
pytest tests/integration/ai/test_ai_module.py tests/integration/ai/test_ai_processing.py tests/integration/ui/test_ui_components.py -q
```

Expected:
- 缺少重依赖时允许 `SKIPPED`，但不应出现旧路径 `ImportError`。
- 不再出现根目录 `test_utilities` 导入失败。

**Step 5: 提交**

```bash
git add tests/integration/ai tests/integration/ui tests/ai_module_tests.py tests/ai_processing_tests.py tests/ui_component_tests.py
git commit -m "test(test-structure): 归位 AI 与 UI 历史集成测试"
```

---

### Task 4: 迁移 `phase3` 历史 runner / support 到 `integration/legacy_phase3`

**Files:**
- Create: `tests/integration/legacy_phase3/__init__.py`
- Create: `tests/integration/legacy_phase3/core_checks.py`
- Create: `tests/integration/legacy_phase3/feature_checks.py`
- Create: `tests/integration/legacy_phase3/runner.py`
- Create: `tests/integration/legacy_phase3/support.py`
- Create: `tests/integration/legacy_phase3/test_phase3.py`
- Delete: `tests/phase3_core_tests.py`
- Delete: `tests/phase3_feature_tests.py`
- Delete: `tests/phase3_test_runner.py`
- Delete: `tests/phase3_test_utilities.py`
- Delete: `tests/integration/test_phase3.py`

**Step 1: 迁移并重命名非 pytest 入口**

- 将 `phase3_core_tests.py` 重命名为 `core_checks.py`。
- 将 `phase3_feature_tests.py` 重命名为 `feature_checks.py`。
- 将 `phase3_test_runner.py` 重命名为 `runner.py`。
- 将 `phase3_test_utilities.py` 重命名为 `support.py`。

**Step 2: 保留单一可收集测试入口**

- 把 `tests/integration/test_phase3.py` 改为 `tests/integration/legacy_phase3/test_phase3.py`。
- 该文件只负责桥接 `runner.py`，避免 pytest 误收集多个脚本式模块。

**Step 3: 修正导入路径**

- `runner.py` 改为从 `tests.integration.legacy_phase3.core_checks`、`feature_checks`、`support` 导入。
- 删除所有 `from phase3_* import ...` 这类依赖根目录文件名的导入方式。

**Step 4: 运行聚焦验证**

Run:
```powershell
pytest tests/integration/legacy_phase3/test_phase3.py -q
```

Expected:
- 不再依赖根目录 `tests/phase3_*` 文件。
- 迁移后若部分环境依赖缺失，可失败在实际运行逻辑，但不应失败在旧路径导入。

**Step 5: 提交**

```bash
git add tests/integration/legacy_phase3 tests/phase3_core_tests.py tests/phase3_feature_tests.py tests/phase3_test_runner.py tests/phase3_test_utilities.py tests/integration/test_phase3.py
git commit -m "test(test-structure): 收口 phase3 历史测试入口"
```

---

### Task 5: 清理空目录并同步脚本/文档

**Files:**
- Modify: `tests/TESTING_GUIDE.md`
- Modify: `scripts/vwr.ps1`
- Modify: `docs/plans/2026-03-18-project-structure-audit.md`
- Review: `pyproject.toml`
- Remove when empty: `tests/app/`
- Remove when empty: `tests/core/`

**Step 1: 同步测试文档**

- 将 `tests/TESTING_GUIDE.md` 中示例路径更新为新分层路径。
- 增加“主分层为 `unit/integration/e2e`，模块放在二级目录”的说明。

**Step 2: 同步脚本入口**

- 检查 `scripts/vwr.ps1` 是否存在对旧测试路径的硬编码。
- 如有，改成新路径；如无，仅补充注释或帮助文本，不做无效改动。

**Step 3: 回写审计文档状态**

- 将 `docs/plans/2026-03-18-project-structure-audit.md` 第 118 行对应项标记为已完成。
- 在同节补一句收口说明，明确根目录历史测试入口、`tests/app/**`、`tests/core/**` 已完成归位。

**Step 4: 运行引用扫描**

Run:
```powershell
rg -n "tests/app/|tests/core/|ai_module_tests|ai_processing_tests|ui_component_tests|phase3_core_tests|phase3_feature_tests|phase3_test_runner|phase3_test_utilities" tests docs scripts
```

Expected:
- 仅允许计划文档或历史变更记录中保留旧名字。
- 执行路径、说明文档、活动测试入口均改为新位置。

**Step 5: 提交**

```bash
git add tests/TESTING_GUIDE.md scripts/vwr.ps1 docs/plans/2026-03-18-project-structure-audit.md
git commit -m "docs(test-structure): 同步测试目录标准化文档与脚本"
```

---

### Task 6: 分层回归与最终收口

**Files:**
- Review only: `tests/unit/**`
- Review only: `tests/integration/**`
- Review only: `tests/e2e/**`
- Review only: `docs/plans/2026-03-18-project-structure-audit.md`

**Step 1: 运行单元层快速回归**

Run:
```powershell
pytest tests/unit -q
```

Expected:
- 单元测试在常规开发机上可在可接受时间内完成。

**Step 2: 运行本次受影响的集成层回归**

Run:
```powershell
pytest tests/integration/ai tests/integration/core/ai/video tests/integration/ui tests/integration/legacy_phase3 -q
```

Expected:
- 不出现旧路径导入失败。
- 缺少重依赖的测试允许 `SKIPPED`，但不应因目录迁移导致新增失败。

**Step 3: 运行统一脚本门禁**

Run:
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\\scripts\\vwr.ps1" test unit -Quick
```

Expected:
- 快速单测门禁通过；若脚本仅覆盖 `tests/unit`，应与新分层保持一致。

**Step 4: 最终核验目录**

Run:
```powershell
Get-ChildItem tests -Depth 3
```

Expected:
- 活跃测试主分层只体现为 `unit`、`integration`、`e2e`。
- 不再存在带活跃测试文件的 `tests/app`、`tests/core` 或根目录历史测试入口。

**Step 5: 提交**

```bash
git add tests docs scripts
git commit -m "test(test-structure): 完成测试目录主分层统一"
```

---

## 风险与回滚

- 风险 1：历史脚本式测试依赖 `sys.path.insert(...)` 与根目录文件名，迁移后最容易先在导入阶段失败。
  - 回滚：优先恢复对应测试文件路径，不回滚业务代码。
- 风险 2：`phase3` runner/support 改名后，`tests/integration/legacy_phase3/test_phase3.py` 可能出现桥接路径错误。
  - 回滚：单独回退 `legacy_phase3` 目录与桥接入口提交。
- 风险 3：`PyQt6` / `cv2` 环境不完整时，迁移后的测试可能表现为 `SKIPPED` 或环境性失败。
  - 处理：只把“旧路径导入失败”视为迁移缺陷，把“缺依赖导致 skip”视为环境现象。

## 非目标

- 不修改 `src/app/**` 业务实现。
- 不重写 `tests/test_data/**`、`tests/conftest.py`、`tests/e2e/ps1/**`。
- 不在本次任务中扩大测试覆盖范围；只做路径归位、导入修正、最小 pytest 标准化。
