# 智能视频水印去除工具 🎬

<div align="center">

**基于深度学习的智能视频水印检测与去除工具**

[![Python](https://img.shields.io/badge/Python-3.12.10-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6.0+-green.svg)](https://www.qt.io/qt-for-python)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v0.5.0-orange.svg)](https://github.com/yourusername/video_watermark_remover/releases)

**v0.5.0** | 更新日期: 2025-12-07

[快速开始](#快速开始) • [功能特性](#功能特性) • [安装部署](#安装部署) • [使用指南](#使用指南) • [完整文档](docs/complete-technical-documentation.md)

</div>

---

## 📌 项目简介

智能视频水印去除工具是一个强大的AI驱动应用程序，专为图片和视频文件的水印智能检测与高质量去除而设计。基于YOLOv11x深度学习模型和OpenCV图像处理技术，提供了直观的图形界面和专业级的处理效果。

### ✨ 核心亮点

- 🤖 **AI智能检测** - YOLOv11x-Watermark专用模型，检测准确率>99%
- ⚡ **GPU加速处理** - 支持CUDA加速，大幅提升处理速度
- 🎨 **现代化UI** - 基于PyQt6的专业界面，Light/Dark双主题支持
- 📦 **批量处理** - 智能队列管理，支持多文件并发处理
- 🎵 **音频保留** - 完整保留视频原始音频轨道
- 🖱️ **手动精选** - 支持鼠标框选，像素级精确控制

---

## 🚀 快速开始

### Windows平台（推荐）

```powershell
# 1. 克隆项目
git clone https://github.com/yourusername/video_watermark_remover.git
cd video_watermark_remover

# 2. 初始化环境（首次运行）
#   - 如需更快安装（CPU 版 PyTorch），可加：-TorchBackend cpu
#   - 如需使用镜像（解决下载慢），可加：-DefaultIndex "https://pypi.tuna.tsinghua.edu.cn/simple"
#     或设置环境变量：$env:UV_DEFAULT_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"
#   - 如需开发依赖（pytest/black 等），可加：-Dev
.\scripts\vwr.ps1 setup

# 3. 启动应用
.\scripts\vwr.ps1 run
```

> 说明：当前仓库仅提供 Windows PowerShell 脚本（`.\scripts\vwr.ps1`）。如在 Linux/macOS 使用，请按“手动安装”章节自行创建虚拟环境并运行 `python main.py`。

**首次启动**将自动完成：
- ✅ 使用uv创建Python 3.12.10虚拟环境
- ✅ 使用uv安装所有依赖包
- ✅ YOLOv11x模型自动下载
- ✅ 环境配置检查

---

## 🎯 功能特性

### 水印检测

| 检测方式 | 说明 | 推荐场景 |
|---------|------|---------|
| **YOLO深度学习** | 基于YOLOv11x-Watermark专用模型 | 通用水印、Logo、文字 |
| **OpenCV算法** | Canny边缘检测 + 色彩分析 + 形态学优化 | 简单水印、半透明效果 |
| **手动选择** | 鼠标拖拽框选，支持多区域 | 精确控制、特殊位置 |

### 水印修复

- **小面积水印** (<5%): 自定义插值算法
- **中等面积** (5-15%): TELEA快速行进法
- **大面积水印** (≥15%): Navier-Stokes方法
- **GPU加速**: CUDA深度学习修复（可选）

### 文件支持

- **图片格式**: JPG, JPEG, PNG, BMP
- **视频格式**: MP4, AVI, MKV, MOV
- **批量处理**: 多文件队列，并发处理（1-4个文件）

### 界面特性

- **Light主题**（默认）: 柔和蓝灰绿配色，舒适护眼
- **Dark主题**: 经典深色配色，夜间模式
- **实时预览**: 处理前后对比，支持缩放平移
- **详细日志**: 多维度进度显示，完整处理记录

---

## 💻 系统要求

| 组件 | 要求 | 说明 |
|------|------|------|
| **操作系统** | Windows 10/11, Linux, macOS | Windows为主要支持平台 |
| **Python** | 3.12.10 | 推荐稳定版本 |
| **uv** | 最新版 | Python包管理和虚拟环境工具 |
| **CPU** | 多核处理器 | 推荐4核及以上 |
| **内存** | 8GB+ RAM | 推荐16GB |
| **硬盘** | 2GB+ 可用空间 | 含AI模型文件 |
| **GPU**（可选）| NVIDIA with CUDA 11.8+ | 用于加速处理 |
| **FFmpeg** | 最新稳定版 | 必需，用于音频处理 |

---

## 📦 安装部署

### 方式一：自动化脚本（推荐）⭐

```powershell
.\scripts\vwr.ps1 setup   # 首次运行（创建 .venv + 安装依赖）
.\scripts\vwr.ps1 run     # 启动应用（带环境检查）
```

> 说明：脚本仅支持 Windows PowerShell；Linux/macOS 请参考“手动安装”。

### 方式二：手动安装

```bash
# 1. 安装uv（如果尚未安装）
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 使用uv创建Python 3.12.10虚拟环境
uv venv --python 3.12.10

# 3. 激活虚拟环境
# Windows: .\.venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 4. 使用uv安装依赖
uv pip install -r requirements.txt

# 5. 运行程序
uv run python main.py
```

### 开发环境配置

```powershell
# 使用 vwr 脚本安装开发依赖（推荐）
.\scripts\vwr.ps1 setup -Dev

# 运行代码质量检查
.\scripts\vwr.ps1 quality

# 运行测试
.\scripts\vwr.ps1 test unit -Quick
```

---

## 📖 使用指南

### 单文件处理流程

1. **启动应用** → 点击"📂 选择文件"
2. **选择模式** → 自动检测 或 手动选择
3. **调整参数**（可选）→ 检测敏感度、修复方法、输出质量
4. **开始处理** → 点击"✨ 开始处理"
5. **查看结果** → 实时预览、导出文件

### 批量处理流程

1. **选择多个文件** → Ctrl+点击多选
2. **配置参数** → 统一处理参数、并发数量
3. **开始批处理** → 监控队列进度
4. **查看统计** → 成功/失败数量、详细日志

### 高级技巧

**参数优化建议**:
- 文字水印: 检测敏感度 0.6-0.8, 修复方法 TELEA
- Logo水印: 检测敏感度 0.5-0.7, 修复方法 自动
- 大面积水印: 检测敏感度 0.4-0.6, 修复方法 Navier-Stokes

---

## 📁 项目结构

```
video_watermark_remover/
├── app/                    # 应用核心代码 (11,949行)
│   ├── core/              # 核心功能模块
│   │   ├── ai/            # AI检测与修复
│   │   ├── audio/         # 音频处理
│   │   └── video/         # 视频处理
│   ├── ui/                # 用户界面
│   ├── config/            # 配置管理
│   └── utils/             # 工具函数
├── tests/                 # 测试代码 (5,508行, 29个文件)
├── scripts/               # 自动化脚本（统一入口：vwr.ps1）
├── docs/                  # 文档
├── models/                # AI模型
├── logs/                  # 运行日志
├── config.ini.example     # 配置模板（复制到用户配置目录后生效）
└── main.py                # 程序入口
```

> 说明：应用运行时会在“用户配置目录”自动生成 `config.ini`（默认不纳入版本控制）。  
> 如需确认路径，可运行：`python -c "from app.config.config_manager import ConfigManager; print(ConfigManager.get_config_path())"`

**代码统计**: ~28,000+ 行代码，76个Python文件，79.7%代码规范率

---

## 🧪 测试与质量

### 测试覆盖

- **测试文件**: 29个（5,508行代码）
- **测试类型**: 单元测试 + 集成测试 + UI测试 + 性能测试
- **覆盖率**: ≥60%（核心模块）

### 代码质量工具

- **Black** - 代码格式化（行长100）
- **Flake8** - 代码风格检查
- **MyPy** - 类型注解检查
- **Bandit** - 安全漏洞扫描
- **pytest-cov** - 覆盖率分析

---

## 🎉 版本历史

### v0.5.0 (当前版本 - 2025-12-07)

**重大更新**:
- 🎨 Light主题设为默认，全新柔和蓝灰绿配色
- ✅ 优化文字可读性和GroupBox标题显示
- ✅ 统一日志面板颜色，透明背景自适应
- 🔧 统一使用Python 3.12和uv包管理工具

### v0.4.0 (2025-11-22)

- ✅ 集成YOLOv11x-Watermark专用检测模型
- ✅ GPU加速深度学习修复
- ✅ 多进程分块和流水线处理
- ✅ 完善异常处理体系（13种）

[查看完整版本历史](docs/complete-technical-documentation.md#版本历史)

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！在提交代码前，请确保：

1. 代码遵循PEP8规范
2. 每个模块不超过300行
3. 添加适当的单元测试（覆盖率≥60%）
4. 运行代码质量检查并通过

```powershell
# 提交前检查
.\scripts\vwr.ps1 quality
.\scripts\vwr.ps1 test unit -Quick
```

---

## 📚 相关文档

- [📘 完整技术文档](docs/complete-technical-documentation.md) - 详细的功能说明和技术架构
- [🏗️ 架构设计](docs/architecture.md) - 系统架构和设计模式
- [🔌 API文档](docs/api.md) - 接口说明和使用示例
- [🧪 测试文档](docs/testing.md) - 测试策略和覆盖率
- [🛠️ 开发指南](docs/development.md) - 开发环境配置和规范

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

## 🙏 致谢

**核心依赖**: PyQt6, OpenCV, PyTorch, Ultralytics, FFmpeg, uv

**开发工具**: pytest, Black, Flake8, MyPy, Bandit

---

<div align="center">

**智能视频水印去除工具** - 让视频内容更纯净 ✨

*如有问题或建议，欢迎提交 [Issue](https://github.com/yourusername/video_watermark_remover/issues) 或 [Pull Request](https://github.com/yourusername/video_watermark_remover/pulls)*

⭐ **如果这个项目对你有帮助，请给我们一个Star！** ⭐

</div>
