# SpinBox / DoubleSpinBox UI/UX 优化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为高级参数面板中的 `QSpinBox / QDoubleSpinBox` 提供统一的紧凑样式和交互反馈，使其与当前下拉框视觉语言保持一致。

**Architecture:** 新增独立的 `spinbox` 样式片段，并接入现有 `StyleFactory` / `ModernStyleManager` 样式装配链；随后在高级参数面板中增加统一的 `configure_panel_spin_box()` 配置方法，覆盖所有关键数值输入控件。

**Tech Stack:** Python 3.12、PyQt6、QSS、pytest

---

### Task 1: 先写失败测试

**Files:**
- Create: `tests/unit/app/config/styles/test_spinbox_styles.py`

**Step 1: 写失败测试**

- 断言 `spinbox_styles()` 中包含目标圆角、紧凑 padding、最小高度和步进按钮宽度。

**Step 2: 运行测试确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/app/config/styles/test_spinbox_styles.py" -q`

Expected: FAIL，说明样式尚未实现。

---

### Task 2: 新增全局 SpinBox 样式片段

**Files:**
- Create: `src/app/config/styles/sections/spinbox.py`
- Modify: `src/app/config/styles/sections/__init__.py`
- Modify: `src/app/config/styles/sections/controls/__init__.py`
- Modify: `src/app/config/styles/factory.py`
- Modify: `src/app/config/styles/manager.py`

**Step 1: 实现 `spinbox_styles(colors)`**

- 覆盖 `QSpinBox` 与 `QDoubleSpinBox`
- 设置关闭态、hover、focus、disabled、上下按钮样式

**Step 2: 接入全局样式链**

- `StyleFactory` 增加 `get_spinbox_stylesheet()`
- `ModernStyleManager.get_complete_stylesheet()` 组合 spinbox 样式

---

### Task 3: 参数面板统一配置

**Files:**
- Modify: `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
- Modify: `src/app/ui/widgets/advanced/tabs/detection_tab.py`
- Modify: `src/app/ui/widgets/advanced/tabs/inpainting_tab.py`
- Modify: `src/app/ui/widgets/advanced/tabs/performance_tab.py`

**Step 1: 增加 `configure_panel_spin_box()`**

- 统一设置 objectName、最小高度、手型指针和 tooltip

**Step 2: 应用于所有参数面板数值输入控件**

- `min_area_spin`
- `mask_shrink_pixels_spin`
- `mask_tracking_interval_spin`
- `inpaint_radius_spin`
- `mixed_inpainting_area_percent_spin`
- `worker_count_spin`
- `gpu_memory_spin`
- `cache_size_spin`
- `batch_max_concurrent_files_spin`
- `batch_max_retry_count_spin`

---

### Task 4: 验证

**Files:**
- Test: `tests/unit/app/config/styles/test_spinbox_styles.py`

**Step 1: 跑新测试**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/app/config/styles/test_spinbox_styles.py" -q`

Expected: PASS

**Step 2: 跑编译检查**

Run: `python -m compileall "src/app/config/styles" "src/app/ui"`

Expected: 无语法错误

**Step 3: 跑元数据基础测试**

Run: `.\.venv\Scripts\python.exe -m pytest "tests/unit/test_pyproject_metadata.py" -q`

Expected: PASS

