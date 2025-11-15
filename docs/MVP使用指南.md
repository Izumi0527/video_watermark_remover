# 🚀 智能视频水印去除工具 - MVP版本使用指南

## 📋 版本信息
- **版本**: v0.1.0-MVP  
- **发布日期**: 2025-01-31
- **开发阶段**: 第一阶段 - MVP建立
- **功能状态**: 基础GUI + 模拟处理

## ✨ MVP版本功能特性

### 🎯 已实现功能
- ✅ **现代化GUI界面** - 基于PyQt6的专业界面设计
- ✅ **文件选择功能** - 支持图片和视频文件选择
- ✅ **图片预览功能** - 实时预览选中的图片文件
- ✅ **处理进度显示** - 带进度条的处理状态展示
- ✅ **日志记录系统** - 实时显示操作日志
- ✅ **配置管理** - 跨平台配置文件管理
- ✅ **错误处理** - 友好的错误提示和异常处理

### 🔧 系统架构
- **GUI层**: PyQt6现代化界面
- **配置层**: 基于INI的配置管理
- **日志层**: 多级别日志记录
- **工具层**: 通用工具函数集合

## 🛠️ 安装和运行

### 环境要求
```bash
Python 3.9+
PyQt6 >= 6.6.0
```

### 快速开始

#### 1. 安装依赖
```bash
# 进入项目目录
cd video_watermark_remover

# 激活虚拟环境（如果使用）
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# 安装依赖
pip install PyQt6
```

#### 2. 测试系统
```bash
# 运行MVP测试脚本
python test_mvp.py
```

预期输出：
```
🚀 智能视频水印去除工具 - MVP功能测试
==================================================
🔍 测试模块导入...
✅ ConfigManager 导入成功
✅ Logger 模块导入成功
✅ Utils 模块导入成功
✅ MainWindow 导入成功
✅ PyQt6 导入成功

🔧 测试配置系统...
✅ 配置文件加载成功
   FFmpeg路径: ffmpeg
   日志级别: INFO

📝 测试日志系统...
✅ 日志系统初始化成功
✅ 日志记录测试成功

🖥️ 测试GUI创建...
✅ QApplication 创建成功
✅ MainWindow 创建成功

🔧 测试工具函数...
✅ 目录创建测试: True
✅ 时间格式化测试: 01:01:01
✅ 文件名提取测试: video

==================================================
📊 测试结果: 5/5 通过
🎉 所有测试通过！MVP版本准备就绪。
```

#### 3. 启动应用
```bash
# 启动GUI应用
python main.py
```

成功启动后，控制台会显示：
```
✨ 智能视频水印去除工具 MVP版本启动成功！
Python 版本: 3.x.x
🚀 GUI界面已打开，请在窗口中操作
```

## 📖 使用说明

### 界面布局
```
┌─────────────────────────────────────────┐
│    🎬 智能水印去除工具 - MVP版本          │
├─────────────────────────────────────────┤
│  状态: 📁 请选择图片或视频文件开始处理...   │
├─────────────────────────────────────────┤
│  [📂 选择文件]  [💾 导出结果]            │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐ │
│  │          🖼️ 预览区域              │ │
│  │     (显示选中的图片文件)           │ │
│  └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│  [████████████████] 50%                 │
│  [✨ 开始去除水印]                      │
├─────────────────────────────────────────┤
│  处理日志:                              │
│  [12:34:56] INFO: 文件加载成功...       │
└─────────────────────────────────────────┘
```

### 操作流程

#### 1. 选择文件
- 点击 **"📂 选择文件"** 按钮
- 支持的格式：
  - **图片**: .jpg, .jpeg, .png, .bmp
  - **视频**: .mp4, .avi, .mkv, .mov (预览功能待实现)
- 选择后会在预览区域显示图片

#### 2. 开始处理
- 选择文件后，**"✨ 开始去除水印"** 按钮会激活
- 点击按钮开始模拟处理
- 进度条会显示处理进度
- 日志区域会实时显示处理状态

