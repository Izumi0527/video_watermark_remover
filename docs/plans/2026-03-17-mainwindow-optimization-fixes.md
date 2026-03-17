# 主窗口业务闭环优化修复方案（v0.5.0）

**日期**：2026-03-17  
**范围**：`MainWindow + SignalHandler` 主流程（导入/处理/预览/导出/停止/退出）  
**导出策略**：按“另存为”（复制处理后的输出文件到用户选择路径），**不做格式转换/转码**。
**当前状态**：P0 已完成；已落地部分 P1/P2（实时预览、批量辅助操作、依赖缺失下的测试可运行）。

---

## 0. 进度（截至 2026-03-17）

### P0（必须修复）

- [x] P0-1 导出闭环：导出结果按“另存为复制”完成
- [x] P0-2 线程引用统一：单文件处理线程 stop/cleanup/finished/error 路径一致
- [x] P0-3 临时文件命名安全化：仅改文件名不破坏目录结构
- [x] P0-4 取消处理清理顺序修复：先释放句柄再删除，删除失败仅 warning

### P1（重要优化）

- [x] P1-1 实时预览接入：BGR→RGB + 节流 + 线程信号连接
- [x] P1-2 单文件处理注入 config：与批量一致
- [x] P1-3 批量队列辅助操作：打开输出目录、导出处理清单（JSON）
- [x] P1-4 批量停止体验一致性：统一 stop 能力与 UI 状态

### P2（体验/一致性）

- [x] P2-1 状态栏初始文案与“延迟预加载”逻辑一致
- [x] P2-2 版本号显示一致（`main.py` 与 `MainWindow`）

### 回归验证

- [x] `py_compile`：关键 UI 文件编译通过
- [x] `pytest -q`：`105 passed, 18 skipped`

### 剩余未修复

- 无（主窗口闭环与批量停止一致性已完成；如需继续扩展，可参考第 10 节）

---

## 1. 背景与目标

当前项目 UI 组件拆分清晰（`MainWindow` 负责组装，`SignalHandler` 负责业务协调，`VideoProcessorThread` 负责处理），但主窗口页面存在多处“闭环断点”，会导致：

- 处理完成后“导出”按钮可点击但无法真正导出；
- 停止/关闭窗口时线程清理不一致，可能出现后台线程残留；
- 视频处理临时文件命名不安全，遇到路径/文件名包含 `.` 时容易失败；
- 取消处理时可能因文件句柄未释放导致删除失败并误报为处理失败。

**目标**：优先修复 P0 问题，保证主流程可用且状态一致；随后再逐步补齐 P1/P2 优化（实时预览、config 注入、批量停止等）。

---

## 2. 范围（涉及文件）

### P0（业务闭环必须修复）

- `app/ui/signal_handler.py`
- `app/core/video/single_process_processor.py`
- `app/core/video/multiprocess_processor.py`
- `app/core/video/pipeline_processor.py`
- `app/core/video/video_processor.py`
- `app/core/video/path_utils.py`（新增：临时路径安全生成）

### P1/P2（体验与一致性）

- `app/ui/components/preview_panel.py`（实时预览 UI 接入与节流）
- `app/ui/main_window.py`（状态文案/版本一致性）
- `app/ui/components/file_panel.py`（批量队列辅助操作按钮/信号）
- `app/ui/widgets/batch/batch_processor_thread.py`（批量停止体验）
- `tests/`（缺依赖自动跳过、快慢测分层）

---

## 3. 业务流程（主窗口）

```mermaid
flowchart TD
  A[启动] --> B[MainWindow 组装UI]
  B --> C[连接信号: UI -> SignalHandler]
  C --> D[延迟预加载AI模型(后台线程)]

  U1[选择文件] --> E[SignalHandler.handle_import_file]
  E --> F{单文件/多文件}
  F -->|单文件| G[_handle_single_file: 预览+手动底图]
  F -->|多文件| H[_handle_multiple_files: 入队+预览首个]

  U2[开始处理] --> I[handle_start_processing]
  I --> J{是否批量}
  J -->|否| K[VideoProcessorThread.start]
  J -->|是| L[BatchProcessorThread.start]

  K --> M[core处理: 帧处理/可选音频合并]
  M -->|finished| N[_on_processing_finished: 记录output_path+启用导出]
  M -->|error| O[_on_processing_error]

  U5[批量辅助: 打开输出目录] --> X1[handle_open_output_dir: 打开输出/输入目录]
  U6[批量辅助: 导出处理清单] --> X2[handle_export_batch_manifest: 另存为 JSON]

  U3[导出结果] --> P[handle_export_file]
  P --> Q[按另存为复制 output_file_path 到目标路径]

  U4[停止处理] --> R[handle_stop_processing]
  R --> S[stop: 设置_stop_event + _is_running=False]
```

