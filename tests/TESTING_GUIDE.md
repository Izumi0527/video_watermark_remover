# 单元测试执行指南（本地快速版）

本文档说明如何运行新增的健壮性与语法烟囱测试，帮助快速发现 VSCode/Pylance 可见的语法问题与常见健壮性回归。

## 环境准备
1. Python 3.10/3.11（建议使用项目自带 `.venv`）
2. 安装开发依赖（包含 pytest、lint 工具）：
   ```powershell
   pwsh -NoProfile -Command "pip install -r requirements-dev.txt"
   ```

## 只运行新增测试
1. 配置/工具健壮性（目录、配置修复、日志初始化等）：
   ```powershell
   pwsh -NoProfile -Command "pytest tests/unit/test_config_and_utils_robustness.py -v"
   ```
2. 语法烟囱（py_compile，不触发实际依赖加载）：
   ```powershell
   pwsh -NoProfile -Command "pytest tests/unit/test_module_syntax_smoke.py -v"
   ```

## 完整测试套件
```powershell
pwsh -NoProfile -Command "pytest tests -v"
```

## 说明与注意事项
- 新增烟囱测试使用 `py_compile`，仅校验语法，不会真正导入 PyQt6/torch/cv2，适合在依赖未完全安装时提前发现编辑器可见的语法错误。
- 健壮性测试使用 `tmp_path` 与 `monkeypatch`，不会写入真实用户目录；日志测试会在临时目录生成 `logs/watermark_remover_*.log`，pytest 结束后自动清理。
- 若需结合 GPU/重型依赖测试，请先完整安装生产依赖并使用已有的集成/性能测试脚本（参考项目 README 与 `scripts/`）。 
