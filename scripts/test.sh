#!/bin/bash

# 智能视频水印去除工具 - 测试执行脚本
# 运行完整的测试套件

set -e

echo "🧪 运行测试套件..."

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

echo "🔍 运行代码质量检查..."

# 代码格式检查
echo "📝 检查代码格式 (black)..."
black --check app/ main.py --diff

# 代码风格检查  
echo "📋 检查代码风格 (flake8)..."
flake8 app/ main.py --max-line-length=100 --exclude=.venv

# 类型检查
echo "🔍 检查类型注解 (mypy)..."
mypy app/ main.py --ignore-missing-imports

echo "🧪 运行单元测试..."

# 运行pytest测试
pytest tests/ -v --tb=short

echo "🎯 运行集成测试..."

# 运行各阶段测试
echo "📸 运行MVP功能测试..."
python test_mvp.py

echo "🧠 运行AI功能测试..."
python test_phase2.py

echo "🏗️ 运行产品化功能测试..."
python test_phase3.py

echo "📊 运行批处理测试..."
python test_batch_processing.py

echo ""
echo "✅ 所有测试完成！"
echo "📊 测试报告已保存到 logs/ 目录"