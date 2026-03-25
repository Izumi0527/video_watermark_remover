# LaMa 默认修复后端接入设计

**背景**

当前仓库的“检测”和“修复”能力并不对称：

1. `models/` 下现有权重是 YOLO 检测模型，不是可直接用于 GPU 修复的 U-Net 权重。
2. 现有 GPU 修复链路绑定在 `DeepLearningInpainter + 轻量 U-Net` 上，参数语义依赖 `use_gpu_inpainting + inpainting_algorithm=gpu_dl`，已经难以继续承载更强公开修复模型。
3. 批处理导出的 `manifest` 与运行期 `processing_info` 已经补出“请求值 / 实际值”的雏形，但对“请求后端 / 实际后端 / 降级原因”的表达仍不够通用。

用户已经确认采用默认路线：

- `LaMa` 作为默认 GPU 修复后端
- 现有轻量 U-Net 降级为 `legacy/兼容备用`
- `MAT` 作为后续高质量模式，不进入第一阶段默认主链

**目标**

第一阶段要做到：

- 让 `LaMa` 成为项目默认深度修复后端。
- 把当前“修复算法”和“修复后端”解耦，停止继续扩展 `gpu_dl` 语义。
- 保留现有轻量 U-Net 作为兼容备用，不破坏历史参数与旧回归测试。
- 让 `processing_info`、batch `processing_details`、导出的 `manifest` 能准确记录：
  - 请求修复后端
  - 实际执行后端
  - 降级原因
  - 资源引用与运行期错误
- 在 Windows 下规避 `PyQt6 -> torch` DLL 冲突，把真实 GPU smoke 固定为 subprocess 路线。

**方案选择**

方案 A：继续把 LaMa 直接塞进 `ai_handler.py` 和 `dl_inpainter.py`。

优点：

- 初期改文件少。

缺点：

- `AIHandler` 会继续膨胀。
- `dl_inpainter.py` 会同时承载 legacy U-Net 与 LaMa 两套模型语义，后续再接 MAT 会更乱。
- trace、fallback、模型资源管理很难统一。

方案 B：引入统一的 inpainting backend 适配层，由 `AIHandler` 只负责选择、加载、降级和追溯。

优点：

- 后端职责清晰，LaMa、legacy U-Net、OpenCV、后续 MAT 都能走同一套契约。
- 更容易统一 `processing_info`、batch manifest、运行期 fallback。
- 后续切换默认模型不会再改一大片 if/else。

缺点：

- 第一阶段改动面会从单文件扩大到参数、线程、batch trace 和测试层。

方案 C：直接删除 legacy U-Net，只保留 LaMa 和 OpenCV。

优点：

- 语义最干净。

缺点：

- 会打断历史配置、旧测试、旧 manifest 的兼容读取。
- 第一阶段风险过高。

**推荐**

采用方案 B。

理由：

- 它能一次性解决“后端抽象”“参数语义”“fallback 追溯”“后续 MAT 扩展”四个问题。
- 它允许我们把 legacy U-Net 收敛成兼容备用，而不是继续当默认主链。
- 它和当前项目已有的 batch/manifest 回归体系最匹配，便于持续验证。

**关键设计**

1. 统一后端抽象

新增目录：

- `src/app/core/ai/inpainting_backends/__init__.py`
- `src/app/core/ai/inpainting_backends/base.py`
- `src/app/core/ai/inpainting_backends/factory.py`
- `src/app/core/ai/inpainting_backends/opencv_backend.py`
- `src/app/core/ai/inpainting_backends/legacy_unet_backend.py`
- `src/app/core/ai/inpainting_backends/lama_backend.py`

抽象目标：

- `AIHandler` 不再直接操纵 `ImageInpainter` 与 `DeepLearningInpainter` 的组合细节。
- 每个 backend 负责：
  - 模型/资源加载
  - 单帧修复
  - 自身运行期 trace
  - 清理资源
- `factory.py` 负责从统一参数中选择 backend，并返回可执行对象。

`AIHandler` 只保留：

- 设备选择
- detector 生命周期
- backend 选择与切换
- fallback 协调
- `processing_info` 聚合

2. 参数语义重构

第一阶段新增统一参数：

- `requested_inpainting_backend`
  - `opencv`
  - `lama`
  - `legacy_unet`
  - `mat`
- `opencv_inpainting_method`
  - `auto`
  - `telea`
  - `navier_stokes`
  - `custom_interpolation`

兼容规则：

- 历史 `inpainting_algorithm=gpu_dl` 映射到 `requested_inpainting_backend=legacy_unet`
- 历史 `telea/navier_stokes/custom_interpolation/auto` 映射到 `requested_inpainting_backend=opencv`
- 历史 `use_gpu_inpainting` 仅作为兼容输入，不再作为新主协议

迁移原则：

- UI、builder、validator、thread、manifest 一律以 `requested_inpainting_backend` 为主。
- `inpainting_algorithm` 保留为兼容字段，不再继续承担“后端选择”职责。
- `use_gpu_inpainting` 不再作为新 UI 的主控制项，仅用于旧偏好读取和兼容测试。

3. UI 与参数构建改造

重点改动文件：

