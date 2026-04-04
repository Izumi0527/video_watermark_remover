# 下拉框紧凑密度优化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收紧下拉框关闭态与展开列表的上下留白，让参数面板中的选择控件更紧凑、更适合高密度桌面工具界面。

**Architecture:** 以全局 `QComboBox` QSS 作为主修改入口，通过统一减少关闭态 padding、列表项 padding 和最小高度来改变整体密度；同时下调参数面板与日志面板关键下拉框的 `minimumHeight`，保证视觉与真实控件尺寸同步收紧。

**Tech Stack:** Python 3.12、PyQt6、QSS 样式、pytest

---

### Task 1: 先写失败测试锁定紧凑密度目标

**Files:**
- Create: `tests/unit/app/config/styles/test_combobox_density.py`

**Step 1: 写一个失败测试**

- 断言 `combobox_styles()` 生成的样式已经包含更紧凑的垂直 padding、最小高度和列表项高度。

**Step 2: 跑测试并确认红灯**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/app/config/styles/test_combobox_density.py" -q`

Expected: FAIL，说明当前样式还没有达到目标紧凑度。

---

### Task 2: 修改全局下拉框样式

**Files:**
- Modify: `src/app/config/styles/sections/combobox.py`

**Step 1: 收紧关闭态**

- 降低 `QComboBox` 的垂直 padding 与 `min-height`
- 同步调整 focus 态 padding，避免切换焦点时尺寸跳动

**Step 2: 收紧展开列表**

- 降低列表容器 padding
- 降低列表项上下 padding 与 `min-height`

**Step 3: 收紧箭头区域**

- 缩小 `QComboBox::drop-down` 上下 margin

---

### Task 3: 同步关键控件最小高度

**Files:**
- Modify: `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- Modify: `src/app/ui/components/log_panel.py`

**Step 1: 参数面板默认下拉框高度下调**

- 将 `configure_panel_combo_box()` 的默认 `minimum_height` 下调到更紧凑的值

**Step 2: 日志面板紧凑下拉框高度下调**

- 将日志级别下拉框高度同步下调

---

### Task 4: 运行验证

**Files:**
- Test: `tests/unit/app/config/styles/test_combobox_density.py`

**Step 1: 跑新测试**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/app/config/styles/test_combobox_density.py" -q`

Expected: PASS

**Step 2: 跑现有基础样式测试**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/app/config/styles/test_styles_package.py" -q`

Expected: PASS

**Step 3: 跑编译检查**

Run: `python -m compileall "src/app/config/styles" "src/app/ui"`

Expected: 无语法错误

