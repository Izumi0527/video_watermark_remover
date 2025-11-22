# 智能视频水印去除工具 🎬

> **版本**: v0.3.0 | **更新日期**: 2025-11-22 | **Python**: 3.8-3.11 | **代码量**: ~28,000+ 行

一个基于深度学习和传统图像处理技术的智能视频水印去除工具，支持图片和视频文件的水印智能检测与高质量去除。

## ✨ 主要功能

### 🔥 核心功能
- **🤖 YOLO深度学习检测**：基于YOLOv11x-Watermark专用模型的水印区域智能检测（>99%准确率）⭐
- **🎨 传统算法检测**：基于OpenCV图像处理的水印区域自动检测
- **⚡ GPU加速修复**：深度学习图像修复，支持CUDA加速（Phase 5）
- **🛠️ 多算法修复**：OpenCV修复算法（TELEA、Navier-Stokes）智能填充
- **🖱️ 手动精确选择**：支持鼠标拖拽框选水印区域，提供像素级精确控制
- **📦 批量队列处理**：支持多文件批量处理，智能队列管理
- **👁️ 实时预览对比**：处理过程中的实时预览和原图对比
- **📊 详细进度跟踪**：多维度进度显示（总体进度、帧进度、处理速度）

### 🎨 界面特性
- **现代化UI**：基于PyQt6的现代化用户界面
- **深色/浅色主题**：支持主题切换，适应不同使用环境
- **用户偏好设置**：自动保存用户设置和最近使用文件
- **多面板设计**：文件面板、预览面板、控制面板、日志面板分工明确

### 🚀 高级功能
- **多格式支持**：支持MP4、AVI、MKV、MOV、JPG、PNG、BMP等主流格式
- **音频完整保留**：集成FFmpeg，处理视频时自动提取并合并音频轨道
- **高级参数控制**：检测敏感度、修复方法、输出质量、GPU加速等参数可调
- **多模式处理**：单进程、多进程分块、流水线三种处理模式可选
- **智能设备适配**：自动检测GPU（CUDA）可用性，智能切换CPU/GPU处理
- **用户偏好记忆**：自动保存最近文件、窗口大小、参数设置等用户偏好

## 🛠️ 技术架构

### 核心技术栈
- **GUI框架**：PyQt6 >= 6.6.0
- **图像处理**：OpenCV >= 4.8.0
- **数值计算**：NumPy >= 1.25.0, Pillow >= 10.0.0
- **深度学习**：PyTorch >= 2.6.0, torchvision >= 0.21.0
- **YOLO检测**：Ultralytics >= 8.3.0 (YOLOv11x-Watermark专用模型)
- **视频处理**：FFmpeg (外部依赖)
- **测试框架**：pytest >= 7.0.0, pytest-qt >= 4.2.0
- **日志系统**：Python logging + 文件输出

### 架构设计
- **模块化架构**：单一职责原则，各功能模块独立（11,949行应用代码）
- **多线程处理**：GUI与处理逻辑完全分离，避免界面冻结
- **观察者模式**：PyQt6信号槽机制，实现组件解耦
- **策略模式**：视频处理支持单进程/多进程/流水线三种策略
- **配置管理**：集中化配置管理（INI + JSON），支持用户自定义
- **异常体系**：完善的异常层次结构（13种自定义异常类型）
- **插件化设计**：检测器和修复器可独立扩展

## 📦 安装使用

### 环境要求
- Python 3.8-3.11 (推荐 3.10/3.11)
- Windows 10/11 (推荐) / Linux / macOS
- FFmpeg (必需，用于音频处理)
- CUDA 11.8+ (可选，用于GPU加速)
- 磁盘空间：约2GB（含模型文件）
- 内存：建议8GB+（视频处理）

### 快速开始

**方式一：使用自动化脚本（推荐）**
```powershell
# 1. 环境初始化（仅首次运行）
.\scripts\setup.ps1

# 2. 启动应用
.\scripts\start.ps1
```

**方式二：手动安装**
```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行程序
python main.py
```

### 开发环境配置
```bash
# 安装开发依赖（包括测试、代码质量工具）
pip install -r requirements-dev.txt

# 安装 pre-commit hooks
pre-commit install

# 运行代码质量检查
.\scripts\check-quality.ps1

# 运行测试
.\scripts\test.ps1
```

## 🎯 使用指南

### 基本操作流程
1. **选择文件**：点击"选择文件"按钮或拖拽文件到界面
2. **选择模式**：
   - 自动检测：AI自动识别水印区域
   - 手动选择：用户手动框选水印区域