- `src/app/ui/widgets/advanced/tabs/inpainting_tab.py`
- `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- `src/app/ui/utils/ai_params_builder.py`
- `src/app/config/validators.py`

UI 方案：

- 修复算法下拉框改为明确的“修复后端/算法”文案：
  - `LaMa 深度学习修复（推荐）`
  - `兼容 U-Net 深度修复（旧模型）`
  - `TELEA 快速修复（OpenCV）`
  - `Navier-Stokes 高质量（OpenCV）`
  - `自定义插值方法`
- `enable_gpu` 不再决定是否使用深度学习修复后端。
- 设备仍由现有 `device` 路径控制，深度后端按设备实际可用性运行。

Builder 方案：

- `AIParamsBuilder` 输出：
  - `requested_inpainting_backend`
  - `opencv_inpainting_method`
  - `inpainting_algorithm`（兼容保留）
  - `inpaint_radius`
  - `quality_level`
- 对历史文本、旧偏好、别名和未知值做收敛映射。
- 未识别输入安全回退到 `requested_inpainting_backend=opencv` + `opencv_inpainting_method=auto`。

4. AIHandler 与运行期 fallback

重点改动文件：

- `src/app/core/ai/ai_handler.py`
- `src/app/core/ai/dl_inpainter.py`

第一阶段 fallback 规则：

- 请求 `lama`
  - LaMa 资源缺失 / 加载失败 / 运行期异常
  - 降级到 `opencv`
- 请求 `legacy_unet`
  - legacy U-Net 权重缺失 / 加载失败 / 运行期异常
  - 降级到 `opencv`
- 请求 `opencv`
  - 不再额外走深度后端

统一追溯字段：

- `requested_inpainting_backend`
- `actual_inpainting_backend`
- `inpainting_backend`
  - 兼容字段，值等于 `actual_inpainting_backend`
- `inpainting_fallback_reason`
- `gpu_inpainting_requested`
  - 兼容字段，含义为“是否请求了深度修复后端”
- `gpu_inpainting_fallback_reason`
  - 兼容字段，第一阶段保持与 `inpainting_fallback_reason` 同步

资源引用字段：

- 新增通用：
  - `configured_inpainting_asset_ref`
  - `loaded_inpainting_asset_ref`
- 兼容保留：
  - `configured_inpainting_model_path`
  - `loaded_inpainting_model_path`

说明：

- LaMa 往往不是单一 `.pth` 文件，而是一组模型资源或目录。
- 因此第一阶段 trace 必须支持“目录或资源标识”，不能继续只围绕单个 model path 设计。
- 第一阶段真实 runner 的落地形态收敛为：
  - 直接指向 `TorchScript` 模型文件，例如 `big-lama.pt`
  - 或指向包含 `big-lama.pt` 的目录
- 对官方训练导出目录（`config.yaml + models/*.ckpt`）第一阶段只做识别与明确报错，
  暂不在主工程内直接拉起完整训练依赖链。

5. 模型资源与下载策略

新增：

- `src/app/utils/inpainting_model_downloader.py`

原则：

- 不把 LaMa 资源逻辑继续塞进现有 `src/app/utils/model_downloader.py`
- backend 资源下载/校验单独收口
- legacy U-Net 与 LaMa 使用不同资源解析路径

第一阶段只要求：

- 支持本地已准备好的 LaMa 资源目录或权重引用
- 支持基础存在性检查与错误提示
- 不在本轮强制实现全自动下载
- 推荐资产形态是本地 `TorchScript` 文件或包含该文件的目录
- 若用户提供的是官方 checkpoint 目录，系统应给出“需要转换为 TorchScript”这一明确提示

6. 线程刷新与预加载复用

重点改动文件：

- `src/app/core/video/thread.py`

必须扩展 `AI_HANDLER_REFRESH_KEYS`，至少纳入：

- `requested_inpainting_backend`
- `opencv_inpainting_method`
- `inpainting_model_path`
- `lama_model_path` 或 `lama_model_dir`
- 与 backend 选择直接相关的其他关键推理参数

理由：

- 如果不刷新，预加载 `AIHandler` 可能继续复用旧 backend。
- 那么 manifest 里记录的是新请求参数，实际处理却仍走旧后端，追溯会失真。

7. batch manifest 与 processing_info 追溯

重点改动文件：

- `src/app/ui/widgets/batch/batch_processor_thread.py`
- `src/app/ui/signal_handler.py`

新增/增强透传字段：

- `requested_inpainting_backend`
- `actual_inpainting_backend`
- `inpainting_fallback_reason`
- `configured_inpainting_asset_ref`
- `loaded_inpainting_asset_ref`

兼容保留：

- `inpainting_backend`
- `gpu_inpainting_fallback_reason`
- `configured_inpainting_model_path`
- `loaded_inpainting_model_path`

导出原则：

- `run.ai_params` 永远代表请求快照
- `items[*].processing_details` 永远代表实际执行观测

8. 测试策略

新增或重点增强：

- `tests/unit/test_inpainting_backend_selection.py`
- `tests/unit/test_lama_backend_runtime_fallback.py`
- `tests/unit/test_processing_info_backend_trace.py`
- `tests/unit/test_ai_params_builder_inpainting_compatibility.py`
- `tests/unit/test_batch_processing_details_effective_params.py`
- `tests/unit/test_signal_handler_batch_manifest.py`

新增运行期 smoke：

- `tests/integration/runtime/lama_smoke.py`
- pytest 包装测试通过 subprocess 调用该脚本

关键约束：

- 不在默认 pytest 主进程里直接把 `PyQt6` 与 `torch` GPU 运行时混装验证。
- 真实 GPU smoke 统一放到 subprocess 脚本里执行，避免 Windows DLL 冲突把测试进程拖崩。
- 为了让 CI/本地回归可重复，允许通过临时 TorchScript stub 模型验证 smoke 链路本身；
  真正的 LaMa 权重质量验证仍依赖用户提供的 `VWR_LAMA_MODEL_PATH`。

**非目标**

- 本轮不实现 MAT 后端。
- 本轮不删除 legacy U-Net 兼容路径。
- 本轮不做 LaMa 资源自动联网下载闭环。
- 本轮不重构 detector、audio 或视频模式流水线主结构。
