# 日志工具栏控件紧凑化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收紧日志面板工具栏中的下拉框和操作按钮尺寸，让顶部日志操作区域更轻、更紧凑。

**Architecture:** 通过局部修改 `log_panel.py` 中的控件尺寸，以及在 `buttons.py` 中为日志按钮单独定义更紧凑的样式规则，实现中度缩小且不影响其他按钮。

**Tech Stack:** Python 3.12、PyQt6、QSS、pytest

---

### Task 1: 写失败测试

**Files:**
- Create: `tests/unit/app/config/styles/test_log_toolbar_button_styles.py`

**Step 1: 写失败测试**

- 断言 `btn_clear_log / btn_save_log` 具有更紧凑的 padding 和较小的最小高度。

**Step 2: 跑测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/app/config/styles/test_log_toolbar_button_styles.py" -q`

Expected: FAIL

---

### Task 2: 缩小日志工具栏按钮

**Files:**
- Modify: `src/app/config/styles/sections/buttons.py`

**Step 1: 为日志按钮单独定义样式**

- `btn_clear_log`
- `btn_save_log`

**Step 2: 收紧 padding / min-height / 圆角**

---

### Task 3: 缩小日志级别下拉框和按钮实际尺寸

**Files:**
- Modify: `src/app/ui/components/log_panel.py`

**Step 1: 下调日志级别下拉框高度与宽度**

**Step 2: 下调清空 / 保存按钮宽度与高度**

---

### Task 4: 验证

**Step 1: 跑新测试**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/app/config/styles/test_log_toolbar_button_styles.py" -q`

Expected: PASS

**Step 2: 跑编译检查**

Run: `python -m compileall "src/app/config/styles" "src/app/ui"`

Expected: 无语法错误

**Step 3: 跑元数据测试**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/test_pyproject_metadata.py" -q`

Expected: PASS

