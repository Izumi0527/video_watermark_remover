# MAT 后续接入设计

**背景**

在“公开修复模型”的综合权衡里，`LaMa` 更适合作为当前项目的默认主链：

- 接入复杂度更低
- 公开资料和社区验证更充分
- 更适合先替换掉当前轻量 U-Net 的默认地位

但从上限质量看，`MAT` 仍然值得保留为第二阶段高质量模式：

- 它更适合复杂纹理、大面积缺失和更难的结构补全
- 代价是资源更重、推理更慢、环境要求更严格

因此，`MAT` 的正确位置不是第一阶段默认主链，而是第二阶段在“后端抽象层已经稳定”之后接入。

**目标**

第二阶段设计要保证：

- `MAT` 能在不推翻 LaMa 方案的前提下平滑接入。
- `MAT` 与 `LaMa / legacy_unet / opencv` 共用同一套 backend 契约、trace 契约和 batch manifest 契约。
- `MAT` 具备清晰的资源要求、fallback 策略和真实 GPU 验证路径。

**方案选择**

方案 A：等 LaMa 落地后，再临时把 MAT 硬插进 `AIHandler`。

优点：

- 现在不需要额外设计。

缺点：

- 很可能重复第一阶段已经解决过的语义问题。
- 后续又会出现新的 if/else 膨胀。

方案 B：在第一阶段就把 MAT 作为“已保留枚举和扩展位”的后续 backend 方案写清楚，但不在第一阶段实现。

优点：

- 第一阶段抽象层可以一次设计对。
- 第二阶段实现时不必返工 UI、builder、trace 协议。

缺点：

- 需要提前明确接口边界和 fallback 约定。

方案 C：直接跳过 MAT，后续改上扩散模型。

优点：

- 避免当前阶段讨论更重的模型。

缺点：

- 会丢掉一个明显更接近本项目“高质量修复”目标的候选路线。

**推荐**

采用方案 B。

理由：

- 这样可以把 `requested_inpainting_backend=mat` 作为正式枚举预留进去，但不拖慢第一阶段 LaMa 主链。
- 第二阶段只需要新增 backend 实现和测试，不需要再次改协议。

**关键设计**

1. 复用第一阶段 backend 抽象

MAT 不单独发明新入口，直接复用第一阶段新增的：

- `src/app/core/ai/inpainting_backends/base.py`
- `src/app/core/ai/inpainting_backends/factory.py`

第二阶段新增：

- `src/app/core/ai/inpainting_backends/mat_backend.py`

原则：

- `MAT` 与 `LaMa` 在工厂层地位对等。
- `AIHandler` 不出现“专门给 MAT 单独加一套流程”的特例代码。

2. 参数与配置预留

第一阶段即可预留枚举：

- `requested_inpainting_backend=mat`

第二阶段再正式启用的配置项建议：

- `mat_model_path`
- `mat_variant`
- `mat_enable_fp16`
- `mat_tile_size`
- `mat_tile_overlap`
- `mat_max_resolution`

说明：

- `MAT` 通常对显存、分辨率和 tile 策略更敏感。
- 因此它不能只复用 `quality_level` 和 `inpaint_radius`，还需要自己的运行期配置。

3. UI 暴露策略

第二阶段推荐做法：

- 在高级参数面板增加 `MAT 高质量修复（实验）`
- 默认不选中
- 只有当资源校验通过或实验开关开启时才显示为可用

不推荐做法：

- 在第一阶段就把 MAT 当默认选项暴露给所有用户

原因：

- 资源大、环境要求高、GPU 验证复杂
- 一旦体验不稳，会直接拖累第一阶段 LaMa 主链的交付

4. fallback 规则

第二阶段推荐 fallback 顺序：

- 请求 `mat`
  - 资源缺失 / 加载失败 / 显存不满足 / 运行期异常
  - 优先降级到 `lama`
  - `lama` 也不可用时再降级到 `opencv`

trace 要求：

- `requested_inpainting_backend=mat`
- `actual_inpainting_backend=lama` 或 `opencv`
- `inpainting_fallback_reason` 写明首个失败点，例如：
  - `mat_model_missing`
  - `mat_model_load_failed`
  - `mat_oom`
  - `mat_runtime_exception`

这样做的好处：

- 保留“高质量深度修复优先”的策略
- 同时让导出的 manifest 能解释“为什么没有真的跑 MAT”

5. trace 与 batch manifest 契约

MAT 必须完全复用第一阶段已经确立的字段，不另起炉灶：

- `requested_inpainting_backend`
- `actual_inpainting_backend`
- `inpainting_backend`
- `inpainting_fallback_reason`
- `configured_inpainting_asset_ref`
- `loaded_inpainting_asset_ref`
- `gpu_inpainting_runtime_error`
- `effective_quality_level`
- `effective_inpaint_radius`

MAT 专属扩展建议放到独立字典：

- `mat_runtime_profile`
- `mat_retry_profile`

不要把 MAT 特有观测直接塞爆顶层字段。

6. 资源分发与环境约束

MAT 的真实接入风险主要不在算法入口，而在资源和环境：

- 权重体积通常更大
- 可能依赖额外模块或特定推理路径
- 显存占用、tile 参数、半精度稳定性都比 LaMa 更敏感

因此第二阶段必须补：

- 资源格式检查
- 最小显存/分辨率约束
- tile 策略
- fp16 与 fp32 回退策略

7. 测试策略

第二阶段新增：

- `tests/unit/test_mat_backend_selection.py`
- `tests/unit/test_mat_backend_runtime_fallback.py`
- `tests/unit/test_processing_info_backend_trace.py`
  - 增强 MAT -> LaMa -> OpenCV 级联断言
- `tests/integration/runtime/mat_smoke.py`

验证原则：

- 单元测试验证 backend 选择、trace、fallback
- subprocess smoke 验证真实 GPU 资源链路
- 不把 Qt + torch 的真实 GPU 验证塞进默认 pytest 主进程

**实施边界**

第二阶段实施前提：

- 第一阶段 LaMa backend 抽象已经稳定
- `requested/actual/fallback` trace 契约已落地
- Windows 下 subprocess GPU smoke 路线已经验证可用

第二阶段不应再做：

- 重写第一阶段的参数协议
- 重新发明一套 MAT 专用 manifest 结构
- 把 MAT 直接混进 legacy U-Net 代码文件
