# Lint 检查报告（2025-11-27 更新）

> 说明：本文件作为待办清单使用，不纳入提交（请保持未暂存状态）。

## 本轮执行
- 已跑 `pre-commit run --all-files`（失败，见下）。
- black/isort 自动修改：`tests/unit/test_config_and_utils_robustness.py`（black），`app/config/config_manager.py`、`app/core/ai/dl_inpainter.py`、`app/core/video/pipeline_processor.py`、`app/ui/widgets/image_selector_widget.py`（isort）。
- trailing-whitespace 钩子已批量清理 docs/tests 行尾空格。

## mypy
- 命令行 `python -m mypy app`：本地通过。
- pre-commit 钩子失败 1 条：`app/core/ai/yolo_detector.py:170` Unused \"type: ignore\" comment。

## flake8（当前失败，主要在 tests/scripts）
- `app/core/video/pipeline_processor.py`：psutil 未用 + 重复定义（isort 产生）。
- `scripts/check_code_quality.py`：未用导入（os、Tuple），F541，E226 多处。
- tests 目录：大量 F401/F811/F841/W291/E226/E402/C901 等（未用导入/变量、重复定义、行尾空格、导入顺序、复杂度）。

## Bandit（当前失败）
- B110 try/except/pass：
  - `app/core/video/chunk_worker.py:108`
  - `app/core/video/frame_processor.py:72`
  - `app/core/video/frame_writer.py:90`
  - `app/core/video/pipeline_processor.py:309`
  - `app/ui/widgets/advanced/advanced_parameters_widget.py:403`
- B310 urlretrieve：`app/utils/model_downloader.py:129`（需 URL 校验或风险说明）。

## 已完成
- flake8 主干代码已通过（docstring 规则在 `.flake8` 中忽略）。
- mypy 主干代码已 0 报错；psutil/队列/VideoCapture ignore、AI/UI 类型问题已修复。

## 待办优先级
1. mypy 钩子：移除 `yolo_detector.py:170` 未使用 ignore。
2. flake8：修复 pipeline_processor psutil 导入；`scripts/check_code_quality.py` 清理未用导入/F541/E226；tests 目录批量清理（未用导入/变量、E402、E226、W291，必要时测试入口加 `# noqa: C901`）。
3. Bandit：try/except/pass 改为日志或 `# nosec`；`urlretrieve` 增加校验或注明风险（或替换下载方案）。
4. 重新跑 `pre-commit run --all-files` 直至通过，再提交。
