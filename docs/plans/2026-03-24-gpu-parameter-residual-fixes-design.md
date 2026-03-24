# GPU 参数残余风险修复设计

**背景**

上一轮审查确认 GPU 修复参数主链路已经闭环，但仍保留 3 个会影响稳定性或追溯可信度的残余问题：

1. 历史或未知 `inpainting_method` 会被静默映射到 `gpu_dl`，存在把 OpenCV 意图误导向 GPU 的风险。
2. GPU 深度学习修复在模型已加载成功后，如果单帧运行期抛异常，当前实现会直接返回原帧，而不会降级到 OpenCV 继续修复。
3. `processing_info` 与 batch manifest 中记录的 `quality_level` 是请求值，不一定等于 OpenCV 或 GPU 路径实际归一化后的生效值。

**目标**

本次修复要做到：

- 对历史/兼容输入给出稳定、可解释的算法映射，不再让未知值静默偏向 GPU。
- GPU 运行期出现单帧异常时，当前帧仍能自动回退到 OpenCV，尽量保证“继续可用”。
- 追溯信息同时保留兼容字段与实际生效字段，让 manifest 可用于排障与复盘。

**方案选择**

方案 A：最小化兼容修复。

- 在 `AIParamsBuilder` 中补别名映射，未知值回退到安全的 OpenCV `auto`。
- 在 `AIHandler` 中仅对 GPU 分支做局部异常拦截，失败后切回 OpenCV。
- 新增 `effective_quality_level` 字段，保留原有 `quality_level`。

优点：

- 改动集中在当前热点文件，影响面可控。
- 不破坏现有 manifest 或 `processing_info` 的旧读法。
- 能快速补齐回归测试。

缺点：

- 仍保留请求值与实际值并存的双字段语义，需要调用方逐步迁移到新字段。

方案 B：引入统一的“修复执行观测对象”。

- 将算法请求值、实际后端、有效质量等级、降级原因统一封装到独立结构中。
- `processing_info` 和 manifest 全量输出该结构。

优点：

- 语义最完整，后续扩展最自然。

缺点：

- 改动面明显扩大，会影响现有导出结构和消费方。
- 对本轮目标偏重。

方案 C：严格拒绝未知 `inpainting_method`。

- 遇到未知方法直接报错或中止构建参数。

优点：

- 问题暴露最直接。

缺点：

- 会破坏历史配置导入、脚本调用和旧偏好回放。
- 与当前产品“优先继续可用”的方向不一致。

**推荐**

采用方案 A。

理由：

- 它同时解决“兼容输入误路由”“运行期继续可用”“追溯字段失真”这 3 个问题。
- 它不要求大范围改协议，也不会把旧调用方一下子打断。
- 后续如果需要统一观测结构，还能在此基础上平滑演进。

**关键设计**

1. 参数兼容映射

- 在 `AIParamsBuilder._map_inpainting_method()` 中补充对历史值/别名的兼容：
  - `auto` / 空值等回退到安全 OpenCV 算法 `auto`
  - `ns` / `navier-stokes` / `navier_stokes` 归一到 `navier_stokes`
  - `custom` / `custom_interpolation` 归一到 `custom_interpolation`
  - `gpu_dl` 归一到 `gpu_dl`
- 当前实现同步扩展验证器允许值，把所有兼容映射最终收敛到验证器已接受的集合：
  - `auto`
  - `gpu_dl`
  - `telea`
  - `navier_stokes`
  - `custom_interpolation`
- 完全未知值会记录 warning，并安全回退到 `auto`，避免再次误触发 GPU 路径。

2. GPU 运行期降级

- 在 `AIHandler.inpaint_frame()` 中把 GPU 调用包成局部步骤：
  - GPU 成功：保持现有观测字段写入。
  - GPU 异常：记录日志与明确降级原因，立即切到 OpenCV，并停用当前 handler 后续 GPU 修复能力。
- 当前实现会保留 `loaded_inpainting_model_path` 以便追溯，但会清空 `dl_inpainter` 并将 `use_gpu_inpainting` 设为 `False`，避免后续帧重复触发相同异常。
- 若 OpenCV 也失败，才退回原帧。

3. 追溯字段准确性

- 保留旧字段 `quality_level`，语义继续表示“请求质量等级”。
- 新增：
  - `requested_quality_level`
  - `effective_quality_level`
  - `effective_inpaint_radius`
  - `gpu_inpainting_runtime_error`
- 字段来源：
  - OpenCV 路径取 `ImageInpainter.last_quality_level`
  - OpenCV 半径取 `ImageInpainter.last_effective_radius`
  - GPU 路径优先取 `last_gpu_inpainting_profile_used` 中的 `quality_level` 与 `requested_radius`
- batch manifest 的 `processing_details` 一并透传这些字段。
- 对旧 `processing_info` 若缺少 `effective_quality_level`，batch 层会基于 `quality_level` 做 1-5 的最小补位，避免 manifest 追溯断档。

**测试策略**

- 为 `AIParamsBuilder` 增加兼容映射单测，覆盖旧值、别名、未知值安全回退与验证器 `auto` 兼容。
- 为 `AIHandler` 增加 GPU 运行期异常降级单测，断言当前帧会落到 OpenCV 且记录降级原因。
- 为 `processing_info` 增加请求值/生效值追踪单测，断言 `requested_quality_level`、`effective_quality_level` 与 GPU/OpenCV 路径一致。
- 为 batch manifest 增加追溯字段单测，断言 `quality_level`、`requested_quality_level` 与 `effective_quality_level` 同时存在且含义正确。
