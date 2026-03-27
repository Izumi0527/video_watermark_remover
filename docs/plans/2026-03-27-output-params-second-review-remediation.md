# 输出参数第二轮审查修复计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复第二轮输出参数专项审查确认的 8 个问题，优先消除源文件覆盖、批处理索引漂移与导出追溯失真风险，并补齐对应回归测试。

**Architecture:** 以 `AdvancedParamsSnapshot.resolve_output_config()` 为唯一业务真源，继续收敛到 `output_strategy.py` 作为运行时出口；批处理链路只允许一套文件级输出参数口径；视频导出链路补上路径安全、容器策略与 FFmpeg fallback 一致性保护。

**Tech Stack:** Python、PyQt6、OpenCV、FFmpeg、pytest

---

## 修复优先级

### P0：必须先止血

1. 输入路径与输出路径冲突保护
2. 批处理中移除队列项导致索引漂移
3. `_last_batch_*` 快照污染 manifest

### P1：本轮一并修掉

4. 多进程分块容器与目标容器不一致
5. FFmpeg fallback 参数与目标 codec 不匹配
6. 流水线写帧不足仍按成功处理
7. manifest / 队列输出路径与文件级参数追溯不一致

### P2：结构收敛

8. UI “输出格式”视频语义不清
9. `add_processed_suffix` / 旧 `processing` 输出字段兼容残留继续收口

## 分阶段实施

### 阶段一：运行安全与状态一致性

**目标**

- 禁止输出路径落回输入路径
- 禁止处理中移除导致索引错位
- 清理批次快照污染

**涉及文件**

- `src/app/core/video/output_strategy.py`
- `src/app/ui/signal_handler.py`
- `src/app/ui/widgets/batch/batch_processor_thread.py`
- `src/app/ui/components/file_panel.py`
- `tests/unit/core/video/test_output_strategy.py`
- `tests/unit/test_signal_handler_batch_manifest.py`
- `tests/unit/test_batch_processor_file_level_runtime_config.py`

**验收标准**

- 任意媒体在禁用后缀/时间戳时也不会写回输入文件
- 批处理中不能移除正在依赖索引回写的队列项，或改为稳定 ID 回写
- 从旧批次删除单项后导出 manifest 不会继续复用旧快照

### 阶段二：核心导出链路修复

**目标**

- 多进程输出容器策略统一
- FFmpeg fallback 与目标容器参数模型一致
- 流水线缺帧改为失败态

**涉及文件**

- `src/app/core/video/modes/multiprocess.py`
- `src/app/core/video/workers/chunk.py`
- `src/app/core/video/workers/frame_writer.py`
- `src/app/core/video/modes/pipeline.py`
- `src/app/core/audio/ffmpeg_audio_processor.py`
- `src/app/core/video/modes/single_process.py`
- `tests/unit/core/video/test_output_strategy.py`
- `tests/unit/core/video/test_single_process_output_audio.py`

**验收标准**

- 多进程中间容器策略与最终输出策略一致，不能再靠隐式 `.mp4`
- AVI / WebM / MP4 fallback 命令参数分别受控
- 写帧不足会中断处理并暴露明确错误

### 阶段三：批处理追溯与 UI 语义收敛

**目标**

- manifest item 级保留可回放的输出参数
- `BatchProcessingWidget` 与 `SignalHandler` 对齐为同一输出参数来源
- UI 明示图片/视频的输出格式语义

**涉及文件**

- `src/app/ui/signal_handler.py`
- `src/app/ui/widgets/batch/batch_processing_widget.py`
- `src/app/ui/utils/ai_params_builder.py`
- `src/app/ui/widgets/advanced/tabs/output_tab.py`
- `src/app/config/advanced_params.py`
- `tests/unit/test_signal_handler_output_config.py`
- `tests/unit/test_signal_handler_batch_manifest.py`
- `tests/integration/ui/test_ui_components.py`

**验收标准**

- manifest item 同时记录 `output_path` 与文件级输出参数快照
- 批处理组件旁路不再覆盖文件级输出路径
- UI 对视频场景的输出格式提示明确，避免静默忽略

## 并行修复包

### 修复包 A：批处理编排层

**负责人**

- `batch-orchestrator`

**范围**

- `src/app/ui/signal_handler.py`
- `src/app/ui/widgets/batch/**`
- 相关单测

**任务**

1. 先写失败测试覆盖“处理中移除队列项”“移除后旧批次快照污染”“未启动导出 manifest 输出路径失真”
2. 收敛队列项回写标识，避免索引漂移
3. 统一批处理导出、队列路径和文件级输出参数来源

### 修复包 B：核心输出链路

**负责人**

- `core-engine-implementer`

**范围**

- `src/app/core/video/**`
- `src/app/core/audio/**`
- 相关单测

**任务**

1. 先写失败测试覆盖“输入输出同路径保护”“多进程容器策略”“FFmpeg fallback 参数模型”“流水线缺帧失败”
2. 补上路径安全保护与容器策略
3. 收紧 FFmpeg fallback 与缺帧处理语义

### 修复包 C：UI 与参数表达

**负责人**

- `ui-implementer`

**范围**

- `src/app/ui/widgets/advanced/**`
- `src/app/ui/utils/ai_params_builder.py`
- 相关 UI 测试

**任务**

1. 先写失败测试覆盖视频场景输出格式提示
2. 调整输出格式文案与说明
3. 避免 UI 继续扩散旧输出字段命名

## 本轮验证命令

```powershell
pytest tests/unit/core/video/test_output_strategy.py -q
pytest tests/unit/core/video/test_single_process_output_audio.py -q
pytest tests/unit/test_signal_handler_output_config.py -q
pytest tests/unit/test_signal_handler_batch_manifest.py -q
pytest tests/unit/test_batch_processor_file_level_runtime_config.py -q
pytest tests/integration/ui/test_ui_components.py -q
```

## 风险提醒

1. 当前工作区已有大量输出参数相关未提交改动，修复时只能增量兼容，不能误回退用户现有修改。
2. `signal_handler.py` 与 `batch_processor_thread.py` 高耦合，批处理修复必须一起验证。
3. `output_strategy.py` 是当前运行时出口，任何字段名调整都必须同步测试与 manifest。
