# SpinBox / DoubleSpinBox UI/UX 优化设计

**日期：** 2026-04-04

**目标：** 将右侧参数面板中的 `QSpinBox / QDoubleSpinBox` 做成与下拉框一致的紧凑密度和视觉语言，降低“默认控件感”，提升参数输入的专业感与一致性。

---

## 1. 当前问题

- 右侧参数面板的数值输入控件仍然保留默认桌面控件观感。
- 与已优化过的下拉框相比，`SpinBox` 的层级感和风格一致性不足。
- 控件上下留白偏大，导致参数面板整体密度不够统一。

---

## 2. 设计方向

本次采用“**紧凑型专业参数输入控件**”方案，继续沿用 `ui-ux-pro-max` 的专业、可读、可聚焦方向：

- 关闭态：与下拉框一致的圆角、边框、背景和紧凑密度。
- Hover / Focus：提供明确的边框和焦点反馈。
- 步进按钮：保留右侧上下按钮区域，但缩小视觉体积，避免喧宾夺主。
- 一致性：`QSpinBox` 与 `QDoubleSpinBox` 在参数面板中使用同一设计语言。

---

## 3. 作用范围

- 全局样式：
  - `src/app/config/styles/sections/spinbox.py`
  - `src/app/config/styles/sections/__init__.py`
  - `src/app/config/styles/sections/controls/__init__.py`
  - `src/app/config/styles/factory.py`
  - `src/app/config/styles/manager.py`
- 参数面板控件：
  - `src/app/ui/widgets/advanced/advanced_parameters_widget.py`
  - `src/app/ui/widgets/advanced/tabs/detection_tab.py`
  - `src/app/ui/widgets/advanced/tabs/inpainting_tab.py`
  - `src/app/ui/widgets/advanced/tabs/performance_tab.py`

---

## 4. 关键决策

### 4.1 密度

- 默认参数面板 `SpinBox` 高度收敛到与当前紧凑下拉框接近。
- 缩小内部垂直 padding，保证数值内容更紧凑但不拥挤。

### 4.2 右侧步进按钮

- 保留上下步进按钮，避免影响现有桌面交互习惯。
- 按钮区使用更细的边界和更轻的 hover 反馈，避免太重。

### 4.3 焦点可见性

- 数值输入控件保留清晰的 focus 边框。
- 不做过度阴影，只强调专业工具的稳定感。

