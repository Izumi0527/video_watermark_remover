# Scripts 目录使用说明

## 📋 目录概述

本目录包含了智能视频水印去除工具的所有自动化脚本，用于环境配置、项目运行、测试、构建和代码质量管理。

**脚本类型分类：**
- 🔧 **环境管理脚本**：环境配置和依赖安装
- 🚀 **运行和构建脚本**：应用启动和发布打包
- 🧪 **测试脚本**：单元测试、集成测试、覆盖率分析
- 🔍 **代码质量脚本**：代码格式、风格和类型检查
- 🧹 **维护脚本**：缓存清理和项目维护
- 🤖 **CI/CD 脚本**：持续集成和自动化流程

---

## 🔧 环境管理脚本

### `setup.ps1` / `setup.sh` - 环境配置脚本（推荐使用）

**功能：** 使用现代化的 `uv` 包管理器和 `.venv` 虚拟环境配置项目开发环境。

**特点：**
- ✅ 自动安装 `uv` 包管理器
- ✅ 创建 `.venv` 虚拟环境（符合现代 Python 规范）
- ✅ 清理旧的 `venv` 环境
- ✅ 安装核心依赖和开发工具

**使用方法：**

```powershell
# Windows (PowerShell)
.\scripts\setup.ps1

# Linux/macOS (Bash)
./scripts/setup.sh
```

**依赖包：**
- **核心依赖：** PyQt6, opencv-python, numpy, Pillow
- **开发依赖：** pytest, pytest-qt, black, flake8, mypy

---

### `install.ps1` / `install.sh` - 环境安装脚本（旧版）

**功能：** 提供交互式环境安装，支持多种安装模式和系统依赖检查。

**特点：**
- 📋 交互式安装类型选择（最小/完整/开发环境）
- 🔍 自动检测操作系统和 Python 版本
- 🎬 FFmpeg 安装指导和自动安装（Linux/macOS）
- 🧪 可选的基础测试运行

**使用方法：**

```powershell
# Windows
.\scripts\install.ps1

# Linux/macOS
./scripts/install.sh
```

**安装类型：**
1. **最小安装** - 仅核心功能（无 AI 模块）
2. **完整安装** - 包含 AI 功能（推荐）
3. **开发环境** - 包含开发工具和测试框架

**注意：** 此脚本为旧版本，推荐使用 `setup.ps1/sh` 替代。

---

## 🚀 运行和构建脚本

### `run.ps1` / `run.sh` - 应用启动脚本（简洁版）

**功能：** 快速启动应用程序，自动激活虚拟环境。

**使用方法：**

```powershell
# Windows
.\scripts\run.ps1

# Linux/macOS
./scripts/run.sh
```

**执行流程：**
1. 检查 `.venv` 虚拟环境是否存在
2. 激活虚拟环境
3. 确保日志目录存在
4. 启动 `main.py`

---

### `start.ps1` - 应用启动脚本（增强版）

**功能：** 提供完整的环境检查、诊断和详细日志记录的启动流程。

**特点：**
- 🔍 环境检查（Python、依赖、FFmpeg、配置文件）
- 📝 详细日志记录到 `logs/log_YYYYMMDD.log`
- 🩺 错误诊断和自动修复功能
- 🎨 彩色终端输出

**使用方法：**

```powershell
# 标准启动
.\scripts\start.ps1

# 自动修复问题
.\scripts\start.ps1 -AutoFix

# 显示详细调试信息
.\scripts\start.ps1 -Verbose

# 跳过环境检查（不推荐）
.\scripts\start.ps1 -SkipChecks
```

**参数说明：**
- `-AutoFix` - 自动修复检测到的问题
- `-Verbose` - 显示详细调试信息
- `-SkipChecks` - 跳过环境检查

---

### `build.ps1` / `build.sh` - 构建发布脚本

**功能：** 使用 PyInstaller 打包生成可执行文件，创建发布版本。

**使用方法：**

```powershell
# Windows
.\scripts\build.ps1

# Linux/macOS
./scripts/build.sh
```

