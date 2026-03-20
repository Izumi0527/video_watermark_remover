# 项目专属子代理总览

## 作用

本目录用于保存 `video_watermark_remover` 项目的专属子代理模板与调度规则。
如果你是新会话中的 Codex，想快速知道本项目有哪些子代理、分别负责什么、应该怎么调度，请先读这里。

详细文件：

- `docs/agents/project_subagents.jsonc`
- `docs/agents/dispatch_guide.md`

---

## 固定 5 代理编组

1. `repo-explorer`
   - 类型：`explorer`
   - 作用：只读梳理代码地图、影响面、冲突边界

2. `ui-implementer`
   - 类型：`default`
   - 作用：负责 UI 主界面、预览、参数面板、样式与交互

3. `batch-orchestrator`
   - 类型：`default`
   - 作用：负责批处理、信号、线程状态与进度编排

4. `core-engine-implementer`
   - 类型：`default`
   - 作用：负责 AI、视频、音频处理内核

5. `quality-reviewer`
   - 类型：`reviewer`
   - 作用：负责回归风险、竞态、异常处理与测试缺口审查

替补位：

- `long-task-monitor`
  - 类型：`awaiter`
  - 作用：用于集成测试、E2E、脚本、日志监控

---

## 最短使用流程

1. 先看 `project_subagents.jsonc`
   - 里面保存了可直接复制给 `spawn_agent` 的参数对象

2. 再看 `dispatch_guide.md`
   - 里面定义了推荐调度顺序、冲突边界和替补位规则

3. 默认调度顺序
   - 先起 `repo-explorer`
   - 再并行起 `ui-implementer`、`batch-orchestrator`、`core-engine-implementer`
   - 实现稳定后起 `quality-reviewer`
   - 需要盯长任务时再起 `long-task-monitor`

---

## 快速提醒

- 不要让多个实现代理同时修改 `src/app/ui/signal_handler.py`
- 不要让多个实现代理同时修改 `src/app/ui/widgets/batch/**`
- 不要让多个实现代理同时修改 `src/app/core/ai/**`
- 不要让多个实现代理同时修改 `src/app/core/video/**`
- 不要让多个实现代理同时修改 `src/app/core/audio/**`
- 不要把 `worker` 作为固定席位

---

## 新会话建议

新会话开始时，建议直接按下面这句执行：

`请先按 AGENTS.md 与 docs/agents/project_subagents.jsonc 的项目专属子代理规则工作。`

如果只需要一句最短指令：

`请先读取 docs/agents/project_subagents.jsonc 和 docs/agents/dispatch_guide.md。`
