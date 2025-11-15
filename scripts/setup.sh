#!/bin/bash

# 智能视频水印去除工具 - 环境配置脚本
# 使用现代化的 uv 包管理器和 .venv 虚拟环境

set -e

echo "🚀 智能视频水印去除工具 - 现代化环境配置"
echo "================================================="

# 检查 uv 是否已安装
if ! command -v uv &> /dev/null; then
    echo "⚡ 安装 uv 包管理器..."
    pip install uv
    echo "✅ uv 安装完成"
else
    echo "✅ uv 已安装: $(uv --version)"
fi

# 检查并删除旧的 venv 目录
if [ -d "venv" ]; then
    echo "🗑️  删除旧的 venv 目录..."
    rm -rf venv
    echo "✅ 旧环境已清理"
fi

# 创建 .venv 虚拟环境
if [ ! -d ".venv" ]; then
    echo "🐍 创建 .venv 虚拟环境..."
    uv venv .venv
    echo "✅ .venv 环境创建完成"
else
    echo "✅ .venv 环境已存在"
fi

# 激活虚拟环境并安装依赖
echo "📦 使用 uv 安装依赖包..."

# 检查操作系统类型
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows
    source .venv/Scripts/activate
    echo "✅ Windows 环境已激活"
else
    # Linux/macOS
    source .venv/bin/activate
    echo "✅ Unix 环境已激活"
fi

# 使用 uv 安装核心依赖
echo "📦 安装核心依赖..."
uv pip install PyQt6>=6.6.0
uv pip install opencv-python>=4.8.0
uv pip install numpy>=1.25.0
uv pip install Pillow>=10.0.0

# 安装开发依赖
echo "🧪 安装开发和测试依赖..."
uv pip install pytest>=7.0.0
uv pip install pytest-qt>=4.2.0
uv pip install black>=23.0.0
uv pip install flake8>=6.0.0
uv pip install mypy>=1.0.0

echo ""
echo "🎉 环境配置完成！"
echo "================================================="
echo "✅ 使用现代化的 uv + .venv 环境"
echo "✅ 核心依赖已安装"
echo "✅ 开发工具已配置"
echo ""
echo "📝 使用说明："
echo "   激活环境: source .venv/bin/activate (Linux/macOS)"
echo "            source .venv/Scripts/activate (Windows)"
echo "   启动应用: ./scripts/run.sh"
echo "   运行测试: ./scripts/test.sh"
echo ""