**执行流程：**
1. 检查虚拟环境
2. 安装 PyInstaller 打包工具
3. 清理之前的构建产物
4. 运行测试确保代码质量
5. 使用 PyInstaller 打包应用
6. 创建发布目录和版本信息

**输出：**
- 📦 可执行文件：`release/智能水印去除工具.exe`
- 📄 版本信息：`release/VERSION.txt`
- 📚 文档：`release/README.md`

---

## 🧪 测试脚本

### `test.ps1` / `test.sh` - 增强测试执行脚本（推荐）

**功能：** 参数化、模块化的完整测试套件，支持多种测试类型和模式。

**使用方法：**

```powershell
# 运行所有测试
.\scripts\test.ps1

# 仅运行单元测试
.\scripts\test.ps1 unit

# 运行 AI 模块的集成测试
.\scripts\test.ps1 integration ai

# 快速代码质量检查
.\scripts\test.ps1 quality -Quick

# 运行音频处理测试
.\scripts\test.ps1 audio

# 端到端测试（详细输出）
.\scripts\test.ps1 e2e -Verbose

# 用户偏好设置测试
.\scripts\test.ps1 preferences

# 全面测试并生成覆盖率报告
.\scripts\test.ps1 all all -Coverage

# 包含性能基准测试
.\scripts\test.ps1 all all -Performance

# 查看帮助信息
.\scripts\test.ps1 help
```

**测试类型：**
- `unit` - 单元测试（pytest）
- `integration` - 集成测试（功能测试）
- `quality` - 代码质量检查
- `audio` - 音频处理测试
- `e2e` - 端到端工作流测试
- `preferences` - 用户偏好设置测试
- `all` - 所有测试（默认）

**模块选择：**
- `mvp` - MVP 基础功能
- `ai` - AI 功能模块
- `ui` - UI 组件
- `batch` - 批处理功能
- `video` - 视频处理
- `audio` - 音频处理
- `preferences` - 用户偏好设置
- `all` - 所有模块（默认）

**可选参数：**
- `-Quick` - 快速模式（跳过耗时检查）
- `-Parallel` - 并行执行（实验性）
- `-Report` - 生成详细测试报告
- `-Verbose` - 详细输出模式
- `-Coverage` - 生成代码覆盖率报告
- `-Performance` - 运行性能基准测试

---

### `run-tests.ps1` - 简单单元测试脚本

**功能：** 快速运行 pytest 单元测试的简化脚本。

**使用方法：**

```powershell
# 基本运行
.\scripts\run-tests.ps1

# 详细输出
.\scripts\run-tests.ps1 -Verbose

# 生成覆盖率报告
.\scripts\run-tests.ps1 -Coverage

# 指定测试路径
.\scripts\run-tests.ps1 -TestPath "tests/unit/"
```

---

### `test-all.ps1` - 完整测试套件脚本

**功能：** 依次执行环境检查、代码质量检查、单元测试、集成测试、端到端测试、性能测试，并生成综合报告。

**使用方法：**

```powershell
# 运行完整测试套件
.\scripts\test-all.ps1

# 快速模式
.\scripts\test-all.ps1 -Quick

# 跳过性能测试
.\scripts\test-all.ps1 -SkipPerformance

# 跳过覆盖率分析
.\scripts\test-all.ps1 -SkipCoverage

# 生成 HTML 报告
.\scripts\test-all.ps1 -GenerateReport -ReportFormat html

# 生成报告并自动打开
.\scripts\test-all.ps1 -GenerateReport -OpenReport

# 快速失败模式
.\scripts\test-all.ps1 -FailFast
```

**执行步骤：**
1. ✅ 环境检查
2. 🔍 代码质量检查
3. 🧪 单元测试
4. 🎵 音频处理测试
5. 👤 用户偏好测试
6. 🎬 端到端测试
7. 📊 代码覆盖率分析（可选）
8. 🚀 性能基准测试（可选）
9. 📄 生成综合测试报告

---

### `test-coverage.ps1` - 代码覆盖率分析脚本

**功能：** 自动分析代码覆盖率，生成详细报告，标识未测试的代码区域。

**使用方法：**

