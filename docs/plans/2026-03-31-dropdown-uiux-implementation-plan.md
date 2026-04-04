# 下拉框 UI/UX 优化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 统一优化项目中核心 `QComboBox` 的视觉层级和交互反馈，让参数面板与日志面板中的下拉框具备更强的设计感与可用性。

**Architecture:** 以全局样式入口 `src/app/config/styles/sections/combobox.py` 为主，统一调整关闭态、悬停态、聚焦态和弹出列表样式；再对高级参数面板与日志面板中的关键下拉框补充对象名、尺寸和交互细节，保证统一且稳定。

**Tech Stack:** Python 3.12、PyQt6、QSS 样式表、现有 ModernStyleManager

---

### Task 1: 梳理下拉框入口与影响范围

**Files:**
- Modify: `src/app/config/styles/sections/combobox.py`
- Modify: `src/app/ui/widgets/advanced/tabs/detection_tab.py`
- Modify: `src/app/ui/widgets/advanced/tabs/inpainting_tab.py`
- Modify: `src/app/ui/widgets/advanced/tabs/performance_tab.py`
- Modify: `src/app/ui/widgets/advanced/tabs/output_tab.py`
- Modify: `src/app/ui/components/log_panel.py`

**Step 1: 确认核心下拉框分布**

Run: `rg -n "QComboBox" "src/app/ui"`

Expected: 定位高级参数与日志面板中的主要下拉框。

**Step 2: 确认全局样式入口**

Run: `Get-Content "src/app/config/styles/sections/combobox.py"`

Expected: 明确当前全局 `QComboBox` 样式结构。

---

### Task 2: 优化全局下拉框样式

**Files:**
- Modify: `src/app/config/styles/sections/combobox.py`

**Step 1: 调整关闭态**

- 提升圆角、内边距、最小高度与边框层级。
- 添加更柔和但清晰的背景与轻阴影表达。

**Step 2: 调整 Hover / Focus 态**

- Hover 同时提升边框与背景反馈。
- Focus 增加更清晰的主色焦点表现。

**Step 3: 调整展开列表样式**

- 提升弹层边框、圆角、列表项留白。
- 区分 hover 项和选中项。

**Step 4: 运行静态验证**

Run: `python -m compileall "src/app/config/styles"`

Expected: 无语法错误。

---

### Task 3: 强化关键下拉框的组件表达

**Files:**
- Modify: `src/app/ui/widgets/advanced/tabs/detection_tab.py`
- Modify: `src/app/ui/widgets/advanced/tabs/inpainting_tab.py`
- Modify: `src/app/ui/widgets/advanced/tabs/performance_tab.py`
- Modify: `src/app/ui/widgets/advanced/tabs/output_tab.py`
- Modify: `src/app/ui/components/log_panel.py`

**Step 1: 为关键下拉框补充对象名**

- 为参数面板与日志面板中的关键 `QComboBox` 设置统一且可读的 `objectName`。

**Step 2: 调整尺寸与提示**

- 统一最小高度、最小内容长度或固定宽度策略。
- 对容易截断或语义较重的下拉框补充 tooltip。

**Step 3: 保证与现有逻辑兼容**

- 不修改当前参数绑定、信号连接和业务值映射。

---

### Task 4: 验证与回归

**Files:**
- Test: `src/app/ui/...`

**Step 1: 运行编译检查**

Run: `python -m compileall "src/app/ui"`

Expected: 无语法错误。

**Step 2: 运行已有元数据测试**

Run: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\\.venv\\Scripts\\python.exe -m pytest "tests/unit/test_pyproject_metadata.py" -q`

Expected: `5 passed`

**Step 3: 人工验收**

- 启动应用后检查参数面板与日志面板中的下拉框层级、hover、focus、弹层和选中态。
- 确认没有再次出现横向滚动恶化或文本截断明显的问题。

---

### Task 5: 更新说明与收尾

**Files:**
- Modify: `docs/plans/2026-03-31-dropdown-uiux-design.md`
- Modify: `docs/plans/2026-03-31-dropdown-uiux-implementation-plan.md`

**Step 1: 记录最终设计与实现差异**

- 若实现细节与初版方案存在偏差，补充到文档中。

**Step 2: 汇总验证结果**

- 记录 compileall 与 pytest 结果。

**Step 3: 提交代码**

Run: `git add <相关文件>`

Expected: 改动可单独提交。
