#!/bin/bash

# 智能视频水印去除工具 - 应用启动脚本
# 自动激活环境并启动应用

set -e

echo "🎬 启动智能视频水印去除工具..."

# 检查 .venv 是否存在
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: ./scripts/setup.sh"
    exit 1
fi

# 根据操作系统激活环境
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # Linux/macOS
    source .venv/bin/activate
fi

# 确保日志目录存在
mkdir -p logs

# 启动应用
echo "🚀 启动应用程序..."
python main.py

echo "✨ 应用程序已退出"
