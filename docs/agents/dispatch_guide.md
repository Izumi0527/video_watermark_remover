# 项目专属子代理调度指南

## 目标

本指南用于 `video_watermark_remover` 项目的多子代理协作。
目标不是把代理“平均分配”，而是让每个代理拥有稳定职责边界、清晰写入范围和最小冲突面。

固定编组不使用 `worker`。
默认使用 5 个席位：

1. `repo-explorer`
2. `ui-implementer`
3. `batch-orchestrator`
4. `core-engine-implementer`
5. `quality-reviewer`

如进入长时间测试、脚本或日志监控阶段，可临时用 `long-task-monitor` 替换 `quality-reviewer`。

---

## 固定编组说明

### 1. `repo-explorer`

- 类型：`explorer`
- 角色：只读侦察
- 职责：建立代码地图、调用链、影响面、多人协作边界
- 原则：不改代码，不做破坏性操作

### 2. `ui-implementer`

- 类型：`default`
- 角色：主界面与交互实现
- 职责：主窗口、预览、参数面板、样式和交互细节
- 主要写入范围：
  - `src/app/ui/main_window.py`
  - `src/app/ui/components/**`
  - `src/app/ui/widgets/advanced/**`
  - `src/app/ui/widgets/image_selector_widget.py`
  - `src/app/ui/widgets/selectable_image_label.py`
  - `src/app/config/styles/**`

### 3. `batch-orchestrator`

- 类型：`default`
- 角色：批处理与信号编排实现
- 职责：批量队列、线程状态、信号流、进度和取消逻辑
- 主要写入范围：
  - `src/app/ui/signal_handler.py`
  - `src/app/ui/widgets/batch/**`
  - `src/app/ui/components/detailed_progress_widget.py`
  - `src/app/ui/components/log_panel.py`
  - 与批处理直接相关的测试

### 4. `core-engine-implementer`

- 类型：`default`
- 角色：AI、视频、音频处理内核实现
- 职责：水印检测修复、视频流水线、音频链路、模型加载、GPU 降级
- 主要写入范围：
  - `src/app/core/ai/**`
  - `src/app/core/video/**`
  - `src/app/core/audio/**`
  - `src/app/utils/model_downloader.py`
  - 与 core 逻辑直接相关的测试

### 5. `quality-reviewer`

- 类型：`reviewer`
- 角色：代码审查与回归风险把关
- 职责：找 bug、找回归、找竞态、找缺测试
- 原则：默认不改业务代码，除非主代理明确授权

---

## 推荐调度顺序

### 阶段一：侦察

先启动 `repo-explorer`，让它输出：

- 模块地图
- 高耦合文件
- 当前热点文件
- 冲突边界
- 最小回归测试清单

### 阶段二：并行实现

在 `repo-explorer` 输出代码地图后，并行启动：

1. `ui-implementer`
2. `batch-orchestrator`
3. `core-engine-implementer`

此阶段主代理负责：

- 统一需求口径
- 分配写入边界
- 接收各代理回报
- 处理跨域接口变化

### 阶段三：审查

功能改动进入稳定状态后，启动 `quality-reviewer` 做审查。

重点检查：

- GUI 行为回归
- 批处理竞态
- 线程退出与资源释放
- 音频链路完整性
- GPU/模型失败时的降级路径
- 测试缺口与回归建议

### 阶段四：长任务监控

当主代理需要跑较慢任务时，可临时起 `long-task-monitor`：

- 集成测试
- E2E 测试
- `scripts/vwr.ps1`
- 长时间批处理
- 日志监控

默认做法：

- 保留固定 5 代理编组
- 仅在需要盯长任务时额外启用 `long-task-monitor`

资源紧张时的替换做法：

- 暂停 `quality-reviewer`
- 用 `long-task-monitor` 顶替
- 长任务结束后再恢复 `quality-reviewer`

---

## 冲突边界

以下文件或目录不建议由多个实现代理同时修改：

- `src/app/ui/signal_handler.py`
- `src/app/ui/widgets/batch/**`
- `src/app/core/video/**`
- `src/app/core/audio/**`
- `src/app/core/ai/**`
- `scripts/vwr.ps1`

建议的边界约束：

- `ui-implementer` 不碰 `src/app/ui/signal_handler.py` 和 `src/app/ui/widgets/batch/**`
- `batch-orchestrator` 不下沉重构 `src/app/core/**`
- `core-engine-implementer` 不跨入 `src/app/ui/**`
- `quality-reviewer` 默认不改业务代码
- `repo-explorer` 永远不改代码

---

## 输出协议

所有项目专属子代理统一使用四段输出：

1. 结论
2. 产物
3. 风险
4. 下一步

要求：

- 产物必须列出明确文件路径
- 风险必须写清影响面
- 下一步必须明确交接对象

---

## 使用建议

### 建议一：把模板当作固定资产

`docs/agents/project_subagents.jsonc` 应视为本项目的协作基线。
新增成员或新会话进入时，优先复用该文件中的模板，不要每次重新设计 prompt。

### 建议二：主代理只做整合与验证

主代理尽量不要和实现代理争抢同一批文件。
主代理更适合承担：

- 分派任务
- 收敛接口
- 汇总结果
- 跑验证
- 做最终集成

### 建议三：按阶段换位，不要一开始就上所有类型

默认固定席位已经够用。
只有在需要盯长时间命令、日志或测试时，再切出 `long-task-monitor`。

---

## 与 `spawn_agent` 的关系

本项目不会新增自定义 `agent_type`。
“项目专属子代理”的实现方式是：

1. 使用内置类型：`default`、`explorer`、`reviewer`、`awaiter`
2. 将本项目专属职责边界固化到 prompt
3. 把 prompt 保存到仓库中复用

因此，`docs/agents/project_subagents.jsonc` 中保存的是“可直接复制到 `spawn_agent` 的参数对象”。

---

## 维护规则

当以下任一情况发生时，应更新模板：

- 目录结构发生明显变化
- 关键热点文件迁移
- 批处理或 core 处理链路重构
- 测试分层策略变化
- 主代理发现多个子代理频繁冲突

更新时优先改：

1. 写入范围
2. 禁止范围
3. 输出协议
4. 替补位使用时机