3. **调整参数**：在高级参数面板中调整检测敏感度等参数
4. **开始处理**：点击"开始处理"按钮开始水印去除
5. **查看结果**：在预览面板查看处理效果

### 批量处理
1. 切换到"批量处理"标签页
2. 点击"添加文件"批量添加待处理文件
3. 设置处理参数（对所有文件生效）
4. 点击"开始批量处理"
5. 在进度面板监控处理进度

### 高级设置
- **检测敏感度**：调整水印检测的敏感程度
- **修复方法**：选择TELEA或Navier-Stokes算法
- **输出质量**：设置输出文件的质量等级
- **并发数量**：控制批量处理时的并发文件数

## 📁 项目结构

```
video_watermark_remover/
├── app/                          # 主应用代码 (11,949行)
│   ├── core/                     # 核心功能模块 (5,245行)
│   │   ├── ai/                   # AI处理模块 (1,389行)
│   │   │   ├── ai_handler.py     # AI处理协调器 (376行)
│   │   │   ├── yolo_detector.py  # YOLOv11x水印检测 (277行)
│   │   │   ├── image_inpainter.py # OpenCV图像修复 (274行)
│   │   │   ├── dl_inpainter.py   # GPU深度学习修复 (408行)
│   │   │   └── __init__.py
│   │   ├── audio/                # 音频处理模块 (1,850行)
│   │   │   ├── ffmpeg_audio_processor.py  # FFmpeg音频处理主类 (326行)
│   │   │   ├── audio_extractor.py         # 音频提取 (267行)
│   │   │   ├── audio_merger.py            # 音频合并 (286行)
│   │   │   ├── video_info_extractor.py    # 视频信息提取 (249行)
│   │   │   ├── ffmpeg_detector.py         # FFmpeg检测 (237行)
│   │   │   └── __init__.py
│   │   ├── video/                # 视频处理模块 (1,609行)
│   │   │   ├── video_processor.py # 视频处理核心 (1609行 - 多进程+流水线)
│   │   │   └── __init__.py
│   │   ├── exceptions.py         # 异常体系 (453行 - 13种异常类型)
│   │   └── __init__.py
│   │
│   ├── ui/                       # 用户界面 (3,843行)
│   │   ├── components/           # UI组件 (1,559行)
│   │   │   ├── file_panel.py            # 文件选择面板 (122行)
│   │   │   ├── control_panel.py         # 控制面板 (254行)
│   │   │   ├── preview_panel.py         # 预览面板 (486行)
│   │   │   ├── detailed_progress_widget.py  # 详细进度显示 (428行)
│   │   │   ├── log_panel.py             # 日志面板 (217行)
│   │   │   └── __init__.py
│   │   ├── widgets/              # 自定义控件 (1,656行)
│   │   │   ├── advanced/         # 高级参数组件 (619行)
│   │   │   │   ├── advanced_parameters_widget.py   (320行)
│   │   │   │   ├── advanced_parameters_tabs.py     (283行)
│   │   │   │   └── __init__.py
│   │   │   ├── batch/            # 批处理组件 (1,037行)
│   │   │   │   ├── batch_processing_widget.py      (281行)
│   │   │   │   ├── batch_processor_thread.py       (347行)
│   │   │   │   ├── batch_file_manager.py           (222行)
│   │   │   │   ├── batch_ui_components.py          (282行)
│   │   │   │   └── __init__.py
│   │   │   ├── image_selector_widget.py      (136行)
│   │   │   ├── selectable_image_label.py     (290行)
│   │   │   ├── selection_handlers.py         (182行)
│   │   │   ├── coordinate_converter.py       (157行)
│   │   │   └── __init__.py
│   │   ├── main_window.py        # 主窗口 (314行)
│   │   ├── signal_handler.py     # 信号处理器 (556行)
│   │   ├── utils/                # UI工具
│   │   │   ├── ai_params_builder.py  # AI参数构建器 (320行)
│   │   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── config/                   # 配置管理 (1,774行)
│   │   ├── config_manager.py     # INI配置管理 (224行)
│   │   ├── preferences.py        # 用户偏好设置 (748行)
│   │   ├── styles.py             # 主题样式管理 (796行)
│   │   └── __init__.py
│   │
│   └── utils/                    # 工具函数 (148行)
│       ├── logger_setup.py       # 日志配置 (78行)
│       ├── utils.py              # 工具函数 (70行)
│       └── __init__.py
│
├── tests/                        # 测试代码 (5,508行，29个测试文件)
│   ├── unit/                     # 单元测试
│   │   ├── test_config_manager.py
│   │   ├── test_exceptions.py    (287行)
│   │   ├── test_image_inpainter.py (256行)
│   │   └── __init__.py
│   ├── integration/              # 集成测试
│   │   └── __init__.py
│   ├── test_video_processor.py   (391行)
│   ├── test_yolo_detector.py
│   ├── test_yolo_pipeline.py     (230行)
│   ├── test_dl_inpainter_gpu.py
│   ├── test_aihandler_gpu_integration.py
│   ├── test_mvp.py               (217行)
│   ├── test_batch_processing.py
│   ├── test_pipeline_video.py    (232行)
│   ├── test_multiprocess_video.py (246行)
│   ├── ui_component_tests.py     (272行)
│   ├── ai_module_tests.py        (218行)
│   ├── ai_processing_tests.py    (266行)
│   ├── test_utilities.py         (206行)
│   ├── conftest.py               # pytest配置
│   └── test_data/                # 测试数据
│       ├── configs/
│       └── models/
│
├── scripts/                      # 自动化脚本 (20个脚本)
│   ├── PowerShell脚本 (Windows)
│   │   ├── setup.ps1             # 环境初始化
│   │   ├── start.ps1             # 完整启动脚本 (24KB)
│   │   ├── run.ps1               # 快速启动
│   │   ├── build.ps1             # 发布构建
│   │   ├── test.ps1              # 参数化测试 (24KB)
│   │   ├── test-all.ps1          # 完整测试套件 (20KB)
│   │   ├── test-coverage.ps1     # 覆盖率分析 (15KB)
│   │   ├── test-performance.ps1  # 性能测试 (22KB)
│   │   ├── check-quality.ps1     # 代码质量检查 (13KB)
│   │   ├── clean-cache.ps1       # 缓存清理
│   │   └── ci-test.ps1           # CI/CD测试 (18KB)
│   ├── Bash脚本 (Linux/macOS)
│   │   ├── setup.sh
│   │   ├── run.sh
│   │   ├── build.sh
│   │   └── test.sh
│   ├── Python脚本
│   │   └── check_code_quality.py # 代码行数检查
│   └── README.md                 # 脚本使用说明 (794行)
│
├── docs/                         # 文档 (8,591行，16个文档)
│   ├── api.md                    # API接口文档 (1004行)
│   ├── architecture.md           # 架构设计文档 (767行)
│   ├── development.md            # 开发指南 (801行)
│   ├── testing.md                # 测试文档 (718行)
│   ├── phase3_complete_summary.md        (965行)
│   ├── phase4_stage1_complete_report.md  (799行)
│   ├── phase6_yolo_detection.md          (474行)
│   ├── comprehensive_analysis_and_optimization_2025.md (105行)
│   ├── frontend_ui_analysis.md           (357行)
│   ├── video_upload_issue_analysis.md    (431行)
│   ├── video_upload_fix_completed.md     (312行)
│   ├── videowriter_codec_fix.md          (391行)
│   ├── Windows使用指南.md        (144行)
│   └── MVP使用指南.md            (286行)
│
├── models/                       # 预训练模型
│   ├── yolo11x-watermark.pt      # YOLOv11x专用水印检测模型 (114MB)
│   └── README.md                 # 模型说明文档
│
├── logs/                         # 运行日志目录
├── config.ini                    # 应用配置文件
├── config.ini.example            # 配置文件示例
├── pyproject.toml                # 项目元数据和工具配置
├── setup.py                      # 安装脚本
├── main.py                       # 应用入口
├── requirements.txt              # 生产依赖
├── requirements-dev.txt          # 开发依赖
├── README.md                     # 项目说明
├── MANIFEST.in                   # 打包清单
└── .pre-commit-config.yaml       # 代码提交前检查
```

