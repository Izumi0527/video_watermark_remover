# 单进程 LaMa 吞吐提速设计

## 背景

当前 GPU 深度修复在运行时安全护栏下会收敛到单进程路径，主处理链路位于：

- `src/app/ui/signal_handler.py`
- `src/app/ui/utils/ai_params_builder.py`
- `src/app/core/video/thread.py`
- `src/app/core/video/modes/single_process.py`
- `src/app/core/ai/ai_handler.py`

基于代码事实，单进程路径的主要吞吐损耗不在 LaMa 是否已经做 ROI，而在三个更靠前的热点：

1. YOLO 检测仍按逐帧串行调用，未复用 `YOLOWatermarkDetector.detect_batch()`
2. 修复后的后处理仍以整帧为单位执行，掩码很小时也会重算整帧
3. `AIHandler.process_frame()` 与 LaMa 写回路径存在多处整帧复制，空掩码/轻量场景也会付出复制成本

## 目标

在不改变现有 UI 参数语义、不放宽 GPU 深度修复串行护栏的前提下，优先提升单进程 LaMa 路径的有效吞吐，降低每帧 CPU 内存拷贝和整帧后处理开销。

本轮目标不包含：

- 新增跨帧缓存策略
- 放开 GPU 深度修复进入流水线/多进程
- 改写 LaMa TorchScript runtime 底层张量实现

## 方案对比

### 方案一：只做默认值和参数预设收敛

优点：

- 改动小，风险低
- 可以快速减少不必要的预处理/后处理开销

缺点：

- 无法解决逐帧 YOLO 检测串行开销
- 无法解决整帧后处理和整帧复制热点
- 更偏“绕开问题”，不是直接提升核心链路吞吐

### 方案二：只优化 LaMa runtime / ROI

优点：

- 理论上可以继续挖 GPU 推理侧性能

缺点：

- 当前代码已经具备 ROI 裁剪、按预算缩放、局部写回
- 现阶段不是最主要瓶颈
- 风险较高，且收益不一定先于检测批处理

### 方案三：围绕单进程链路做分层提速

优点：

- 直接打在当前最热的三个路径上
- 可以复用现有 `detect_batch()` 和现有 LaMa ROI 设计
- 风险相对可控，适合以 TDD 渐进落地

缺点：

- 需要同步修改 `single_process.py`、`ai_handler.py`、`image_processor.py`
- 需要补足新的单元测试与回归测试

## 选型

采用方案三，并按以下顺序实施：

1. 单进程读取改为“小批量取帧 + 批量检测 + 逐帧修复/写回”
2. 后处理改为 ROI/局部区域执行，避免整帧重算
3. 减少无效整帧复制，补上无水印快速路径

原因：

- 这三个点是当前代码中最明确、最稳定、最容易验证收益的热点
- 改造顺序从“收益最大且边界清晰”到“细节优化”，便于逐步回归

## 架构设计

### 1. 单进程小批量检测

在 `src/app/core/video/modes/single_process.py` 中引入“小批量帧窗口”：

- 保持视频读取、写出、音频合并仍在单线程主循环内
- 每次读取一批帧，例如按 `YOLOWatermarkDetector.batch_size` 或更保守阈值组帧
- 自动检测模式下优先走 `AIHandler.process_frames_batch()`
- 手动掩码模式或检测器不可用时，回退到现有逐帧 `process_frame()`

批量处理的职责边界：

- 检测阶段批量化
- 修复阶段仍逐帧调用现有 `inpaint_frame()`
- 写回与进度更新仍按原有帧序执行，避免改变输出顺序与 UI 节奏

### 2. AIHandler 批处理入口

在 `src/app/core/ai/ai_handler.py` 中新增批处理共享路径，避免在 `single_process.py` 内复制过多业务逻辑：

- 新增面向单进程路径的 `process_frames_batch()` 方法
- 内部统一处理：
  - 预处理是否启用
  - 自动检测模式下的批量掩码构建
  - 每帧修复和处理信息生成
  - 与单帧模式一致的 `processing_info` 字段

这样做的目的：

- 把“检测批量化、修复串行化”的逻辑收敛到 AI 层
- 保持视频模式层只负责 I/O、进度与状态管理

### 3. ROI 后处理

在 `src/app/core/ai/image_processor.py` 中新增局部后处理能力：

- 基于 mask 计算局部 ROI
- 对 `smooth / blend / enhance` 只处理 ROI 子图
- 再写回原始 `processed` 帧对应区域
- 当 ROI 过大或 mask 为空时，安全回退到现有整帧逻辑

配套地，在 `AIHandler.process_frame()` 和批处理共享逻辑中：

- 只有真正启用后处理且 mask 非空时才触发局部后处理
- 保持 `postprocessing_applied` 的观测字段不变

### 4. 复制优化

在 `src/app/core/ai/ai_handler.py` 中做两类复制收敛：

- `original_frame` 改为 lazy copy：只有启用后处理时才复制原始帧
- 无水印路径尽量返回原始帧或已知安全引用，避免 `frame.copy()`

在 `src/app/core/ai/inpainting_backends/lama_backend.py` 中：

- 仅在 ROI 写回确有必要时复制整帧
- 保持“只覆写 mask 区域”的稳定性约束不变

## 数据流

单进程自动检测路径将变为：

1. `single_process.py` 连续读取一小批帧
2. `AIHandler.process_frames_batch()` 对这一批帧统一做检测预处理
3. 调用 `YOLOWatermarkDetector.detect_batch()` 返回逐帧 mask
4. 每帧继续串行走 `inpaint_frame()`
5. 若启用后处理，仅在 mask ROI 上执行后处理
6. 返回按原顺序排好的 `processed_frame + processing_info`
7. `single_process.py` 逐帧写出、发预览、更新进度

## 错误处理

需要保持以下稳定性原则：

- 批量检测异常时，不能导致整批中断；应允许降级回逐帧检测或逐帧原样输出
- 单帧修复异常仍保持当前行为：记录错误并回退到原帧
- ROI 后处理异常不能影响整帧结果，应回退到整帧后处理或跳过后处理
- 所有降级都要尽量保留 `processing_info["error"]` 或现有追踪字段

## 测试设计

本轮以 TDD 落地，优先补三类测试：

1. 单进程自动检测路径会优先走批量检测，而不是严格逐帧检测
2. 后处理在小掩码场景下只处理 ROI，而不是把整帧再次送入处理
3. 无水印或未启用后处理时，不再发生不必要的整帧复制

回归范围：

- `tests/unit/core/video/` 下单进程模式测试
- `tests/unit/test_dynamic_watermark_tracking.py` 风格的 AIHandler 轻量测试
- `tests/unit/test_lama_backend_roi_inpainting.py` 风格的 ROI/写回稳定性测试

## 风险与控制

主要风险：

- 批量检测引入后，预览/进度节奏可能与逐帧路径略有差异
- ROI 后处理若边界计算不稳，可能带来局部接缝或覆盖范围不足
- 复制优化若误用了共享引用，可能污染原始帧

控制手段：

- 保持写出顺序、进度更新频率和预览触发条件不变
- ROI 后处理提供“空掩码/大 ROI/异常”三类回退
- 用单元测试断言输入帧不被意外修改

## 实施顺序

1. 先补失败测试，锁定批量检测入口与 ROI 后处理行为
2. 再实现 `AIHandler` 批处理入口和 `single_process.py` 小批量循环
3. 然后实现 `image_processor.py` 局部后处理
4. 最后做 lazy copy 与无水印快速路径收敛
