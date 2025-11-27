# 智能视频水印去除工具 - 开发指南

**版本**: v0.3.0-refactored
**更新时间**: 2025-01-15
**作者**: 

## 📋 目录

1. [开发环境配置](#开发环境配置)
2. [代码规范](#代码规范)
3. [工作流程](#工作流程)
4. [项目结构](#项目结构)
5. [常见任务](#常见任务)
6. [故障排除](#故障排除)
7. [贡献指南](#贡献指南)

---

## 开发环境配置

### 环境要求

- **Python**: 3.8+ (推荐 3.12)
- **操作系统**: Windows 10/11, Linux, macOS
- **FFmpeg**: 可选，用于音频处理
- **IDE**: 推荐 VS Code 或 PyCharm
- **Git**: 版本控制

### 快速开始

**1. 克隆仓库**

```bash
git clone https://github.com/yourusername/video_watermark_remover.git
cd video_watermark_remover
```

**2. 环境初始化（Windows）**

```powershell
# 使用自动化脚本
.\scripts\setup.ps1

# 脚本会自动执行：
# - 创建虚拟环境
# - 安装生产依赖
# - 安装开发依赖
# - 安装pre-commit hooks
# - 创建配置文件
```

**3. 手动配置（可选）**

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 安装pre-commit hooks
pre-commit install
```

**4. 验证安装**

```bash
# 运行测试
pytest tests/ -v

# 运行代码质量检查
.\scripts\check-quality.ps1

# 启动应用
python main.py
```

### IDE 配置

#### VS Code

**推荐扩展**:
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "ms-python.flake8",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff"
  ]
}
```

**settings.json**:
```json
{
  "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm

**配置步骤**:
1. File → Settings → Project → Python Interpreter → 选择 `.venv`
2. File → Settings → Tools → Python Integrated Tools:
   - Default test runner: pytest
   - Docstring format: Google
3. File → Settings → Tools → Black:
   - Line length: 100
   - Enable on save
4. File → Settings → Tools → External Tools:
   - 添加 Flake8 和 MyPy

---

## 代码规范

### Python 代码风格

#### PEP 8 基础

```python
# ✅ 正确：遵循PEP 8
class WatermarkDetector:
    """水印检测器类。

    使用OpenCV传统图像处理方法检测水印区域。
    """

    def __init__(self, config: Optional[ConfigParser] = None) -> None:
        """初始化检测器。

        Args:
            config: 配置对象（可选）
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def detect_watermark(
        self,
        image: np.ndarray,
        sensitivity: float = 0.5
    ) -> Optional[np.ndarray]:
        """检测图像中的水印区域。

        Args:
            image: 输入图像（BGR格式）
            sensitivity: 检测敏感度 (0.0-1.0)

        Returns:
            二值掩码，None表示检测失败
        """
        if image is None:
            self.logger.error("输入图像为空")
            return None

        # 处理逻辑...
        return mask
```

```python
# ❌ 错误：不遵循规范
class watermark_detector:  # 类名应该是大驼峰
    def __init__(self,config=None):  # 缺少类型注解和空格
        self.config=config  # 操作符周围缺少空格

    def detect(self,img):  # 参数缺少类型注解
        if img == None:  # 应该使用 is None
            return  # 返回值不明确
        # ...
```

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块/包 | 小写+下划线 | `watermark_detector.py` |
| 类 | 大驼峰 | `WatermarkDetector` |
| 函数/方法 | 小写+下划线 | `detect_watermark()` |
| 常量 | 全大写+下划线 | `EDGE_THRESHOLD_LOW` |
| 变量 | 小写+下划线 | `detection_result` |
| 私有成员 | 前缀`_` | `_internal_method()` |

#### 类型注解

```python
# ✅ 正确：完整的类型注解
from typing import Optional, Dict, Any, Tuple, List
import numpy as np

def process_frame(
    frame: np.ndarray,
    params: Optional[Dict[str, Any]] = None
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """处理单个帧。"""
    ...

# ❌ 错误：缺少类型注解
def process_frame(frame, params=None):
    """处理单个帧。"""
    ...
```

#### 文档字符串 (Google Style)

```python
def detect_watermark(
    self,
    image: np.ndarray,
    sensitivity: float = 0.5
) -> Optional[np.ndarray]:
    """检测图像中的水印区域。

    使用Canny边缘检测和形态学操作识别潜在的水印区域。

    Args:
        image: 输入图像，BGR格式的numpy数组
        sensitivity: 检测敏感度，范围0.0-1.0
            - 0.0: 最低敏感度，只检测明显水印
            - 0.5: 中等敏感度（默认）
            - 1.0: 最高敏感度，可能产生误检

    Returns:
        二值掩码（单通道，0/255），如果检测失败返回None

    Raises:
        ValueError: 如果image为空或格式不正确
        RuntimeError: 如果检测过程发生错误

    Example:
        >>> detector = WatermarkDetector()
        >>> detector.load_model()
        >>> image = cv2.imread("input.jpg")
        >>> mask = detector.detect_watermark(image, sensitivity=0.6)
        >>> if mask is not None:
        ...     print(f"检测到水印区域")
    """
    ...
```

### 项目特定规范

#### 模块组织

```python
# 导入顺序
# 1. 标准库
import os
import sys
import logging
from typing import Optional, Dict, Any

# 2. 第三方库
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

# 3. 项目内部导入
from app.core.ai.watermark_detector import WatermarkDetector
from app.core.ai.image_inpainter import ImageInpainter
from app.config.config_manager import ConfigManager
```

#### 常量提取

```python
# ✅ 正确：提取魔法数字为常量
# 模块级别常量
EDGE_THRESHOLD_LOW = 50
EDGE_THRESHOLD_HIGH = 150
MORPH_KERNEL_SIZE = 5
MIN_CONTOUR_AREA = 100

def detect_edges(image):
    edges = cv2.Canny(image, EDGE_THRESHOLD_LOW, EDGE_THRESHOLD_HIGH)
    return edges

# ❌ 错误：使用魔法数字
def detect_edges(image):
    edges = cv2.Canny(image, 50, 150)  # 50和150是什么意思？
    return edges
```

#### 错误处理

```python
# ✅ 正确：详细的错误处理
def load_image(file_path: str) -> np.ndarray:
    """加载图像文件。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    image = cv2.imread(file_path)
    if image is None:
        raise ValueError(f"无法读取图像文件: {file_path}")

    return image

# ❌ 错误：吞没异常
def load_image(file_path):
    try:
        return cv2.imread(file_path)
    except:  # 过于宽泛的异常捕获
        return None  # 丢失了错误信息
```

---

## 工作流程

### Git 工作流

#### 分支策略

```
main (主分支)
  ├── develop (开发分支)
  │   ├── feature/watermark-detection (功能分支)
  │   ├── feature/ui-improvements (功能分支)
  │   └── bugfix/config-loading (修复分支)
  └── hotfix/critical-bug (紧急修复)
```

#### 提交规范

**格式**: `<type>(<scope>): <subject>`

**类型 (type)**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```bash
git commit -m "feat(ai): 添加水印检测敏感度参数"
git commit -m "fix(ui): 修复预览面板图像缩放问题"
git commit -m "docs(api): 更新AIHandler接口文档"
git commit -m "refactor(core): 提取图像处理常量"
git commit -m "test(ai): 添加ImageInpainter单元测试"
```

### 开发流程

**1. 创建功能分支**

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

**2. 开发功能**

```bash
# 编写代码
# 编写测试
# 运行测试
pytest tests/ -v

# 运行代码质量检查
.\scripts\check-quality.ps1

# 如果格式有问题，自动修复
.\scripts\check-quality.ps1 -Fix
```

**3. 提交代码**

```bash
# 添加文件
git add .

# 提交（pre-commit hooks会自动运行检查）
git commit -m "feat(scope): description"

# 如果pre-commit检查失败，修复后重新提交
```

**4. 推送和创建PR**

```bash
git push origin feature/your-feature-name

# 在GitHub上创建Pull Request
# PR标题遵循提交规范
# 填写PR模板，说明变更内容
```

**5. 代码审查和合并**

- 至少一人审查代码
- 所有测试通过
- 代码质量检查通过
- 解决所有评审意见
- 合并到develop分支

### Pre-commit Hooks

安装后，每次 `git commit` 时自动运行：

1. **Black**: 自动格式化代码
2. **isort**: 排序import语句
3. **Flake8**: 检查代码风格
4. **MyPy**: 类型检查
5. **其他检查**: 文件大小、YAML格式、私钥检测等

**跳过hooks（不推荐）**:
```bash
git commit --no-verify -m "message"
```

---

## 项目结构

### 目录组织

```
video_watermark_remover/
├── app/                          # 主应用代码
│   ├── __init__.py
│   ├── core/                     # 核心功能模块
│   │   ├── __init__.py
│   │   ├── ai/                   # AI处理模块
│   │   │   ├── __init__.py
│   │   │   ├── ai_handler.py         # AI协调器
│   │   │   ├── watermark_detector.py # 水印检测
│   │   │   └── image_inpainter.py    # 图像修复
│   │   ├── audio/                # 音频处理
│   │   │   ├── __init__.py
│   │   │   └── ffmpeg_audio_processor.py
│   │   └── video/                # 视频处理
│   │       ├── __init__.py
│   │       └── video_processor.py
│   ├── ui/                       # UI模块
│   │   ├── __init__.py
│   │   ├── main_window.py            # 主窗口
│   │   ├── signal_handler.py         # 信号处理
│   │   ├── components/               # UI组件
│   │   └── widgets/                  # 自定义控件
│   ├── config/                   # 配置管理
│   │   ├── __init__.py
│   │   ├── config_manager.py         # 配置管理器
│   │   └── preferences_manager.py    # 偏好设置
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       └── logger_setup.py
├── tests/                        # 测试文件
│   ├── __init__.py
│   ├── conftest.py                   # pytest配置
│   ├── unit/                         # 单元测试
│   └── integration/                  # 集成测试
├── scripts/                      # 辅助脚本
│   ├── setup.ps1                     # 环境初始化
│   ├── start.ps1                     # 启动应用
│   ├── test.ps1                      # 运行测试
│   └── check-quality.ps1             # 代码质量检查
├── docs/                         # 文档
│   ├── architecture.md               # 架构设计
│   ├── api.md                        # API接口
│   ├── testing.md                    # 测试文档
│   └── development.md                # 开发指南
├── discuss/                      # 讨论记录
├── models/                       # 模型文件
├── logs/                         # 日志文件
├── .flake8                       # Flake8配置
├── .pre-commit-config.yaml       # Pre-commit配置
├── .gitignore                    # Git忽略文件
├── pyproject.toml                # 项目配置
├── requirements.txt              # 生产依赖
├── requirements-dev.txt          # 开发依赖
├── config.ini                    # 主配置文件
├── main.py                       # 程序入口
└── README.md                     # 项目说明
```

### 模块职责

| 模块 | 职责 | 示例文件 |
|------|------|---------|
| `core/ai/` | AI处理逻辑 | watermark_detector.py |
| `core/audio/` | 音频处理 | ffmpeg_audio_processor.py |
| `core/video/` | 视频编解码 | video_processor.py |
| `ui/` | 用户界面 | main_window.py |
| `config/` | 配置管理 | config_manager.py |
| `utils/` | 通用工具 | logger_setup.py |
| `tests/` | 测试代码 | test_*.py |
| `scripts/` | 辅助脚本 | *.ps1 |

---

## 常见任务

### 添加新功能

**示例：添加新的水印检测算法**

1. **创建新文件**:
```python
# app/core/ai/deep_learning_detector.py
from typing import Optional
import numpy as np

class DeepLearningDetector:
    """基于深度学习的水印检测器。"""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None

    def load_model(self) -> bool:
        """加载深度学习模型。"""
        # 实现加载逻辑
        ...

    def detect_watermark(
        self,
        image: np.ndarray
    ) -> Optional[np.ndarray]:
        """使用深度学习模型检测水印。"""
        # 实现检测逻辑
        ...
```

2. **编写测试**:
```python
# tests/unit/test_deep_learning_detector.py
import pytest
from app.core.ai.deep_learning_detector import DeepLearningDetector

class TestDeepLearningDetector:
    def test_load_model_success(self):
        """测试模型加载成功。"""
        detector = DeepLearningDetector("model.pth")
        assert detector.load_model() is True

    def test_detect_watermark_returns_mask(self, mock_image):
        """测试检测返回掩码。"""
        detector = DeepLearningDetector("model.pth")
        detector.load_model()

        mask = detector.detect_watermark(mock_image)

        assert mask is not None
        assert isinstance(mask, np.ndarray)
```

3. **集成到AIHandler**:
```python
# app/core/ai/ai_handler.py
from app.core.ai.deep_learning_detector import DeepLearningDetector

class AIHandler:
    def __init__(self, ...):
        # ...
        self.dl_detector = DeepLearningDetector("model.pth")
```

4. **更新文档**:
- 更新 `docs/api.md` 添加新API
- 更新 `README.md` 说明新功能

5. **提交代码**:
```bash
git add app/core/ai/deep_learning_detector.py
git add tests/unit/test_deep_learning_detector.py
git commit -m "feat(ai): 添加基于深度学习的水印检测器"
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/unit/test_watermark_detector.py -v

# 运行并生成覆盖率报告
pytest tests/ --cov=app --cov-report=html

# 跳过慢速测试
pytest tests/ -v -m "not slow"

# 并行运行（需要pytest-xdist）
pytest tests/ -n auto
```

### 代码质量检查

```bash
# 运行所有检查
.\scripts\check-quality.ps1

# 自动修复格式问题
.\scripts\check-quality.ps1 -Fix

# 快速检查（跳过MyPy）
.\scripts\check-quality.ps1 -Quick

# 仅检查特定类型
.\scripts\check-quality.ps1 -Check format
.\scripts\check-quality.ps1 -Check style
.\scripts\check-quality.ps1 -Check type
```

### 构建和发布

```bash
# 构建Python包
python -m build

# 检查包
twine check dist/*

# 上传到PyPI（测试）
twine upload --repository testpypi dist/*

# 上传到PyPI（正式）
twine upload dist/*
```

---

## 故障排除

### 常见问题

#### 1. 虚拟环境激活失败

**问题**: PowerShell脚本执行策略限制

**解决方案**:
```powershell
# 临时允许脚本执行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 永久允许（管理员权限）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. pytest找不到模块

**问题**: PYTHONPATH未设置

**解决方案**:
```bash
# Windows
$env:PYTHONPATH = (Get-Location).Path

# Linux/macOS
export PYTHONPATH=$(pwd)
```

#### 3. Pre-commit hooks失败

**问题**: Black修改了文件但提交失败

**解决方案**:
```bash
# 重新add修改的文件
git add .

# 重新提交
git commit -m "message"
```

#### 4. FFmpeg不可用

**问题**: 视频音频处理失败

**解决方案**:
```bash
# Windows（使用Chocolatey）
choco install ffmpeg

# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# 验证安装
ffmpeg -version
```

### 调试技巧

#### 使用日志

```python
import logging

logger = logging.getLogger(__name__)

def process_image(image):
    logger.debug(f"Processing image with shape: {image.shape}")

    try:
        result = detect_watermark(image)
        logger.info("Watermark detection successful")
        return result
    except Exception as e:
        logger.error(f"Watermark detection failed: {e}", exc_info=True)
        raise
```

#### 使用断点

```python
# 使用pdb
import pdb

def debug_function(image):
    pdb.set_trace()  # 程序会在这里暂停
    result = process(image)
    return result

# 或使用breakpoint()（Python 3.7+）
def debug_function(image):
    breakpoint()  # 程序会在这里暂停
    result = process(image)
    return result
```

---

## 贡献指南

### 如何贡献

1. **Fork 项目**
2. **创建功能分支** (`git checkout -b feature/AmazingFeature`)
3. **提交变更** (`git commit -m 'feat: Add some AmazingFeature'`)
4. **推送到分支** (`git push origin feature/AmazingFeature`)
5. **创建 Pull Request**

### PR 检查清单

- [ ] 代码遵循项目规范
- [ ] 添加了相应的测试
- [ ] 所有测试通过
- [ ] 代码质量检查通过
- [ ] 更新了相关文档
- [ ] 提交信息清晰明确

### 代码审查重点

- **功能正确性**: 代码是否实现了预期功能
- **代码质量**: 是否遵循规范和最佳实践
- **测试覆盖**: 是否有足够的测试
- **性能**: 是否有性能问题
- **安全性**: 是否有安全漏洞
- **可维护性**: 代码是否易于理解和维护

---

## 参考资源

### 文档链接

- [Python PEP 8](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [MyPy Documentation](https://mypy.readthedocs.io/)

### 项目文档

- [架构设计文档](architecture.md)
- [API 接口文档](api.md)
- [测试文档](testing.md)
- [README](../README.md)

---

**Happy Coding! 🎉**