### 📊 项目统计

| 维度 | 数据 |
|------|------|
| **总代码量** | ~28,000+ 行 |
| **应用代码** | 11,949 行 (47个文件) |
| **测试代码** | 5,508 行 (29个测试文件) |
| **文档** | 8,591 行 (16个文档) |
| **脚本** | ~2,000 行 (20个脚本) |
| **Python文件** | 76 个 (应用47 + 测试29) |
| **代码规范达标率** | 79.7% (≤300行/文件) |

## 🧪 开发测试

### 运行测试

**使用自动化脚本（推荐）**
```powershell
# 运行所有测试
.\scripts\test.ps1

# 仅运行单元测试
.\scripts\test.ps1 unit

# 运行测试并生成覆盖率报告
.\scripts\test.ps1 -Coverage

# 运行代码质量检查
.\scripts\test.ps1 quality

# 快速测试（跳过耗时检查）
.\scripts\test.ps1 -Quick
```

**手动运行测试**
```bash
# 运行所有单元测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/unit/test_config_manager.py -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html

# 运行代码质量检查
black app main.py --check
flake8 app main.py
mypy app main.py
```

### 测试覆盖情况

当前项目建立了完善的测试体系：

**测试统计**:
- 📊 **测试文件**: 29个测试文件
- 📊 **测试代码**: 5,508行
- 📊 **测试类型**: 单元测试 + 集成测试 + UI测试 + 性能测试

