# 智能视频水印去除工具 🎬

一个基于AI技术的智能视频水印去除工具，支持图片和视频文件的水印检测与去除。

## ✨ 主要功能

### 🔥 核心功能
- **智能水印检测**：基于OpenCV传统图像处理方法的水印区域自动检测
- **AI图像修复**：使用多种OpenCV修复算法（TELEA、Navier-Stokes）进行智能填充
- **手动选择**：支持用户手动框选水印区域，提供精确控制
- **批量处理**：支持批量队列处理，提高工作效率
- **实时预览**：处理过程中的实时预览和进度跟踪

### 🎨 界面特性
- **现代化UI**：基于PyQt6的现代化用户界面
- **深色/浅色主题**：支持主题切换，适应不同使用环境
- **用户偏好设置**：自动保存用户设置和最近使用文件
- **多面板设计**：文件面板、预览面板、控制面板、日志面板分工明确

### 🚀 高级功能
- **多格式支持**：支持MP4、AVI、MKV、MOV、JPG、PNG、BMP等格式
- **音频保留**：集成FFmpeg，处理视频时自动保留音频轨道
- **高级参数控制**：检测敏感度、修复方法、输出质量等参数可调
- **并发处理**：支持多线程处理，提高处理速度

## 🛠️ 技术架构

### 核心技术栈
- **GUI框架**：PyQt6
- **图像处理**：OpenCV 4.12.0
- **数值计算**：NumPy 2.2.6
- **视频处理**：FFmpeg
- **日志系统**：Python logging

### 架构设计
- **模块化架构**：单一职责原则，各功能模块独立
- **多线程处理**：GUI与处理逻辑分离，避免界面冻结
- **配置管理**：集中化配置管理，支持用户自定义
- **插件化设计**：检测器和修复器可独立扩展

## 📦 安装使用

### 环境要求
- Python 3.8+ (推荐 3.12)
- Windows 10/11 (推荐) / Linux / macOS
- FFmpeg (可选，用于音频处理)

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
├── app/                          # 主应用代码
│   ├── core/                     # 核心功能模块
│   │   ├── ai/                   # AI处理模块
│   │   │   ├── ai_handler.py     # AI处理协调器
│   │   │   ├── watermark_detector.py  # 水印检测器
│   │   │   └── image_inpainter.py     # 图像修复器
│   │   ├── audio/                # 音频处理模块
│   │   └── video/                # 视频处理模块
│   ├── ui/                       # 用户界面
│   │   ├── components/           # UI组件
│   │   ├── widgets/              # 自定义控件
│   │   └── main_window.py        # 主窗口
│   ├── config/                   # 配置管理
│   └── utils/                    # 工具函数
├── tests/                        # 测试文件
├── scripts/                      # 辅助脚本
├── main.py                       # 程序入口
├── requirements.txt              # 依赖列表
└── README.md                     # 项目说明
```

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

**单元测试**:
- ✅ ConfigManager: 18个测试用例
- ✅ WatermarkDetector: 23+个测试用例
- ✅ ImageInpainter: 28+个测试用例
- 📊 总计: 69+ 测试用例

**代码质量**:
- ✅ Black 代码格式化
- ✅ Flake8 代码风格检查
- ✅ MyPy 类型检查
- ✅ Bandit 安全检查
- ✅ Pre-commit hooks 自动化检查

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
[processing]
default_detection_sensitivity = 0.5
default_inpainting_method = auto
preserve_audio = true
output_quality = high

[ui]  
theme = dark
window_width = 1400
window_height = 900

[advanced]
max_threads = -1
enable_gpu = false
cache_size_mb = 512
```

### 用户偏好设置
用户偏好设置自动保存在用户目录：
- Windows: `%USERPROFILE%\.video_watermark_remover\`
- Linux/macOS: `~/.config/video_watermark_remover/`

## 🎉 版本历史

### v0.3.0-refactored (当前版本)
- ✅ 修复AIHandler接口问题
- ✅ 重构代码架构，提高可维护性
- ✅ 优化批量处理功能
- ✅ 完善用户偏好设置
- ✅ 添加现代化主题支持

### v0.2.0
- ✅ 实现基础AI水印检测和去除
- ✅ 添加批量处理功能
- ✅ 集成FFmpeg音频处理

### v0.1.0
- ✅ 基础GUI框架
- ✅ 文件选择和预览功能

## 📚 文档

完整的技术文档请参考 `docs/` 目录：

- **[架构设计文档](docs/architecture.md)** - 详细的系统架构和设计模式
- **[API 接口文档](docs/api.md)** - 核心模块的API接口说明
- **[测试文档](docs/testing.md)** - 测试策略和测试用例说明
- **[开发指南](docs/development.md)** - 开发环境配置和代码规范
- **[Windows 使用指南](docs/Windows使用指南.md)** - Windows平台特定说明
- **[MVP 使用指南](docs/MVP使用指南.md)** - 最小可行产品使用说明

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发规范
- 遵循Python PEP8代码规范
- 每个模块不超过300行代码
- 添加适当的单元测试
- 提交前运行代码质量检查

### 功能扩展
项目采用模块化架构，便于功能扩展：
- **检测器扩展**：在`core/ai/`目录添加新的检测算法
- **修复器扩展**：在`core/ai/`目录添加新的修复算法  
- **UI组件扩展**：在`ui/widgets/`目录添加新的界面组件

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 🙏 致谢

感谢以下开源项目：
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [PyQt6](https://www.qt.io/qt-for-python) - GUI框架
- [NumPy](https://numpy.org/) - 数值计算库
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理工具

---

**智能视频水印去除工具** - 让视频内容更纯净 ✨
