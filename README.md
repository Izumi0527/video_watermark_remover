# 智能视频水印去除工具

面向图片与视频的桌面工具，提供 AI 水印检测、区域修复、音频保留、批处理队列和处理结果追踪。当前版本为 `v0.7.23`，Windows 是主要支持平台。

核心技术栈：`PyQt6`、`OpenCV`、`PyTorch`、`Ultralytics YOLO`、`FFmpeg`、`uv`。

---

## 安装部署

### 1. 环境要求

- 操作系统：优先 Windows 10 / 11。
- Python：推荐 `3.12.10`，项目配置支持 `Python >= 3.8`。
- 包管理：推荐使用 `uv`。
- 外部工具：视频音频保留需要 `FFmpeg` / `ffprobe` 可用。
- GPU：可选；NVIDIA CUDA 环境可提升 YOLO 检测和深度修复速度。

### 2. Windows 菜单式安装

```powershell
git clone https://github.com/Izumi0527/video_watermark_remover.git
cd video_watermark_remover
.\scripts\vwr.ps1
```

进入菜单后，按顺序执行：

1. `环境初始化`
2. `启动程序`

环境初始化会继续询问 Python 版本、Torch 后端、镜像源和是否安装开发依赖。脚本会创建或复用 `.venv`，安装依赖，并把当前项目安装为 editable 开发模式。

### 3. 手动安装

Windows：

```powershell
uv venv --python 3.12.10
.\.venv\Scripts\activate
uv pip install -r requirements.txt
uv pip install -e .
python main.py
```

Linux / macOS：

```bash
uv venv --python 3.12.10
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e .
python main.py
```

Linux / macOS 当前没有专用脚本，主要用于手动验证。

### 4. 模型准备

默认 YOLO 模型可在首次运行时自动下载，也可以提前放入 `models/`：

- `models/yolo11x-watermark.pt`
- `models/yolo11x-watermark-corzent.pt`
- `models/big-lama.pt`

如需指定 LaMa TorchScript 权重：

```powershell
$env:VWR_LAMA_MODEL_PATH="C:/path/to/big-lama.pt"
```

更多模型来源和配置见 [models/README.md](models/README.md)。

### 5. 启动验证

```powershell
.\scripts\vwr.ps1
```

在菜单中选择 `启动程序`。如果提示缺少依赖或模型路径异常，优先回到菜单执行 `环境初始化`，并按提示开启自动修复。

### 6. 打包部署

```powershell
.\scripts\vwr.ps1
```

在菜单中选择 `打包构建`。脚本会使用 PyInstaller 构建可执行文件，并输出到 `release/` 目录。发布前建议先运行菜单中的 `代码质量检查` 和 `运行测试`。

---

## 核心能力

- 图片与视频水印检测：支持自动检测和手动框选。
- 多模型检测：支持 `yolo11x-watermark`、`yolo11x-watermark-corzent`、`yolo11s` 和自定义模型。
- 多后端修复：支持 OpenCV、legacy U-Net、LaMa TorchScript 等修复路径。
- 视频处理：支持单进程、多进程分块和流水线模式。
- 音频保留：处理视频后尽量保留原始音频轨道。
- 批处理：支持队列处理、状态追踪、失败记录和 JSON 清单导出。
- 参数面板：检测、修复、性能、输出参数集中配置。
- 工程化入口：通过 `scripts/vwr.ps1` 管理常用开发和运行任务。

---

## 常用操作

### 启动应用

```powershell
.\scripts\vwr.ps1
```

在菜单中选择 `启动程序`。

### 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit -q
```

也可以运行 `.\scripts\vwr.ps1`，在菜单中选择 `运行测试`。

### 质量检查

```powershell
.\scripts\vwr.ps1
```

在菜单中选择 `代码质量检查`。

---

## 模型与配置

模型文件放在 `models/` 目录。常用模型：

- `yolo11x-watermark.pt`：默认推荐模型。
- `yolo11x-watermark-corzent.pt`：社区微调版本，适合对比检测效果。
- `big-lama.pt`：LaMa TorchScript 修复模型。

YOLO 配置示例：

```ini
[YOLO]
model_type = yolo11x-watermark
auto_download_model = yes
conf_threshold = 0.25
iou_threshold = 0.45
batch_size = 8
```

更多模型下载和配置说明见 [models/README.md](models/README.md)。

---

## 项目结构

```text
src/app/
  entrypoints.py      # 应用启动入口
  config/             # 配置、偏好、参数快照、样式
  core/               # AI、视频、音频处理核心
  ui/                 # PyQt6 主界面、组件、批处理 UI
  utils/              # 模型下载、日志、指标、格式工具
tests/
  unit/               # 单元测试
  integration/        # 集成测试
  e2e/ps1/            # PowerShell 端到端脚本
docs/
  architecture.md     # 当前架构与代码地图
  archive/            # 归档专题文档与历史报告
```

完整架构说明见 [docs/architecture.md](docs/architecture.md)。

---

## 文档索引

- [docs/architecture.md](docs/architecture.md)：当前架构、代码地图与维护边界。
- [scripts/README.md](scripts/README.md)：`vwr.ps1` 菜单入口说明。
- [models/README.md](models/README.md)：模型说明、下载方式与配置建议。
- [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md)：测试分层与推荐执行方式。
- [docs/archive/yolo_model_upgrade.md](docs/archive/yolo_model_upgrade.md)：YOLO 模型升级记录。
- [docs/archive/parameters_analysis.md](docs/archive/parameters_analysis.md)：参数与处理策略分析。

---

## 开发提示

- 参数变更要同时检查 UI 默认值、偏好默认值、参数构建、运行时消费和批处理路径。
- 批处理相关修改要重点关注稳定 `file_id`、取消状态和清单导出。
- AI / 视频核心修改建议先跑定向单测，再视情况补集成测试。
- 文档中避免写死容易过期的文件数量、性能数据和历史目录树。

---

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

## 致谢

感谢所有使用、反馈和贡献本项目的朋友。

<div align="center">

**智能视频水印去除工具 - 让视频内容更纯净 ✨**

如有问题或建议，欢迎提交 [Issue](https://github.com/Izumi0527/video_watermark_remover/issues) 或 [Pull Request](https://github.com/Izumi0527/video_watermark_remover/pulls)

⭐ 如果这个项目对你有帮助，请给我们一个Star！ ⭐

</div>