**主要测试模块**:
- ✅ **单元测试**: ConfigManager, ImageInpainter, Exceptions 等
- ✅ **AI模块测试**: YOLO检测器、GPU修复器、AI处理器集成测试
- ✅ **视频处理测试**: 单进程、多进程、流水线处理测试
- ✅ **UI组件测试**: 界面组件、批处理、预览等
- ✅ **集成测试**: 完整处理流程、音频处理、MVP功能测试

**代码质量工具**:
- ✅ **Black** - 代码格式化 (行长100)
- ✅ **Flake8** - 代码风格检查
- ✅ **MyPy** - 类型注解检查
- ✅ **Bandit** - 安全漏洞检查
- ✅ **Pre-commit hooks** - 提交前自动检查
- ✅ **pytest-cov** - 测试覆盖率分析

**测试覆盖率目标**: ≥60% (核心模块)

### 代码质量检查

```powershell
# 运行所有质量检查
.\scripts\check-quality.ps1

# 自动修复格式问题
.\scripts\check-quality.ps1 -Fix

# 快速检查（跳过类型检查）
.\scripts\check-quality.ps1 -Quick

# 仅检查特定类型
.\scripts\check-quality.ps1 -Check format   # 代码格式
.\scripts\check-quality.ps1 -Check style    # 代码风格
.\scripts\check-quality.ps1 -Check type     # 类型注解
```

## 🔧 配置说明

### 主配置文件 (config.ini)
```ini
[Paths]
ffmpeg_path = ffmpeg
default_model_dir = ./models

[Processing]
default_detection_sensitivity = 0.5
default_inpainting_method = auto
preserve_audio = yes
output_quality = high
gpu_acceleration = auto

[Logging]
log_level = INFO
log_file_path = logs/app.log
console_logging = yes

[UI]
default_theme = dark
default_window_width = 1400
default_window_height = 900

[Advanced]
max_threads = -1
cache_size_mb = 512
enable_cache = yes
```

