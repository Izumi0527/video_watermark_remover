# Windows 系统快速使用指南

**适用系统**: Windows 10/11  
**Python版本**: 3.9+  
**创建时间**: 2025-09-01  

## 🚀 快速开始 (Windows)

### 1️⃣ 一键环境配置
```batch
# 双击运行或在命令行执行
scripts\setup.bat
```

**这个脚本会自动完成**:
- ✅ 检查并安装 uv 包管理器
- ✅ 清理旧的 venv 环境
- ✅ 创建 .venv 虚拟环境
- ✅ 安装所有核心依赖
- ✅ 安装开发和测试工具

### 2️⃣ 启动应用
```batch
# 双击运行或在命令行执行
scripts\run.bat
```

### 3️⃣ 运行测试 (可选)
```batch
# 双击运行或在命令行执行  
scripts\test.bat
```

### 4️⃣ 构建发布版 (可选)
```batch
# 双击运行或在命令行执行
scripts\build.bat
```

## 📋 Windows 脚本说明

| 脚本文件 | 功能说明 | 使用场景 |
|---------|----------|----------|
| `setup.bat` | 环境配置和依赖安装 | 首次使用或环境出错时 |
| `run.bat` | 启动应用程序 | 日常使用启动应用 |
| `test.bat` | 运行测试套件 | 开发调试和质量检查 |
| `build.bat` | 构建发布版本 | 打包生成可执行文件 |

## ⚡ 快速故障排除

### 问题1: 脚本执行失败
**解决方案**:
```batch
# 以管理员身份运行命令提示符
# 右键点击"命令提示符" -> "以管理员身份运行"
cd /d "C:\cascadeProjects\video_watermark_remover"
scripts\setup.bat
```

### 问题2: uv 安装失败
**解决方案**:
```batch
# 手动安装 uv
pip install --upgrade pip
pip install uv
```

### 问题3: 虚拟环境激活失败
**解决方案**:
```batch
# 删除 .venv 目录重新创建
rmdir /s /q .venv
scripts\setup.bat
```

### 问题4: 依赖安装失败
**解决方案**:
```batch
# 更新pip和setuptools
python -m pip install --upgrade pip setuptools wheel
# 重新运行配置脚本
scripts\setup.bat
```

## 🔧 手动操作 (高级用户)

如果自动脚本无法使用，可以手动执行以下操作：

### 手动环境配置
```batch
# 1. 安装 uv
pip install uv

# 2. 创建虚拟环境
uv venv .venv

# 3. 激活环境
.venv\Scripts\activate.bat

# 4. 安装依赖
uv pip install -r requirements.txt
```

### 手动启动应用
```batch
# 1. 激活环境
.venv\Scripts\activate.bat

# 2. 启动应用
python main.py
```

## 💡 使用技巧

### 1. 桌面快捷方式
在桌面创建快捷方式，目标设置为：
```
C:\cascadeProjects\video_watermark_remover\scripts\run.bat
```

### 2. 添加到系统PATH
将项目scripts目录添加到系统PATH环境变量，可在任意位置执行：
```batch
run.bat
test.bat
```

### 3. 定期更新依赖
```batch
# 激活环境后更新依赖
.venv\Scripts\activate.bat
uv pip install --upgrade -r requirements.txt
```

## 🆘 获取帮助

如遇问题，请：
1. 查看 `logs\` 目录下的日志文件
2. 在项目仓库提交 Issue
3. 提供详细的错误信息和系统环境

---

**🎉 现在你可以在Windows系统上轻松使用智能视频水印去除工具了！**