---

## 4. 问题清单与优先级

### P0（必须修复）

1) **导出闭环断裂**【已完成】  
- 现状：`handle_export_file()` 以 `processed_image` 判断可导出且内部为 TODO；但处理完成会启用导出按钮。  
- 目标：以 `output_file_path` 为唯一真值，导出实现为“复制另存为”。

2) **处理线程引用不一致，导致 stop/cleanup 不可靠**【已完成】  
- 现状：存在 `video_processor` 与 `video_processor_thread` 两套引用；`cleanup()` 只处理其中之一。  
- 目标：统一线程引用与生命周期（创建/停止/完成/清理）。

3) **临时文件命名使用 `replace(".", ...)` 不安全**【已完成】  
- 风险：目录或文件名包含 `.` 时生成非法路径，导致 `rename/remove`/音频合并失败。  
- 目标：使用 `pathlib.Path(stem/suffix)` 只修改文件名，不破坏目录结构。

4) **取消处理时可能因句柄未释放导致删除失败并误报**【已完成】  
- 现状：取消分支先 `os.remove(output_path)`，而 `VideoWriter` 可能尚未释放。  
- 目标：先释放句柄，再删除；删除失败只记录 warning，不转为 error。

### P1（重要优化，后续）

- `preview_update` 实时预览未接入（并需处理 BGR/RGB + 节流）。【已完成】
- 批量停止未覆盖/体验不一致。【已完成】
- 单文件处理未注入 config（批量已注入）。【已完成】
- 批量队列缺少辅助动作：打开输出目录、导出清单（便于定位失败项/复盘）。【已完成】

### P2（体验/一致性）

- 状态栏初始文案与“延迟预加载”逻辑不一致。【已完成】
- 版本号显示（`main.py` vs `MainWindow`）不一致。【已完成】

---

## 5. P0 修复方案（实施要点）

### 5.1 导出“另存为”实现

- `SignalHandler` 维护 `self.output_file_path`（处理完成写入；新导入/清空/失败/取消时清空）。
- `handle_export_file()`：
  - 若 `output_file_path` 为空或文件不存在：提示无可导出结果；
  - 保存对话框默认文件名为处理后的文件名；
  - 对用户选择路径执行 `shutil.copy2(output_file_path, target_path)`；
  - 若用户未写扩展名，则自动补齐源文件扩展名；
  - 记录 `last_output_dir`。

### 5.2 线程引用统一与清理

- 统一使用 `self.video_processor_thread` 保存单文件线程实例。
- `handle_start_processing()` 创建线程后写入该字段，完成/异常/取消后置空。
- `handle_stop_processing()`/`cleanup()` 统一对该字段执行 stop + wait（带超时）。

### 5.3 临时文件路径安全化（3 处替换）

- 将 `output_path.replace(".", "...")` 替换为：
  - `Path(output_path).with_name(f"{stem}__temp_xxx{suffix}")`
- 改名优先使用 `os.replace()`（覆盖旧临时文件，降低重复运行失败概率）。

### 5.4 取消清理顺序修复

- 取消分支中：先 release writer，再尝试删除输出；删除异常仅 warning。

---

## 6. 验收标准（P0）

- ✅ 处理成功后点击“导出结果”，可在目标路径生成文件，大小>0，日志提示成功。
- ✅ 未处理/处理失败/取消时，“导出结果”不可导出（或点击提示明确）。
- ✅ 点击“停止处理”后，处理线程能退出或在超时后给出明确日志，UI 状态恢复。
- ✅ 路径包含 `.` 的目录（例如 `C:/tmp/v1.2.3/a.mp4`）能稳定完成音频合并/文件移动。
- ✅ 取消处理不应误报为“处理失败”，且不留下明显锁定文件。

