#!/bin/bash

# 智能视频水印去除工具 - 构建发布脚本
# 打包生成可执行文件

set -e

echo "📦 构建发布版本..."

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

# 安装打包工具
echo "🔧 安装打包工具..."
uv pip install PyInstaller>=5.0.0

# 清理之前的构建
echo "🧹 清理构建目录..."
rm -rf build/ dist/ *.spec

# 运行测试确保代码正常
echo "🧪 运行测试确保代码质量..."
./scripts/test.sh

# 使用PyInstaller打包
echo "📦 使用PyInstaller打包..."
pyinstaller --onefile \
            --windowed \
            --name="智能水印去除工具" \
            --icon="app/assets/icons/app.ico" \
            --add-data="app:app" \
            --add-data="models:models" \
            --hidden-import="PyQt6" \
            --hidden-import="cv2" \
            --hidden-import="numpy" \
            main.py

# 创建发布目录
echo "📁 创建发布包..."
mkdir -p release
cp -r dist/* release/
cp README.md release/
cp requirements.txt release/

# 创建版本信息
echo "📝 生成版本信息..."
cat > release/VERSION.txt << EOF
智能视频水印去除工具
版本: v0.3.0-optimized
构建时间: $(date)
Python版本: $(python --version)
构建环境: 现代化 uv + .venv 环境
EOF

echo ""
echo "🎉 构建完成！"
echo "📦 发布文件位于: release/ 目录"
echo "📊 构建日志已保存到 logs/ 目录"