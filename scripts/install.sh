#!/bin/bash
# 智能视频水印去除工具 - 环境安装脚本
# 自动检测系统并安装相应依赖

set -e

echo "🚀 智能视频水印去除工具 - 环境安装脚本"
echo "================================================"

# 检测操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "🐧 检测到 Linux 系统"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo "🍎 检测到 macOS 系统"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    echo "🪟 检测到 Windows 系统"
else
    OS="unknown"
    echo "❓ 未知系统: $OSTYPE"
fi

# 检查Python版本
echo ""
echo "🐍 检查Python版本..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "✅ Python版本: $PYTHON_VERSION"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version | cut -d' ' -f2)
    echo "✅ Python版本: $PYTHON_VERSION"
    PYTHON_CMD="python"
else
    echo "❌ 未找到Python，请先安装Python 3.8+"
    exit 1
fi

# 检查pip
echo ""
echo "📦 检查pip..."
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
    echo "✅ 找到pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
    echo "✅ 找到pip"
else
    echo "❌ 未找到pip，请先安装pip"
    exit 1
fi

# 询问安装类型
echo ""
echo "📋 请选择安装类型:"
echo "1) 最小安装 (仅核心功能)"
echo "2) 完整安装 (包含AI功能)"
echo "3) 开发环境 (包含开发工具)"
read -p "请输入选择 (1-3): " INSTALL_TYPE

case $INSTALL_TYPE in
    1)
        REQUIREMENTS_FILE="requirements-minimal.txt"
        echo "🎯 选择最小安装"
        ;;
    2)
        REQUIREMENTS_FILE="requirements.txt"
        echo "🎯 选择完整安装"
        ;;
    3)
        REQUIREMENTS_FILE="requirements-dev.txt"
        echo "🎯 选择开发环境安装"
        ;;
    *)
        echo "❌ 无效选择，使用默认完整安装"
        REQUIREMENTS_FILE="requirements.txt"
        ;;
esac

# 创建虚拟环境
echo ""
echo "🏠 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
echo ""
echo "🔄 激活虚拟环境..."
if [[ "$OS" == "windows" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
echo "✅ 虚拟环境已激活"

# 升级pip
echo ""
echo "⬆️ 升级pip..."
python -m pip install --upgrade pip
echo "✅ pip升级完成"

# 安装依赖
echo ""
echo "📦 安装Python依赖..."
echo "使用文件: $REQUIREMENTS_FILE"
pip install -r $REQUIREMENTS_FILE
echo "✅ Python依赖安装完成"

# 安装系统依赖 (FFmpeg)
echo ""
echo "🎬 检查FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1)
    echo "✅ FFmpeg已安装: $FFMPEG_VERSION"
else
    echo "⚠️ 未检测到FFmpeg"
    echo "📖 FFmpeg安装指南:"

    if [[ "$OS" == "linux" ]]; then
        echo "  Ubuntu/Debian: sudo apt install ffmpeg"
        echo "  CentOS/RHEL: sudo yum install ffmpeg"
        echo "  Arch Linux: sudo pacman -S ffmpeg"
    elif [[ "$OS" == "macos" ]]; then
        echo "  Homebrew: brew install ffmpeg"
        echo "  MacPorts: sudo port install ffmpeg"
    elif [[ "$OS" == "windows" ]]; then
        echo "  1. 从 https://ffmpeg.org/download.html 下载"
        echo "  2. 解压到任意目录"
        echo "  3. 将bin文件夹添加到系统PATH"
    fi

    echo ""
    read -p "是否现在安装FFmpeg? (仅Linux/macOS) [y/N]: " INSTALL_FFMPEG

    if [[ $INSTALL_FFMPEG == "y" || $INSTALL_FFMPEG == "Y" ]]; then
        if [[ "$OS" == "linux" ]]; then
            if command -v apt &> /dev/null; then
                echo "🔧 使用apt安装FFmpeg..."
                sudo apt update && sudo apt install -y ffmpeg
            elif command -v yum &> /dev/null; then
                echo "🔧 使用yum安装FFmpeg..."
                sudo yum install -y ffmpeg
            elif command -v pacman &> /dev/null; then
                echo "🔧 使用pacman安装FFmpeg..."
                sudo pacman -S ffmpeg
            else
                echo "❌ 未找到包管理器，请手动安装FFmpeg"
            fi
        elif [[ "$OS" == "macos" ]]; then
            if command -v brew &> /dev/null; then
                echo "🔧 使用Homebrew安装FFmpeg..."
                brew install ffmpeg
            else
                echo "❌ 未找到Homebrew，请先安装Homebrew或手动安装FFmpeg"
            fi
        fi
    fi
fi

# 运行测试
echo ""
read -p "是否运行基础测试? [y/N]: " RUN_TEST

if [[ $RUN_TEST == "y" || $RUN_TEST == "Y" ]]; then
    echo "🧪 运行基础测试..."
    python test_phase3.py
fi

# 完成安装
echo ""
echo "🎉 安装完成!"
echo "================================================"
echo ""
echo "📖 使用说明:"
echo "1. 激活虚拟环境:"
if [[ "$OS" == "windows" ]]; then
    echo "   venv\\Scripts\\activate"
else
    echo "   source venv/bin/activate"
fi
echo ""
echo "2. 运行程序:"
echo "   python main.py"
echo ""
echo "3. 停用虚拟环境:"
echo "   deactivate"
echo ""
echo "📚 更多信息请查看项目文档和README文件"
