# 智能视频水印去除工具 - 测试文档

**版本**: v0.3.0-refactored
**更新时间**: 2025-01-15
**作者**:

## 📋 目录

1. [测试概述](#测试概述)
2. [测试框架](#测试框架)
3. [单元测试](#单元测试)
4. [集成测试](#集成测试)
5. [代码覆盖率](#代码覆盖率)
6. [运行测试](#运行测试)
7. [编写测试](#编写测试)
8. [CI/CD集成](#cicd集成)

---

## 测试概述

### 测试策略

项目采用**测试金字塔**策略：

```
      /\
     /集\      少量端到端测试
    /成测\
   /试____\
  /单元测试\   大量单元测试
 /__________\
```

- **单元测试** (70%): 测试独立函数和类
- **集成测试** (25%): 测试模块间交互
- **端到端测试** (5%): 测试完整工作流

### 测试原则

1. **快速反馈**: 单元测试运行时间 < 5秒
2. **隔离性**: 每个测试独立运行，不依赖其他测试
3. **可重复性**: 测试结果稳定，不受运行顺序影响
4. **有意义**: 测试业务逻辑，不测试框架代码
5. **可维护性**: 测试代码清晰，易于理解和修改

### 测试覆盖率目标

| 模块类型 | 覆盖率目标 | 当前覆盖率 |
|---------|-----------|-----------|
| 核心模块 (core/) | ≥ 80% | 进行中 |
| UI模块 (ui/) | ≥ 60% | 待开发 |
| 配置模块 (config/) | ≥ 90% | 90%+ |
| 工具模块 (utils/) | ≥ 70% | 待开发 |
| **总体目标** | **≥ 70%** | **进行中** |

---

## 测试框架

### 技术栈

```python
# pytest - 测试框架
pytest >= 7.0.0

# pytest-qt - PyQt6测试
pytest-qt >= 4.2.0

# pytest-cov - 代码覆盖率
pytest-cov >= 4.0.0

# pytest-mock - Mock支持
pytest-mock >= 3.10.0
```

### 目录结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # pytest配置和fixtures
├── unit/                    # 单元测试
│   ├── __init__.py
│   ├── test_config_manager.py       # 配置管理器测试
│   ├── test_watermark_detector.py   # 水印检测器测试
│   └── test_image_inpainter.py      # 图像修复器测试
└── integration/             # 集成测试
    ├── __init__.py
    ├── test_ai_workflow.py          # AI工作流测试
    └── test_video_processing.py     # 视频处理测试
```

### Pytest 配置

**[pyproject.toml](../pyproject.toml:141)** 中的配置：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

---

## 单元测试

### ConfigManager 测试

**文件**: [tests/unit/test_config_manager.py](../tests/unit/test_config_manager.py:1)
**测试用例数**: 18个
**覆盖率**: 90%+

#### 测试类组织

```python
class TestConfigManager:
    """ConfigManager基础功能测试"""

    def test_load_config_creates_file_if_not_exists(self):
        """测试配置文件不存在时自动创建"""
        ...

    def test_load_config_reads_existing_file(self):
        """测试读取已存在的配置文件"""
        ...

    def test_save_config_persists_changes(self):
        """测试配置变更持久化"""
        ...
```

```python
class TestConfigManagerEdgeCases:
    """ConfigManager边界情况测试"""

    def test_load_config_handles_corrupted_file(self):
        """测试处理损坏的配置文件"""
        ...

    def test_load_config_handles_permission_error(self):
        """测试处理权限错误"""
        ...
```

#### 重要测试案例

**测试配置文件创建**:
```python
def test_load_config_creates_file_if_not_exists(self, temp_config_file):
    """测试当配置文件不存在时会创建默认配置"""
    assert not temp_config_file.exists()

    config = ConfigManager.load_config(str(temp_config_file))

    assert temp_config_file.exists()
    assert isinstance(config, ConfigParser)
    assert config.has_section("processing")
    assert config.has_section("ui")
```

**测试配置持久化**:
```python
def test_save_config_persists_changes(self, temp_config_file):
    """测试配置保存后能正确持久化"""
    config = ConfigManager.load_config(str(temp_config_file))
    config.set("ui", "theme", "light")

    success = ConfigManager.save_config(config, str(temp_config_file))
    assert success is True

    # 重新加载验证
    reloaded_config = ConfigManager.load_config(str(temp_config_file))
    assert reloaded_config.get("ui", "theme") == "light"
```

---

### WatermarkDetector 测试

**文件**: [tests/unit/test_watermark_detector.py](../tests/unit/test_watermark_detector.py:1)
**测试用例数**: 23+个
**覆盖率**: 目标 80%

#### 测试类组织

```python
class TestWatermarkDetector:
    """基础功能测试"""

class TestWatermarkDetectorConstants:
    """常量验证测试"""

class TestWatermarkDetectorEdgeCases:
    """边界情况测试"""

class TestWatermarkDetectorWithConfig:
    """配置集成测试"""
```

#### 重要测试案例

**测试水印检测**:
```python
def test_detect_watermark_with_simulated_text(self):
    """测试在包含模拟文本的图像上检测"""
    detector = WatermarkDetector()
    detector.load_model()

    # 创建包含白色矩形的图像（模拟水印）
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(image, (50, 50), (200, 100), (255, 255, 255), -1)

    result = detector.detect_watermark(image)

    assert result is not None
    assert isinstance(result, np.ndarray)
    assert np.any(result > 0)  # 应该检测到水印区域
```

**测试常量验证**:
```python
def test_mask_binary_threshold_is_defined(self):
    """测试掩码二值化阈值已定义"""
    from app.core.ai.watermark_detector import EDGE_THRESHOLD_LOW, EDGE_THRESHOLD_HIGH

    assert isinstance(EDGE_THRESHOLD_LOW, int)
    assert isinstance(EDGE_THRESHOLD_HIGH, int)
    assert 0 < EDGE_THRESHOLD_LOW < EDGE_THRESHOLD_HIGH <= 255
```

---

### ImageInpainter 测试

**文件**: [tests/unit/test_image_inpainter.py](../tests/unit/test_image_inpainter.py:1)
**测试用例数**: 28+个
**覆盖率**: 目标 80%

#### 测试类组织

```python
class TestImageInpainter:
    """基础功能测试"""

class TestImageInpainterConstants:
    """常量验证测试"""

class TestImageInpainterEdgeCases:
    """边界情况测试"""

class TestImageInpainterWithConfig:
    """配置集成测试"""

class TestImageInpainterPerformance:
    """性能测试"""
```

#### 重要测试案例

**测试小区域修复**:
```python
def test_inpaint_frame_with_small_area_uses_custom_method(self, mock_image):
    """测试小区域修复使用自定义方法"""
    inpainter = ImageInpainter()
    inpainter.load_model()

    # 创建小面积掩码 (< 5%图像面积)
    mask = np.zeros((480, 640), dtype=np.uint8)
    mask[200:220, 300:320] = 255  # 20x20像素

    result = inpainter.inpaint_frame(mock_image, mask)

    assert result is not None
    assert result.shape == mock_image.shape
```

**测试性能**:
```python
@pytest.mark.slow
def test_inpaint_completes_in_reasonable_time(self, mock_image):
    """测试修复在合理时间内完成"""
    import time

    inpainter = ImageInpainter()
    inpainter.load_model()

    mask = np.zeros((480, 640), dtype=np.uint8)
    mask[200:300, 300:400] = 255  # 100x100像素

    start_time = time.time()
    result = inpainter.inpaint_frame(mock_image, mask)
    elapsed_time = time.time() - start_time

    assert result is not None
    assert elapsed_time < 5.0  # 应该在5秒内完成
```

---

## 集成测试

### AI 工作流测试

**测试范围**: WatermarkDetector + ImageInpainter + AIHandler

```python
class TestAIWorkflow:
    """测试完整的AI处理流程"""

    def test_complete_processing_workflow(self):
        """测试完整的检测-修复流程"""
        # 1. 创建测试图像
        image = self._create_test_image_with_watermark()

        # 2. 创建AI Handler
        ai_handler = AIHandler()
        ai_handler.load_models()

        # 3. 处理图像
        params = {"auto_detect": True, "detection_sensitivity": 0.5}
        result, info = ai_handler.process_frame(image, params)

        # 4. 验证结果
        assert result is not None
        assert info["watermark_areas_found"] > 0
        assert "processing_time" in info
        assert "inpainting_method" in info
```

### 视频处理测试

```python
class TestVideoProcessing:
    """测试视频处理流程"""

    @pytest.mark.slow
    def test_process_short_video(self, tmp_path):
        """测试处理短视频"""
        input_video = self._create_test_video(frames=10)
        output_video = tmp_path / "output.mp4"

        processor = VideoProcessorThread(
            input_path=str(input_video),
            output_path=str(output_video),
            ai_params={"auto_detect": True}
        )

        # 模拟信号连接
        results = {"progress": [], "status": []}
        processor.progress.connect(lambda p: results["progress"].append(p))
        processor.status.connect(lambda s: results["status"].append(s))

        # 运行处理
        processor.run()

        # 验证结果
        assert output_video.exists()
        assert len(results["progress"]) > 0
        assert 100 in results["progress"]  # 应该达到100%
```

---

## 代码覆盖率

### 生成覆盖率报告

```bash
# HTML报告（推荐）
pytest tests/ --cov=app --cov-report=html

# 终端报告
pytest tests/ --cov=app --cov-report=term

# XML报告（用于CI/CD）
pytest tests/ --cov=app --cov-report=xml
```

### 覆盖率报告位置

- HTML报告: `htmlcov/index.html`
- XML报告: `coverage.xml`

### 覆盖率配置

**[pyproject.toml](../pyproject.toml:158)** 中的配置：

```toml
[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/test_*",
    "venv/*",
    ".venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

---

## 运行测试

### 使用自动化脚本

```powershell
# 运行所有测试
.\scripts\test.ps1

# 仅运行单元测试
.\scripts\test.ps1 unit

# 运行测试并生成覆盖率报告
.\scripts\test.ps1 -Coverage

# 快速测试（跳过慢速测试）
.\scripts\test.ps1 -Quick

# 详细输出
.\scripts\test.ps1 -Verbose
```

### 使用Pytest直接运行

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/unit/test_config_manager.py -v

# 运行特定测试类
pytest tests/unit/test_config_manager.py::TestConfigManager -v

# 运行特定测试方法
pytest tests/unit/test_config_manager.py::TestConfigManager::test_load_config_creates_file_if_not_exists -v

# 跳过慢速测试
pytest tests/ -v -m "not slow"

# 仅运行单元测试
pytest tests/unit/ -v

# 并行运行测试（需要pytest-xdist）
pytest tests/ -n auto
```

### 运行结果示例

```
==================== test session starts ====================
platform win32 -- Python 3.12.0, pytest-7.4.3
rootdir: C:\cascadeProjects\video_watermark_remover
collected 69 items

tests/unit/test_config_manager.py::TestConfigManager::test_load_config_creates_file_if_not_exists PASSED [ 1%]
tests/unit/test_config_manager.py::TestConfigManager::test_load_config_reads_existing_file PASSED [ 2%]
...
tests/unit/test_image_inpainter.py::TestImageInpainterPerformance::test_inpaint_completes_in_reasonable_time PASSED [100%]

==================== 69 passed in 12.34s ====================
```

---

## 编写测试

### Fixtures (测试夹具)

**[tests/conftest.py](../tests/conftest.py:1)** 提供了共享的fixtures：

```python
@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def mock_image():
    """创建模拟图像数据（使用numpy）"""
    import numpy as np
    return np.zeros((480, 640, 3), dtype=np.uint8)

@pytest.fixture
def mock_mask():
    """创建模拟掩码数据"""
    import numpy as np
    mask = np.zeros((480, 640), dtype=np.uint8)
    mask[100:200, 100:200] = 255
    return mask
```

### 测试命名规范

```python
# ✅ 正确：清晰描述测试内容
def test_load_config_creates_file_if_not_exists(): ...
def test_detector_returns_none_for_empty_image(): ...
def test_inpainter_handles_invalid_mask_gracefully(): ...

# ❌ 错误：不清晰的命名
def test_config(): ...
def test_detector_1(): ...
def test_function(): ...
```

### 测试结构 (AAA模式)

```python
def test_example():
    # Arrange (准备)
    detector = WatermarkDetector()
    detector.load_model()
    image = create_test_image()

    # Act (执行)
    result = detector.detect_watermark(image)

    # Assert (断言)
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (480, 640)
```

### Mock 使用

```python
def test_with_mock(mocker):
    """使用mock模拟外部依赖"""
    # Mock cv2.imread
    mock_imread = mocker.patch("cv2.imread")
    mock_imread.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

    # 测试代码
    image = cv2.imread("fake_path.jpg")
    assert image is not None
```

### 参数化测试

```python
@pytest.mark.parametrize("sensitivity, expected_result", [
    (0.0, "low_sensitivity"),
    (0.5, "medium_sensitivity"),
    (1.0, "high_sensitivity"),
])
def test_detector_with_different_sensitivities(sensitivity, expected_result):
    """测试不同敏感度的检测结果"""
    detector = WatermarkDetector()
    result = detector.detect_watermark(image, sensitivity)
    # 验证逻辑...
```

---

## CI/CD集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest tests/ -v --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-commit Hooks

**.pre-commit-config.yaml** 已配置测试钩子：

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: [tests/, -v, --tb=short]
```

---

## 最佳实践

### 1. 测试隔离

```python
# ✅ 正确：每个测试独立
def test_load_config_creates_file(temp_config_file):
    config = ConfigManager.load_config(str(temp_config_file))
    assert config is not None

# ❌ 错误：测试间有依赖
shared_config = None  # 全局变量

def test_load_config():
    global shared_config
    shared_config = ConfigManager.load_config()

def test_save_config():
    # 依赖上一个测试
    ConfigManager.save_config(shared_config)
```

### 2. 有意义的断言

```python
# ✅ 正确：具体的断言
assert result is not None
assert isinstance(result, np.ndarray)
assert result.shape == (480, 640)
assert np.sum(result > 0) > 100  # 至少100个像素被标记

# ❌ 错误：模糊的断言
assert result  # 什么是"真"？
assert result == expected  # expected是什么？
```

### 3. 测试边界条件

```python
def test_edge_cases():
    """测试边界情况"""
    detector = WatermarkDetector()

    # 空图像
    assert detector.detect_watermark(None) is None

    # 极小图像
    tiny_image = np.zeros((10, 10, 3), dtype=np.uint8)
    result = detector.detect_watermark(tiny_image)
    assert result is not None

    # 极大图像
    huge_image = np.zeros((10000, 10000, 3), dtype=np.uint8)
    result = detector.detect_watermark(huge_image)
    assert result is not None
```

---

## 测试指标

### 当前测试覆盖情况

| 模块 | 测试用例 | 覆盖率 | 状态 |
|------|---------|-------|------|
| ConfigManager | 18个 | 90%+ | ✅ 完成 |
| WatermarkDetector | 23+个 | 进行中 | 🚧 进行中 |
| ImageInpainter | 28+个 | 进行中 | 🚧 进行中 |
| AIHandler | 待开发 | 0% | ⏳ 待开发 |
| VideoProcessorThread | 待开发 | 0% | ⏳ 待开发 |
| **总计** | **69+个** | **进行中** | **🚧 进行中** |

### 下一步计划

- [ ] 完成 AIHandler 单元测试
- [ ] 完成 VideoProcessorThread 集成测试
- [ ] 添加 UI 组件测试（pytest-qt）
- [ ] 实现端到端测试
- [ ] 提高覆盖率至70%+
- [ ] 集成到CI/CD流水线

---

**相关文档**:
- [架构设计文档](architecture.md)
- [API 接口文档](api.md)
- [开发指南](development.md)