#### 3. 导出结果
- 处理完成后，**"💾 导出结果"** 按钮会激活
- 点击选择保存位置和文件名
- MVP版本仅显示保存路径（实际文件保存功能待实现）

## 🔧 配置说明

### 配置文件位置
- **Windows**: `C:\Users\{用户名}\AppData\Local\VideoWatermarkRemover\config.ini`
- **Linux**: `~/.config/videowatermarkremover/config.ini`
- **macOS**: `~/Library/Application Support/VideoWatermarkRemover/config.ini`

### 配置项说明
```ini
[Paths]
ffmpeg_path = ffmpeg              # FFmpeg路径
default_model_dir = ./models      # 模型文件目录
last_input_dir =                  # 上次输入目录
last_output_dir =                 # 上次输出目录

[Processing]  
default_output_suffix = _processed # 默认输出文件后缀
auto_start_processing = no         # 自动开始处理
gpu_acceleration = auto            # GPU加速设置

[Logging]
log_level = INFO                   # 日志级别
log_file_path = {config_dir}/app.log # 日志文件路径

[Models]
detection_model_path =             # 检测模型路径
inpainting_model_path =            # 修复模型路径
default_confidence_threshold = 0.5 # 默认置信度阈值
```

## 📝 日志系统

### 日志文件位置
与配置文件相同目录下的 `app.log`

### 日志级别
- **DEBUG**: 详细调试信息
- **INFO**: 一般信息记录  
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

### 日志轮转
- 单个日志文件最大 5MB
- 保留最近 5 个备份文件
- 自动压缩历史日志

## ⚠️ 已知限制

### MVP版本限制
- 🔲 **仅模拟处理**: 不执行实际的水印去除
- 🔲 **视频预览**: 视频文件无法预览
- 🔲 **AI模型**: 未集成实际的AI模型
- 🔲 **文件保存**: 不执行实际的文件保存操作

### 系统要求
- Python 3.9+ 
- PyQt6 依赖
- 建议内存 2GB+
- 支持的操作系统: Windows 10+, Ubuntu 18+, macOS 10.15+

## 🐛 故障排除

### 常见问题

#### 1. PyQt6 导入失败
```bash
❌ 缺少必要的依赖库: No module named 'PyQt6'
```
**解决方案**:
```bash
pip install PyQt6
```

#### 2. 配置目录无法创建
```bash
❌ Error creating config directory: Permission denied
```
**解决方案**:
- 检查用户权限
- 手动创建配置目录
- 以管理员权限运行

#### 3. 日志文件写入失败
```bash
❌ Failed to set up file logger: Permission denied
```
**解决方案**:
- 检查日志目录权限
- 修改配置文件中的日志路径

#### 4. GUI界面无法显示
**可能原因**:
- 缺少图形界面环境（Linux服务器）
- PyQt6版本不兼容
- 系统缺少必要的图形库

**解决方案**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-pyqt6

# CentOS/RHEL  
sudo yum install python3-pyqt6
```

## 📞 获取帮助

### 测试命令
```bash
# 测试所有功能
python test_mvp.py

# 测试单个模块
python -c "from app.config_manager import ConfigManager; print('Config OK')"
python -c "from app.main_window import MainWindow; print('GUI OK')"
```

### 调试模式
修改配置文件中的日志级别：
```ini
[Logging]
log_level = DEBUG
```

重启应用查看详细日志信息。

---

## 🎯 下一步计划

MVP版本验证了基础架构的可行性，接下来将进入**第二阶段：核心功能完善**：

1. **轻量级AI模型集成** - OpenCV图像处理实现水印检测
2. **图像修复算法** - 简单的插值填充修复
3. **视频处理扩展** - 支持视频文件的逐帧处理
4. **实际文件处理** - 完整的文件保存和导出功能

*📅 文档更新时间: 2025-01-31*  
*🔄 版本: MVP v0.1.0*  
*📝 作者: Claude Code Assistant*