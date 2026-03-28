# 输出参数剩余风险修复实施计划

> 归档说明：本文件保留第一次拆解时的实施草案，当前以
> `docs/plans/2026-03-27-output-params-remaining-risks-remediation.md`
> 作为继续执行与收口的主计划；若两者描述不一致，以 remediation
> 版本为准。

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复输出参数第二轮审查后仍遗留的 4 项风险，完成结构收敛、批处理稳定标识改造、UI 集成回归入口增强与更大范围验证。

**Architecture:** 继续以 `AdvancedParamsSnapshot` 作为统一参数真源，将 legacy 兼容收缩到单一输入迁移边界；批处理链路从“索引即身份”改为“`file_id` 稳定身份 + 索引仅作视图定位”；GUI 集成测试采用分层可用性探针，把环境问题和业务回归分离。

**Tech Stack:** Python、PyQt6、pytest、PowerShell

---

## 修复优先级

### P0：状态一致性与结构基础

1. 批处理链路引入稳定 `file_id`，替代“索引即身份”的核心假设
2. 为 `file_id` 改造补齐队列、manifest、状态回写与运行时快照测试

### P1：参数结构彻底收敛

3. 收口 `add_processed_suffix` 旧字段读取残留
4. 收口 `processing.output_quality` / `processing.preserve_audio` 旧输出字段残留
5. 统一文档、测试数据与偏好样例为 `add_suffix` / `compression_quality` / `preserve_audio`

### P2：回归入口与验证

6. UI 集成测试改为“导入探针 / QApplication 探针 / 组件实例化探针”分层执行
7. 增补定向回归与更大范围回归命令，明确哪些场景因环境跳过、哪些属于真实失败

## 分阶段实施顺序

### 阶段一：批处理稳定标识重构

**目标**

- 队列项拥有稳定 `file_id`
- 批处理线程、SignalHandler、manifest 导出不再把索引当唯一身份
- 为后续“处理中动态编辑队列”建立安全基础

**涉及文件**

- `src/app/ui/widgets/batch/batch_processor_thread.py`
- `src/app/ui/widgets/batch/batch_file_manager.py`
- `src/app/ui/widgets/batch/batch_processing_widget.py`
- `src/app/ui/signal_handler.py`
- `tests/unit/test_batch_processor_file_level_runtime_config.py`
- `tests/unit/test_signal_handler_batch_manifest.py`
- `tests/unit/test_signal_handler_batch_config_passthrough.py`

**验收标准**

- 新增队列项时生成稳定 `file_id`
- 状态更新、输出路径快照、输出参数快照、manifest item 能携带 `file_id`
- 处理中即使允许局部编辑，也不会因为索引偏移写错状态或路径

### 阶段二：legacy 输出字段兼容层收口

**目标**

- 新导出、新持久化、新日志全部只写统一字段
- legacy 字段只保留在受控输入迁移入口，避免继续向运行时扩散

**涉及文件**

- `src/app/config/advanced_params.py`
- `src/app/config/preferences/defaults.py`
- `src/app/config/preferences/manager.py`
- `src/app/config/preferences/validator.py`
- `src/app/ui/utils/ai_params_builder.py`
- `src/app/ui/signal_handler.py`
- `src/app/core/video/output_strategy.py`
- `tests/unit/test_advanced_params_schema.py`
- `tests/unit/app/config/preferences/test_advanced_params_preferences.py`
- `tests/unit/core/video/test_output_strategy.py`
- `tests/test_data/configs/user_prefs_sample.json`

**验收标准**

- `to_ai_params()`、manifest、批次摘要、测试样例不再写出 `add_processed_suffix`
- `compression_quality` 成为唯一质量字段，`preserve_audio` 只保留统一出口
- 仅 `AdvancedParamsSnapshot.from_dict()` 一类输入迁移入口继续兼容旧字段

### 阶段三：UI 集成回归入口增强

**目标**

- 明确区分“GUI 环境不可用”与“业务组件回归”
- 在 PyQt6 存在但 QtWidgets / QApplication 失败时给出分层跳过原因

**涉及文件**

- `tests/integration/ui/test_ui_components.py`
- `tests/TESTING_GUIDE.md`
- 必要时最小调整 `src/app/entrypoints.py`

**验收标准**

- 测试文件能输出清晰探针结果：模块导入、QApplication 创建、组件实例化
- 外部 DLL/桌面环境异常不会误报为业务代码失败
- 具备可复用的 GUI 可用性检测辅助函数或约定

### 阶段四：更大范围验证

**目标**

- 在完成前三阶段后，执行输出参数相关定向测试 + 更大范围回归
- 输出清晰的“通过 / 跳过 / 受环境限制”结论

**建议命令**

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_signal_handler_batch_manifest.py tests/unit/test_batch_processor_file_level_runtime_config.py tests/unit/test_signal_handler_batch_config_passthrough.py tests/unit/test_signal_handler_output_config.py -q -o addopts=''
.\.venv\Scripts\python.exe -m pytest tests/unit/core/video/test_output_strategy.py tests/unit/core/video/test_single_process_output_audio.py tests/unit/core/video/test_multiprocess_output_container.py tests/unit/core/video/test_ffmpeg_audio_fallback.py -q -o addopts=''
.\.venv\Scripts\python.exe -m pytest tests/unit/app/config/preferences/test_advanced_params_preferences.py tests/unit/test_advanced_params_schema.py tests/integration/ui/test_ui_components.py -q -o addopts=''
```

**扩展回归候选**

- `tests/integration/test_batch_processing.py`
- `tests/integration/test_pipeline_video.py`
- `tests/integration/test_multiprocess_video.py`

## 并行修复拆分

### 修复包 A：批处理稳定标识

**负责人**

- `batch-orchestrator`

**职责**

1. 引入 `file_id` 并收敛批处理状态回写
2. 更新队列操作、manifest item 与文件级快照追溯
3. 补齐稳定标识相关单元测试

### 修复包 B：legacy 字段消费侧收口

**负责人**

- `core-engine-implementer`
- 主代理负责 `config/preferences` 汇总收尾

**职责**

1. 清理 runtime / core / builder / signal_handler 的 legacy 写出和读取残留
2. 确保新链路只输出统一字段
3. 更新输出参数专项测试

### 修复包 C：GUI 回归入口增强

**负责人**

- `ui-implementer`

**职责**

1. 改造 `tests/integration/ui/test_ui_components.py` 的环境探针结构
2. 补充测试说明或辅助函数
3. 运行 UI 集成相关测试并反馈环境约束

### 修复包 D：只读地图与最终审查

**负责人**

- `repo-explorer`
- `quality-reviewer`（实现稳定后再启用）

**职责**

1. 给出冲突边界、最小回归集与剩余风险
2. 在实现稳定后做第二轮审查和测试缺口检查

## 风险提醒

1. `src/app/ui/signal_handler.py`、`src/app/ui/widgets/batch/batch_processor_thread.py`、`tests/unit/test_signal_handler_batch_manifest.py` 是高冲突文件，不应由多个实现代理同时修改。
2. `legacy` 字段清理需要区分“输入兼容”与“新输出继续扩散”，不能一次性删除所有兼容逻辑导致历史配置无法读取。
3. UI 集成测试的核心目标是分清环境问题和业务失败，不是强行让无桌面环境的机器通过真实 GUI 用例。