```powershell
# 标准覆盖率分析
.\scripts\test-coverage.ps1

# 快速模式
.\scripts\test-coverage.ps1 -Quick

# 生成 HTML 报告
.\scripts\test-coverage.ps1 -OutputFormat html

# 生成报告并自动打开
.\scripts\test-coverage.ps1 -OpenReport

# 设置最小覆盖率阈值
.\scripts\test-coverage.ps1 -MinCoverage 85

# 低覆盖率时失败退出
.\scripts\test-coverage.ps1 -MinCoverage 80 -FailOnLow

# 详细输出
.\scripts\test-coverage.ps1 -Verbose
```

**参数说明：**
- `-OutputFormat` - 报告格式（html/json/xml/term）
- `-ReportPath` - 报告保存路径（默认：`logs/coverage_report`）
- `-MinCoverage` - 最小覆盖率阈值（默认：80.0%）
- `-FailOnLow` - 低于阈值时退出失败
- `-OpenReport` - 生成后自动打开报告

**输出报告：**
- 📊 总体覆盖率统计
- 📁 模块级覆盖率详情
- ⚠️ 未覆盖代码行标识
- 💡 覆盖率提升建议

---

### `test-performance.ps1` - 性能基准测试脚本

**功能：** 测试视频处理速度、内存使用和 AI 模型推理性能。

**使用方法：**

```powershell
# 标准性能测试
.\scripts\test-performance.ps1

# 快速模式（减少迭代次数）
.\scripts\test-performance.ps1 -Quick

# 启用内存分析
.\scripts\test-performance.ps1 -MemoryProfile

# 启用 GPU 性能分析
.\scripts\test-performance.ps1 -GPUProfile

# 自定义迭代次数
.\scripts\test-performance.ps1 -Iterations 10

# 指定测试数据路径
.\scripts\test-performance.ps1 -TestDataPath "tests/perf_data"

# 保存性能报告
.\scripts\test-performance.ps1 -ReportPath "logs/perf_report.json"

# 详细输出
.\scripts\test-performance.ps1 -Verbose
```

**测试项目：**
- 🎬 视频处理速度基准测试
- 🧠 AI 模型推理性能测试
- 💾 内存使用监控
- 🖥️ GPU 性能分析（可选）
- 📈 系统资源利用率

---

## 🔍 代码质量脚本

### `check-quality.ps1` - 代码质量检查脚本

**功能：** 集成 Black、Flake8、MyPy 进行自动化代码质量检查。

**使用方法：**

```powershell
# 运行所有质量检查
.\scripts\check-quality.ps1

# 自动修复代码格式问题
.\scripts\check-quality.ps1 -Fix

# 快速检查（跳过 MyPy 类型检查）
.\scripts\check-quality.ps1 -Quick

# 仅检查代码格式
.\scripts\check-quality.ps1 -Check format

# 仅检查代码风格
.\scripts\check-quality.ps1 -Check style

# 仅检查类型注解
.\scripts\check-quality.ps1 -Check type

# 详细输出
.\scripts\check-quality.ps1 -Verbose

# 查看帮助
.\scripts\check-quality.ps1 -Help
```

**检查项目：**
1. 📝 **代码格式检查（Black）** - 代码格式是否符合 PEP 8 规范
2. 📋 **代码风格检查（Flake8）** - 代码风格、复杂度、潜在错误
3. 🔍 **类型注解检查（MyPy）** - 类型注解的正确性和完整性

**参数说明：**
- `-Fix` - 自动修复代码格式问题（使用 Black 格式化）
- `-Quick` - 快速检查模式（跳过类型检查）
- `-Check` - 指定检查类型（all/format/style/type）
- `-Verbose` - 显示详细输出信息

---

### `check_code_quality.py` - 代码行数检查工具

**功能：** 检查 Python 文件是否符合 300 行以内的硬性指标，识别需要重构的代码。

**使用方法：**

```bash
# 检查当前目录
python scripts/check_code_quality.py

# 指定扫描路径
python scripts/check_code_quality.py --path app/

# 自定义行数限制
python scripts/check_code_quality.py --limit 250

# 详细输出（显示所有文件）
python scripts/check_code_quality.py --verbose
```