### 用户偏好设置
用户偏好设置自动保存在用户目录：
- Windows: `%USERPROFILE%\.video_watermark_remover\`
- Linux/macOS: `~/.config/video_watermark_remover/`

## 🎉 版本历史

### v0.3.0 (当前版本 - 2025-11-22)

**核心功能升级**:
- ✅ **Phase 6+**: 集成YOLOv11x-Watermark专用水印检测模型（>99%准确率）
- ✅ **Phase 5**: GPU加速深度学习图像修复 (dl_inpainter)
- ✅ **Phase 4**: 多进程分块处理和流水线处理架构

**代码质量优化**:
- ✅ 修复AIHandler接口问题和PyQt6 API兼容性
- ✅ 重构代码架构，提高可维护性
- ✅ 新增AI参数构建器工具类
- ✅ 完善异常处理体系（13种自定义异常）
- ✅ 优化音频处理器模块化设计

**功能改进**:
- ✅ 优化批量处理功能和UI组件
- ✅ 完善用户偏好设置系统
- ✅ 添加深色/浅色主题支持
- ✅ 修复视频处理完成后UI不更新问题
- ✅ 修复VideoWriter编解码器兼容性问题

**开发工具**:
- ✅ 完善20个自动化脚本（PowerShell + Bash）
- ✅ 建立完整测试体系（29个测试文件，5,508行测试代码）
- ✅ 集成代码质量检查工具链
- ✅ 添加性能测试和覆盖率分析脚本

**文档完善**:
- ✅ 新增16个技术文档（8,591行）
- ✅ 项目优化分析和修复文档
- ✅ YOLO检测模块专项文档
- ✅ 前端UI分析文档

### v0.2.0 (2024-Q4)
- ✅ 实现基础AI水印检测和去除
- ✅ 添加批量处理功能
- ✅ 集成FFmpeg音频处理
- ✅ 实现多线程处理架构

### v0.1.0 (2024-Q3)
- ✅ 基础GUI框架（PyQt6）
- ✅ 文件选择和预览功能
- ✅ 基础图像处理流程

## 📚 文档

完整的技术文档请参考 `docs/` 目录（共16个文档，8,591行）：

**核心文档**:
- **[架构设计文档](docs/architecture.md)** (767行) - 详细的系统架构和设计模式
- **[API 接口文档](docs/api.md)** (1004行) - 核心模块的API接口说明
- **[测试文档](docs/testing.md)** (718行) - 测试策略和测试用例说明
- **[开发指南](docs/development.md)** (801行) - 开发环境配置和代码规范

**阶段总结文档**:
- **[Phase 3 完成总结](docs/phase3_complete_summary.md)** (965行) - Phase 3交付总结
- **[Phase 4 Stage 1 报告](docs/phase4_stage1_complete_report.md)** (799行) - Phase 4第一阶段报告
- **[Phase 6 YOLO检测](docs/phase6_yolo_detection.md)** (474行) - YOLO检测模块文档

**问题分析与修复文档**:
- **[项目优化分析2025](docs/comprehensive_analysis_and_optimization_2025.md)** (105行) - 全面优化分析
- **[前端UI分析](docs/frontend_ui_analysis.md)** (357行) - 前端UI组件分析
- **[视频上传问题分析](docs/video_upload_issue_analysis.md)** (431行) - 视频上传问题诊断
- **[视频上传修复完成](docs/video_upload_fix_completed.md)** (312行) - 视频上传修复记录
- **[VideoWriter编解码修复](docs/videowriter_codec_fix.md)** (391行) - 编解码器兼容性修复

**使用指南**:
- **[Windows 使用指南](docs/Windows使用指南.md)** (144行) - Windows平台特定说明
- **[MVP 使用指南](docs/MVP使用指南.md)** (286行) - 最小可行产品使用说明

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发规范
- **代码规范**: 遵循Python PEP8代码规范
- **文件大小**: 每个模块不超过300行代码（硬性指标）
- **测试要求**: 添加适当的单元测试，覆盖率≥60%
- **提交检查**: 提交前必须运行代码质量检查 (`.\scripts\check-quality.ps1`)
- **类型注解**: 优先使用类型注解提高代码可读性
- **文档更新**: 重要功能需要更新对应文档

### 功能扩展
项目采用模块化架构，便于功能扩展：
- **检测器扩展**：在 [app/core/ai/](app/core/ai/) 目录添加新的检测算法
- **修复器扩展**：在 [app/core/ai/](app/core/ai/) 目录添加新的修复算法
- **UI组件扩展**：在 [app/ui/widgets/](app/ui/widgets/) 目录添加新的界面组件
- **处理策略扩展**：在 [app/core/video/](app/core/video/) 目录添加新的视频处理策略

### 代码架构原则
- ✅ **单一职责**: 每个模块专注于一个功能
- ✅ **开放封闭**: 对扩展开放，对修改封闭
- ✅ **依赖倒置**: 依赖抽象而非具体实现
- ✅ **接口隔离**: 使用最小化接口
- ✅ **组合优于继承**: 优先使用组合而非继承

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 🙏 致谢

感谢以下开源项目和技术：

**核心依赖**:
- [PyQt6](https://www.qt.io/qt-for-python) - 强大的跨平台GUI框架
- [OpenCV](https://opencv.org/) - 计算机视觉和图像处理库
- [PyTorch](https://pytorch.org/) - 深度学习框架
- [Ultralytics](https://github.com/ultralytics/ultralytics) - YOLOv11实现
- [NumPy](https://numpy.org/) - 高性能数值计算库
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理瑞士军刀

**开发工具**:
- [pytest](https://pytest.org/) - Python测试框架
- [Black](https://github.com/psf/black) - 代码格式化工具
- [Flake8](https://flake8.pycqa.org/) - 代码风格检查
- [MyPy](http://mypy-lang.org/) - 静态类型检查
- [Bandit](https://bandit.readthedocs.io/) - 安全漏洞检查

**特别感谢**:
- OpenCV社区提供的图像修复算法
- PyTorch团队提供的深度学习框架
- Ultralytics团队开发的YOLO系列模型

---

**智能视频水印去除工具** - 让视频内容更纯净 ✨

*最后更新: 2025-11-22 | 版本: v0.3.0*
