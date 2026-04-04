# 智能视频水印去除工具 🎬

<div align="center">

**面向图片与视频的 AI 水印检测、修复与批处理桌面工具**

[![Python](https://img.shields.io/badge/Python-3.12.10-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6.0+-green.svg)](https://www.qt.io/qt-for-python)
[![uv](https://img.shields.io/badge/uv-workflow-4B8BBE.svg)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v0.7.23-orange.svg)](https://github.com/Izumi0527/video_watermark_remover/releases)

**v0.7.23** | 更新日期：2026-04-04 | Windows 为主要支持平台

[快速开始](#快速开始) • [更新重点](#更新重点) • [功能特性](#功能特性) • [安装与运行](#安装与运行) • [使用说明](#使用说明) • [测试与质量](#测试与质量) • [文档索引](#文档索引)

</div>

---

## 📌 项目简介

智能视频水印去除工具面向图片与视频场景，提供水印检测、区域修复、音频保留、批量队列和图形化预览能力。项目当前以 `PyQt6 + OpenCV + PyTorch + Ultralytics + FFmpeg + uv` 为核心技术栈，仓库代码已经收敛到 `src/app` 布局，并通过统一脚本入口 `.\scripts\vwr.ps1` 以交互式菜单管理环境、运行、测试、质量检查与打包流程。

这个项目目前更适合以下使用场景：

- 图片或短视频的局部水印清理
- 需要保留原始音频的视频导出
- 需要批量处理、导出清单和追踪失败项的桌面工作流
- 在 Windows 环境下用统一脚本快速搭好开发/运行环境

---

## ✨ 更新重点

### v0.7.23（2026-04-04）

- ✅ 复杂图片掩码优化新增 `MaskRefiner`，加强噪点清理、裂缝桥接、短线缺口填补与稳定孔洞保护
- ✅ 复杂视频时序一致性新增 `TemporalCoordinator`，支持丢检容忍、大位移重检与确认帧控制
- ✅ 新时序参数已正式下沉到配置层、AI 参数构建层与高级参数面板，支持直接调参
- ✅ 丢检容忍次数与位移确认帧数的上限策略已在 UI、配置与偏好校验层统一为 `30`
- ✅ 新增复杂掩码、复杂视频时序跟踪、批处理冷启动等核心回归测试，稳定性进一步提升

### v0.7.20（2026-03-31）

- ✅ README 改为围绕当前可用能力、真实命令和现有文档入口组织，移除了容易过期的项目结构目录树
- ✅ `src/app` 标准布局已经落地，`.\scripts\vwr.ps1 setup` 会自动执行 editable install，并在 Windows 权限异常时回退为本地 `.pth` 桥接
- ✅ `setup` 新增依赖状态复用能力，环境已满足时会跳过重复下载；同时修复了 `UV_CACHE_DIR` 为空时导致的安装失败
- ✅ 新增 `yolo11x-watermark-corzent` 模型支持，包含自动下载、SHA256 校验，以及失败时回退到默认 `yolo11x-watermark`
- ✅ 导入文件对话框默认统一显示“图片 + 视频”联合过滤器，单文件与批处理处理中的状态文案会区分“图片/视频”
- ✅ 批处理支持导出 JSON 清单，便于回溯队列状态、失败原因和处理参数
- ✅ 视频处理模块完成拆分收口，测试目录已按 `unit / integration / e2e / future` 主分层整理

---

## 🎯 功能特性

### AI 检测与修复

- 支持 `YOLOv11x-Watermark` 专用模型，适合常见文字、Logo、平台角标等水印检测
- 支持 `yolo11x-watermark-corzent` 微调模型，用于对默认模型做效果对比或特定素材增强
- 支持 `yolo11s` 轻量模型与自定义模型路径
- 支持自动下载缺失模型，下载后会进行文件完整性校验
- 针对检测框到修复掩码的转换，提供 padding、腐蚀、膨胀、闭运算等参数微调

### 图片 / 视频工作流

- 图片格式：`JPG`、`JPEG`、`PNG`、`BMP`
- 视频格式：`MP4`、`AVI`、`MKV`、`MOV`
- 支持自动检测、手动框选、多区域修复
- 支持单进程、多进程分块、流水线等视频处理策略
- 支持保留视频原始音频，并在 FFmpeg 不可用时走保守降级路径

### 批量处理与可视化反馈

- 批量队列支持并发处理，当前配置层限制为 `1-8` 个并发文件
- 导入入口默认统一展示“支持的文件（图片 + 视频）”
- 处理中状态会按媒体类型展示“正在处理图片 / 视频”
- 支持详细日志、阶段进度和批处理清单导出
- 支持 Light / Dark 双主题和处理前后预览

### 工程与运维体验

- 统一使用 `.\scripts\vwr.ps1` 交互式菜单管理环境初始化、启动、测试、质量检查、构建与清理
- `setup` 会优先复用已满足的依赖状态，减少重复下载
- 在部分 Windows 环境下，程序会先预加载 `torch` 再导入 `PyQt6`，降低 `WinError 1114` 风险
- 当前仓库已适配 `src/app` editable 开发流，便于调试、测试和打包复用同一导入路径

---

## 🚀 快速开始

### Windows（推荐）

```powershell
# 1. 克隆项目
git clone https://github.com/Izumi0527/video_watermark_remover.git
cd video_watermark_remover

# 2. 运行交互式脚本
.\scripts\vwr.ps1
```

启动后请在菜单中按顺序选择：

1. `环境初始化`
2. `启动程序`

如需国内镜像、CPU 版 PyTorch 或开发依赖，脚本会在“环境初始化”过程中继续询问。

### Linux / macOS（手动路径）

当前仓库只提供 Windows PowerShell 统一脚本。若在 Linux / macOS 使用，可手动执行：

```bash
uv venv --python 3.12.10
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e .
python main.py
```

---

## 📦 安装与运行

### `setup` 会做什么

- 创建或复用 `.venv`
- 安装运行依赖，或在 `-Dev` 下安装开发依赖
- 自动将当前项目安装为 editable
- 验证 `app` / `app.entrypoints` 可导入
- 在依赖状态未变化时跳过重复安装
- 若 Windows 临时构建目录触发 `build_editable` / `egg-info` 权限异常，则自动回退为本地 `.pth` 桥接

### 常用菜单项

- `环境初始化`：创建或修复 `.venv`，安装运行/开发依赖
- `启动程序`：检查环境后启动应用
- `代码质量检查`：执行格式、风格、类型与安全检查
- `运行测试`：运行 `unit / integration / all / audio / preferences / e2e / quality`
- `覆盖率分析`：生成覆盖率报告
- `性能测试`：生成性能报告
- `打包构建`：执行 PyInstaller 打包
- `清理缓存与临时文件`：支持 `basic / temp / all / deep`

### 配置文件位置

程序运行时会优先使用用户配置目录中的 `config.ini`。如需确认实际路径，可执行：

```powershell
python -c "from app.config.config_manager import ConfigManager; print(ConfigManager.get_config_path())"
```

如需快速生成配置，可直接运行 `.\scripts\vwr.ps1`，然后在菜单中选择“启动程序”，并开启自动修复。

---

## 📖 使用说明

### 单文件处理

1. 启动应用并选择图片或视频文件
2. 选择自动检测或手动框选模式
3. 按需调整检测阈值、修复方式、GPU 选项和输出质量
4. 开始处理并在预览区查看过程与结果
5. 导出处理后的文件

### 批量处理

1. 从同一个导入入口批量选择图片 / 视频文件
2. 设置并发数、失败重试和输出参数
3. 启动批处理并观察整体进度、当前文件状态和日志
4. 需要追溯时导出批处理清单（JSON）

### 参数建议

- 文字水印：`conf_threshold` 可从 `0.25-0.35` 起调，修复方法优先 `TELEA`
- Logo / 角标：优先默认 `yolo11x-watermark`，必要时切换 `corzent` 对比
- 低配机器：可尝试 `yolo11s + batch_size=1`
- 边界偏大或偏小：优先调 `mask_padding_px`、`mask_padding_ratio`、`mask_close_kernel`

---

## 🤖 模型与配置

### 当前支持的模型

- `yolo11x-watermark`
  - 默认推荐模型，适合常规生产场景
- `yolo11x-watermark-corzent`
  - 可自动下载，带 SHA256 校验；若不可用，程序会自动回退到默认模型
- `yolo11s`
  - 轻量通用模型，适合 CPU 或快速验证
- `custom`
  - 使用自定义 `.pt` 模型文件

### 配置示例

```ini
[YOLO]
model_type = yolo11x-watermark
auto_download_model = yes
conf_threshold = 0.25
iou_threshold = 0.45
batch_size = 8
```

更完整的模型说明与手动下载方式可查看 [models/README.md](models/README.md)。

---

## 🧪 测试与质量

当前测试体系已按主分层整理，避免 README 挂着很快过期的文件数量统计：

- `tests/unit/`：单元测试，覆盖轻量模块、导入边界和回归点
- `tests/integration/`：集成测试，覆盖 AI / 视频 / UI / 历史兼容场景
- `tests/e2e/ps1/`：PowerShell 端到端脚本
- `tests/future/unit/`：暂挂或未来阶段测试，不纳入当前默认门禁

推荐命令：

```powershell
.\scripts\vwr.ps1 setup -Dev
.\scripts\vwr.ps1 test unit -Quick
.\scripts\vwr.ps1 test integration -Quick
.\scripts\vwr.ps1 quality
```

如果你更关心当前测试约定而不是具体命令细节，请直接看 [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md)。

---

## 🎉 版本历史

### v0.7.23（2026-04-04）

- 新增 `MaskRefiner` 以提升复杂图片掩码质量
- 新增 `TemporalCoordinator` 以提升复杂视频时序一致性
- 高级参数面板已支持时序跟踪核心参数直接配置
- 统一时序参数在 UI、配置与偏好层的上限与校验策略
- 补齐复杂掩码、动态跟踪、批处理冷启动等核心回归测试

### v0.7.20（2026-03-31）

- 统一 README、程序可见版本和包元数据
- 完成 `src/app` 布局后的运行 / 测试 / editable 安装收敛
- `setup` 支持依赖状态跳过，并修复空 `UV_CACHE_DIR` 场景
- 新增 `yolo11x-watermark-corzent` 自动下载、SHA256 校验与回退逻辑
- 导入过滤器统一为图片 + 视频，处理中状态按媒体类型分流
- 批处理支持导出 JSON 清单，测试目录完成主分层整理

### v0.5.0（2025-12-07）

- Light / Dark 主题与界面细节优化
- 统一使用 Python 3.12.10 与 `uv`
- 文档与主窗口交互完成一轮重整

---

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request。提交前建议至少执行：

```powershell
.\scripts\vwr.ps1 setup -Dev
.\scripts\vwr.ps1 quality
.\scripts\vwr.ps1 test unit -Quick
```

如需定位具体开发约定、脚本行为或测试入口，请优先查看下方文档索引。

---

## 📚 文档索引

- [scripts/README.md](scripts/README.md) - `vwr.ps1` 统一脚本入口说明
- [models/README.md](models/README.md) - YOLO 模型说明、下载方式与配置建议
- [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md) - 当前测试分层与推荐执行方式
- [docs/yolo_model_upgrade.md](docs/yolo_model_upgrade.md) - 模型升级相关记录
- [docs/parameters_analysis.md](docs/parameters_analysis.md) - 参数与处理策略分析
- [docs/agents/README.md](docs/agents/README.md) - 项目专属子代理与调度说明
- [docs/complete-technical-documentation.md](docs/complete-technical-documentation.md) - 历史归档技术文档（部分内容仍基于 v0.5.0）

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

## 🙏 致谢

核心依赖包括 `PyQt6`、`OpenCV`、`PyTorch`、`Ultralytics`、`FFmpeg`、`uv`，也感谢 `pytest`、`Black`、`Flake8`、`MyPy`、`Bandit` 等工具为工程质量提供支持。

---

<div align="center">

**智能视频水印去除工具** - 让图片与视频处理流程更稳定、更高效、更可追溯

如有问题或建议，欢迎提交 [Issue](https://github.com/Izumi0527/video_watermark_remover/issues) 或 [Pull Request](https://github.com/Izumi0527/video_watermark_remover/pulls)

</div>