**输出报告：**
- 📊 总体统计（合规/警告/超标文件数量）
- ⚠️ 问题文件详情（超标行数、严重程度）
- 💡 优化建议（按严重程度分级）

**严重程度分级：**
- ✅ **OK** - 300 行以内
- ⚠️ **Medium** - 301-350 行
- 🔴 **High** - 351-400 行
- 💥 **Critical** - 401 行以上

---

## 🧹 维护脚本

### `clean-cache.ps1` - 缓存清理脚本

**功能：** 清除 Python 项目中的各种缓存和临时文件，释放磁盘空间。

**使用方法：**

```powershell
# 交互式清理（会询问确认）
.\scripts\clean-cache.ps1

# 跳过确认直接清理
.\scripts\clean-cache.ps1 -Force
```

**清理目标：**
- 🗑️ Python 字节码缓存（`__pycache__`、`*.pyc`、`*.pyo`）
- 🔍 MyPy 类型检查缓存（`.mypy_cache`）
- 🧪 Pytest 测试缓存（`.pytest_cache`）
- 📊 Coverage 覆盖率报告（`.coverage`、`.coverage.*`）
- 📝 日志文件（`logs/*.log`）
- 📄 测试报告（`*_test_report.json`、`*_test_report.html`）
- 🗃️ 临时文件（`*.tmp`、`*.bak`、`*.backup`、`*.cache`）

**输出信息：**
- 📋 扫描结果（文件数量、占用空间）
- ✅ 清理进度和结果
- 📊 释放空间统计

---

## 🤖 CI/CD 脚本

### `ci-test.ps1` - CI/CD 测试脚本

**功能：** 专为持续集成环境设计的无交互测试脚本，JSON 格式输出，适用于 GitHub Actions、GitLab CI 等。

**使用方法：**

```powershell
# 标准 CI 测试
.\scripts\ci-test.ps1

# 跳过性能测试
.\scripts\ci-test.ps1 -SkipPerformance

# 跳过覆盖率分析
.\scripts\ci-test.ps1 -SkipCoverage

# 设置最小覆盖率阈值
.\scripts\ci-test.ps1 -MinCoverage 85

# 输出到指定文件
.\scripts\ci-test.ps1 -OutputFile "ci-results.json"

# 保存测试产物到目录
.\scripts\ci-test.ps1 -ArtifactsDir "ci-artifacts"

# 设置超时时间（分钟）
.\scripts\ci-test.ps1 -TimeoutMinutes 45

# 详细输出
.\scripts\ci-test.ps1 -Verbose
```

**特点：**
- 🤖 无交互模式运行
- 📄 JSON 格式输出测试结果
- 🔢 返回适当的退出码（0 成功，1 失败）
- 📊 生成 CI 友好的测试报告
- ⏱️ 支持超时控制
- 📦 自动收集测试产物

**输出内容：**
- 测试结果摘要（通过/失败/跳过）
- 代码覆盖率数据
- 性能基准数据
- 错误和警告信息
- 环境信息
- 测试产物路径

---

## 📚 使用指南

### 🎯 快速开始

**1. 初次使用（环境配置）**

```powershell
# Windows
.\scripts\setup.ps1

# Linux/macOS
./scripts/setup.sh
```

**2. 运行应用**

```powershell
# 简洁启动
.\scripts\run.ps1

# 完整检查启动
.\scripts\start.ps1
```

**3. 运行测试**

```powershell
# 快速测试
.\scripts\test.ps1 unit -Quick

# 完整测试
.\scripts\test.ps1 all
```

---

### 🔄 日常开发工作流

#### 编码前 - 拉取最新代码后

```powershell
# 1. 更新依赖（如有变化）
.\scripts\setup.ps1

# 2. 运行测试确保环境正常
.\scripts\test.ps1 unit -Quick
```

#### 编码中 - 频繁检查代码质量

```powershell
# 1. 格式化代码
.\scripts\check-quality.ps1 -Fix

# 2. 运行相关模块测试
.\scripts\test.ps1 integration ai

# 3. 检查代码质量
.\scripts\check-quality.ps1
```

