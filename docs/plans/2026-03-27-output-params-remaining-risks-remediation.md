# 输出参数剩余风险收口实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复输出参数链路当前剩余的 4 项风险，完成 legacy 字段收口、批处理稳定标识重构、UI 集成探针升级与更大范围回归验证。

**Architecture:** 继续以 `AdvancedParamsSnapshot` / `ResolvedOutputConfig` 作为唯一输出参数真源；批处理链路从“按索引回写”升级为“按稳定 file_id 回写”；GUI 集成测试从单点 `skip` 升级为分层探针；验证阶段采用“定向回归 + 扩展回归矩阵”双层策略。

**Tech Stack:** Python、PyQt6、pytest、PowerShell、FFmpeg

---

## 修复优先级

### P0：批处理稳定标识重构

**目标**

- 不再把 `index` 当作批处理队列项的唯一身份。
- 为运行中动态移除、重排、清单导出和状态回写建立稳定标识基础。

**原因**

- 这是后续支持“处理中动态编辑队列”的前置条件。
- 如果继续依赖索引，任何队列变动都会放大为状态错乱、输出路径错位、manifest 追溯失真。

**主战场**

- `src/app/ui/widgets/batch/batch_processor_thread.py`
- `src/app/ui/signal_handler.py`
- `src/app/ui/widgets/batch/batch_processing_widget.py`
- `tests/unit/test_batch_processor_file_level_runtime_config.py`
- `tests/unit/test_signal_handler_batch_manifest.py`
- `tests/unit/test_signal_handler_batch_config_passthrough.py`

### P1：legacy 输出字段彻底收口

**目标**

- 从新导出、新持久化、新运行时快照中彻底移除：
  - `processing.output_quality`
  - `processing.preserve_audio`
  - `add_processed_suffix`
- 仅在必要的输入迁移层保留隔离兼容。

**原因**

- 当前链路已经基本收敛到 `compression_quality` / `preserve_audio` / `add_suffix`。
- 继续在消费侧保留 legacy 读取，会让测试、文档和真实行为分裂。

**主战场**

- `src/app/config/advanced_params.py`
- `src/app/config/preferences/defaults.py`
- `src/app/config/preferences/manager.py`
- `src/app/config/preferences/validator.py`
- `src/app/ui/utils/ai_params_builder.py`
- `src/app/ui/signal_handler.py`
- `tests/unit/**`
- `tests/test_data/configs/user_prefs_sample.json`
- `docs/complete-technical-documentation.md`

### P2：UI 集成探针升级

**目标**

- 将 `tests/integration/ui/test_ui_components.py` 从“模块级粗跳过”升级为更细粒度的运行时探针。
- 明确区分：
  - `PyQt6` 模块缺失
  - `QtWidgets` 不可导入
  - `QApplication` 无法创建
  - 具体组件实例化失败

**原因**

- 当前 skip 粒度过大，容易把真实 UI 回归隐藏在环境噪音后面。
- 需要把环境失败和代码失败切开，才能让 UI 回归结果更可信。

**主战场**

- `tests/integration/ui/test_ui_components.py`
- 视情况最小触达 `tests/integration/test_utilities.py`
- 如确有必要，再最小适配 `src/app/entrypoints.py`

### P3：扩展回归验证

**目标**

- 在定向输出参数测试之外，补跑更大范围但仍可控的回归矩阵。
- 覆盖配置持久化、批处理、GUI 集成与核心视频输出链路。

**原因**

- 这轮改动横跨 `config`、`ui`、`batch`、`core`。
- 仅依赖输出参数专项测试，还不足以证明无跨域回归。

**主战场**

- `tests/unit/app/config/preferences/**`
- `tests/unit/test_signal_handler_*`
- `tests/unit/test_batch_*`
- `tests/integration/ui/test_ui_components.py`
- 必要时补跑 `tests/integration/test_batch_processing.py`

## 实施顺序

### 阶段一：先打通 file_id 基础设施

**目标**

- 给队列项补稳定 `file_id`。
- 信号回调、状态更新、manifest 导出优先支持 `file_id`。
- 为“处理中动态编辑队列”建立数据模型基础，即便本轮还不立即开放全部 UI 能力。

**验收标准**

- 新增队列项时会生成稳定 `file_id`。
- 运行时快照、输出配置快照、状态回写都可以定位到正确文件，而不是隐式依赖当前位置。
- 相关单元测试覆盖新增身份字段、回写与导出链路。

### 阶段二：再清理 legacy 字段

**目标**

- 所有新生成的 AI 参数、偏好快照、manifest、测试样例统一使用新字段。
- legacy 字段只允许出现在隔离迁移函数里，不再散落在 UI/运行时消费逻辑中。

**验收标准**

