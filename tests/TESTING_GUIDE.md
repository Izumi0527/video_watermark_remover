# 测试执行指南（主分层版）

本文档说明当前 `tests/` 的主分层约定，以及如何按层级执行测试。

## 当前测试分层
- `tests/unit/`：单元测试，覆盖局部模块行为、导入边界与轻量健壮性校验。
- `tests/integration/`：集成测试，覆盖 AI / 视频 / UI / `legacy_phase3` 等跨模块协作场景。
- `tests/e2e/ps1/`：PowerShell 端到端脚本，覆盖命令行与真实工作流。
- `tests/future/unit/`：暂挂或未来阶段测试，不属于当前默认门禁。

## 环境准备
1. Python 3.10/3.11（建议直接使用项目自带 `.venv`）。
2. 安装开发依赖（包含 `pytest`、格式化与静态检查工具）：
   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   ```

## 推荐运行方式
1. 运行单元层：
   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/unit -q
   ```
2. 运行集成层：
   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/integration -q
   ```
3. 运行端到端脚本：
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1" test e2e
   ```
4. 使用统一脚本入口：
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1" test unit -Quick
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\vwr.ps1" test integration -Quick
   ```

## 常用定向命令
1. 配置/工具健壮性：
   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/unit/test_config_and_utils_robustness.py -v
   ```
2. 语法烟囱（`py_compile`，不触发真实依赖加载）：
   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/unit/test_module_syntax_smoke.py -v
   ```
3. 本轮目录标准化后的关键验证：
   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/unit/core/ai/video/test_video_module_split.py -q
   .\.venv\Scripts\python.exe -m pytest tests/integration/core/ai/video/test_video_modes.py -q
   .\.venv\Scripts\python.exe -m pytest tests/integration/legacy_phase3/test_phase3.py -q
   ```

## 说明与注意事项
- 默认优先按主分层执行，不再使用 `tests/app/`、`tests/core/` 或根目录散落入口。
- 语法烟囱仅校验语法，不会真正导入 `PyQt6`、`torch`、`cv2` 等重依赖，适合在依赖未完整安装时做前置检查。
- 健壮性测试使用 `tmp_path` 与 `monkeypatch`，不会写入真实用户目录；如需写入运行目录，优先落到仓库内 `.cache/`。
- 若需结合 GPU / 重型依赖测试，请先完整安装生产依赖，再运行相应集成测试或 `scripts/` 下脚本。