#### 编码后 - 提交前完整检查

```powershell
# 1. 自动修复格式问题
.\scripts\check-quality.ps1 -Fix

# 2. 完整质量检查
.\scripts\check-quality.ps1

# 3. 运行完整测试套件
.\scripts\test.ps1 all -Coverage

# 4. 检查代码行数规范
python scripts/check_code_quality.py --verbose
```

---

### 🚀 发布流程

```powershell
# 1. 运行完整测试套件
.\scripts\test-all.ps1

# 2. 检查代码覆盖率
.\scripts\test-coverage.ps1 -MinCoverage 80 -FailOnLow

# 3. 运行性能基准测试
.\scripts\test-performance.ps1

# 4. 构建发布版本
.\scripts\build.ps1

# 5. 验证发布包
cd release
.\智能水印去除工具.exe
```

---

### 🧹 项目维护

```powershell
# 定期清理缓存（释放空间）
.\scripts\clean-cache.ps1

# 检查代码行数规范
python scripts/check_code_quality.py --verbose

# 更新依赖到最新版本
.\scripts\setup.ps1
```

---

## 🆘 常见问题

### Q1: 虚拟环境激活失败？

**A:** 确保已运行环境配置脚本：

```powershell
.\scripts\setup.ps1
```

如果仍有问题，手动激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### Q2: 测试失败如何调试？

**A:** 使用 `-Verbose` 参数查看详细输出：

```powershell
.\scripts\test.ps1 unit -Verbose
```

或者直接运行 pytest：

```powershell
.\.venv\Scripts\Activate.ps1
pytest tests/ -v -s
```

---

### Q3: 代码格式检查不通过？

**A:** 使用 `-Fix` 参数自动修复：

```powershell
.\scripts\check-quality.ps1 -Fix
```

---

### Q4: 如何跳过耗时的检查？

**A:** 使用 `-Quick` 参数：

```powershell
.\scripts\test.ps1 quality -Quick
.\scripts\check-quality.ps1 -Quick
```

---

### Q5: 构建失败如何处理？

**A:** 检查步骤：

1. 确保测试通过：`.\scripts\test.ps1 all`
2. 检查依赖完整：`.\scripts\setup.ps1`
3. 查看构建日志：检查 `logs/` 目录

---

### Q6: 如何清理项目缓存？

**A:** 运行清理脚本：

```powershell
.\scripts\clean-cache.ps1 -Force
```

---

## 📊 脚本依赖关系

```
setup.ps1 (环境配置)
    ↓
run.ps1 / start.ps1 (运行应用)
    ↓
test.ps1 (测试)
    ├── check-quality.ps1 (代码质量)
    ├── run-tests.ps1 (单元测试)
    ├── test-coverage.ps1 (覆盖率)
    └── test-performance.ps1 (性能)
    ↓
test-all.ps1 (完整测试套件)
    ↓
build.ps1 (构建发布)
```

---

## 📝 版本历史

- **v0.3.0** - Phase 4 优化版本
  - 新增 `test-performance.ps1` 性能基准测试
  - 增强 `test.ps1` 参数化测试能力
  - 优化代码质量检查流程

- **v0.2.0** - Phase 3 产品化版本
  - 新增 `test-all.ps1` 完整测试套件
  - 新增 `test-coverage.ps1` 覆盖率分析
  - 新增 `ci-test.ps1` CI/CD 支持

- **v0.1.0** - 初始版本
  - 基础环境管理脚本
  - 基础测试和构建脚本

---

## 🔗 相关文档

- [项目 README](../README.md)
- [开发指南](../docs/development.md)
- [测试文档](../docs/testing.md)
- [部署指南](../docs/deployment.md)

---

## 💡 提示

1. **优先使用 `setup.ps1`** 而不是 `install.ps1`（现代化环境管理）
2. **频繁使用代码质量检查**，保持代码规范
3. **提交前运行完整测试**，确保代码质量
4. **定期清理缓存**，保持项目整洁
5. **使用 `-Help` 参数**查看脚本详细使用说明

---

**维护者：** 
**最后更新：** 2025-11-15
**版本：** v1.0