- `rg` 检索结果中，业务代码不再散落读取 `add_processed_suffix`、`processing.output_quality`、`processing.preserve_audio`。
- 测试和示例配置统一使用 `add_suffix` / `compression_quality` / `preserve_audio`。
- `AdvancedParamsSnapshot.from_dict()` 仍可从旧输入迁移，但 `to_ai_params()` / `to_ui_dict()` / manifest 导出不再输出旧字段。

### 阶段三：升级 UI 集成探针

**目标**

- 在不误报环境问题的前提下，提高 UI 集成测试的有效信息量。

**验收标准**

- 环境级失败能给出明确 skip 原因。
- 代码级失败不再被模块级 skip 吞掉。
- 至少覆盖“模块导入”“QApplication 创建”“输出参数页签实例化”三层检查。

### 阶段四：执行扩展回归

**目标**

- 重新跑定向测试。
- 在 60 秒预算内补跑一组跨域扩展回归。

**验收标准**

- 输出参数、偏好持久化、批处理、UI 集成关键路径全部有新鲜验证证据。
- 若有环境限制导致 skip，需明确记录，不把 skip 当 pass。

## 并行修复包

### 修复包 A：批处理稳定标识

**负责人**

- `batch-orchestrator`

**范围**

- `src/app/ui/signal_handler.py`
- `src/app/ui/widgets/batch/**`
- 与批处理直接相关的 `tests/unit/test_batch_*`
- `tests/unit/test_signal_handler_*`

**任务**

1. 写失败测试，锁定 `file_id` 身份需求和回写路径。
2. 给队列项增加稳定标识，并让关键状态更新链路优先支持 `file_id`。
3. 调整 manifest 和文件级快照导出逻辑，避免继续把索引当作唯一身份。

### 修复包 B：legacy 字段收口

**负责人**

- `core-engine-implementer`
- 主线程负责 `config/preferences` 的最终集成

**范围**

- `src/app/ui/utils/ai_params_builder.py`
- `src/app/config/**`
- 与输出参数消费直接相关的 `tests/unit/**`
- `tests/test_data/configs/user_prefs_sample.json`
- 文档中输出参数相关章节

**任务**

1. 收口消费侧对 `add_processed_suffix` 的读取。
2. 把测试夹具、示例配置和日志断言统一到新字段。
3. 把 legacy 兼容限定到迁移入口，避免新导出继续扩散旧字段。

### 修复包 C：UI 集成探针

**负责人**

- `ui-implementer`

**范围**

- `tests/integration/ui/test_ui_components.py`
- 必要时最小触达 `tests/integration/**`

**任务**

1. 拆分 UI 环境探针层次。
2. 对关键 UI 用例采用更清晰的失败/跳过判定。
3. 保持对当前 DLL 权限异常环境的兼容，但不给代码回归“兜底洗白”。

### 修复包 D：全量回归监控

**负责人**

- `long-task-monitor`
- `quality-reviewer`

**范围**

- 只读验证，不先改业务代码

**任务**

1. 监控扩展回归命令的执行状态与超时风险。
2. 审查最终集成后的残余风险与测试缺口。

## 最小回归集合

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest `
  tests/unit/core/video/test_output_strategy.py `
  tests/unit/test_signal_handler_output_config.py `
  tests/unit/test_signal_handler_batch_manifest.py `
  tests/unit/test_signal_handler_batch_config_passthrough.py `
  tests/unit/test_batch_processor_file_level_runtime_config.py `
  tests/unit/app/config/preferences/test_advanced_params_preferences.py `
  tests/unit/test_advanced_params_schema.py `
  tests/integration/ui/test_ui_components.py `
  -q -o addopts=''
```

## 扩展回归建议

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest `
  tests/unit/app/config/preferences `
  tests/unit/test_signal_handler_batch_manifest.py `
  tests/unit/test_signal_handler_output_config.py `
  tests/unit/test_batch_processing_widget_runtime_config.py `
  tests/unit/test_batch_processor_file_level_runtime_config.py `
  tests/integration/ui/test_ui_components.py `
  tests/integration/test_batch_processing.py `
  -q -o addopts=''
```

## 冲突边界

1. `src/app/ui/signal_handler.py` 只能由一个实现代理主写，避免与批处理线程状态机互相覆盖。
2. `src/app/ui/widgets/batch/batch_processor_thread.py` 与 `src/app/ui/widgets/batch/batch_processing_widget.py` 应视为同一编排域。
3. `src/app/config/advanced_params.py`、`src/app/config/preferences/**` 由主线程统一集成，不建议多个子代理同时落改。
4. `tests/unit/test_signal_handler_batch_manifest.py` 与 `tests/unit/test_batch_processor_file_level_runtime_config.py` 会跟随编排层变更，不应被多个实现代理并发编辑。