---

## 7. 风险与回滚

- 风险：修改 stop/临时文件命名可能影响多进程/流水线分支的边界行为。  
  - 缓解：仅改动路径生成与 stop_event 触发，不重构核心算法。
- 回滚：若出现回归，可临时回退到旧逻辑（git revert 对应提交），并保留新日志定位问题点。

---

## 8. 测试与验证建议

由于依赖较重（`PyQt6/cv2/torch`），建议本次 P0 修复优先保证“逻辑正确 + 可运行环境下手工冒烟”。后续补充：

- 快速单测（不依赖 GUI/大模型）：路径生成函数、导出复制逻辑、线程引用状态机。
- GUI/视频处理测试：使用 marker 分层，缺依赖自动 skip，保证默认 quick 集 ≤60s。

---

## 9. 已实施变更摘要（2026-03-17）

### 9.1 P0（闭环）

1) 导出改为“另存为复制”
- `SignalHandler.handle_export_file()` 以 `output_file_path` 为唯一依据：弹出保存对话框后用 `shutil.copy2` 复制到目标路径，强制保持源扩展名（不做转码/格式转换）。

2) 单文件处理线程生命周期统一
- 统一使用 `self.video_processor_thread`：start/stop/finished/error/cleanup 全路径一致，避免残留线程与状态不同步。

3) 临时文件命名安全化
- 新增 `app/core/video/path_utils.py` 的 `build_temp_path()`，替换多处 `output_path.replace(".", ...)` 的不安全逻辑；关键改名操作改为 `os.replace()`（覆盖式更稳）。

4) 取消处理清理顺序修复
- 取消分支先释放 `VideoWriter` 再删文件；删除失败仅 warning，不误报为处理失败。

5) 停止能力增强
- `VideoProcessorThread.stop()` 同步触发 `_stop_event.set()`，让多进程/流水线分支更可停止。

### 9.2 已落地的 P1/P2（体验与可维护性）

1) 实时预览接入（处理过程中）
- `PreviewPanel` 新增 `update_processing_preview_from_bgr()`：BGR→RGB，并加入约 0.12s 节流；`SignalHandler` 连接线程 `preview_update` 信号到预览更新。

2) 批量队列辅助操作（新增按钮）
- 队列区域新增：`打开输出目录`、`导出处理清单`。
- `handle_open_output_dir(index)`：优先选中项，否则第 0 项；从 `output_path/input_path` 推导目录并打开。
- `handle_export_batch_manifest(parent_widget)`：生成 `generated_at/stats/items[]` 的 JSON 清单，通过“另存为”保存。

3) 依赖缺失下的基础回归可运行
- 多个包入口改为惰性导入，并对重依赖相关测试使用 `pytest.importorskip`；新增 `tests/unit/test_path_utils.py` 覆盖临时路径生成逻辑。

4) 版本与状态一致性
- `main.py` 设置应用版本为 `0.5.0`；主窗口初始状态文案不再误报“模型已就绪”。

5) 批量停止体验一致性（取消态）
- 批量 stop 不阻塞 UI：点击“停止处理”后立即返回；由 `batch_completed` 统一收尾。
- 取消时将队列中 `WAITING/PROCESSING` 项统一标记为 `CANCELLED`，避免误判为失败；队列显示增加 `⏹️` 图标与取消数统计。

### 9.3 回归结果（本地）

- `python -m py_compile app/ui/components/file_panel.py app/ui/main_window.py app/ui/signal_handler.py app/ui/widgets/batch/batch_processor_thread.py app/ui/widgets/batch/batch_processing_widget.py`：通过
- `python -m pytest -q`：`105 passed, 18 skipped`

---

## 10. 后续建议（可选）

1) [x] 打开输出目录体验增强（Windows）
- 若输出文件已存在，使用 `explorer /select,` 直接定位并选中该文件；否则打开目录。

2) [x] 无桌面环境反馈
- `xdg-open/open/explorer/os.startfile` 失败或返回码异常时提示用户，避免“看起来没反应”。

3) [x] 清单信息增强
- 清单 root 增加 `app_version/platform/os_name/batch` 等元信息，便于问题追踪。
