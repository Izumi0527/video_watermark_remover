# YOLO 掩码精修 4 项参数设置说明

本文档说明 `config.ini` 的 `[YOLO]` 小节中，掩码精修相关的 4 个参数如何设置、它们的作用关系，以及常见调参思路。

适用版本：本仓库当前实现（`YOLOWatermarkDetector` 的 bbox→mask 逻辑）。

---

## 1. 这 4 个参数在哪里设置

这 4 项参数位于配置文件 `config.ini` 的 `[YOLO]` 段落中（掩码精修部分）：

```ini
[YOLO]
mask_padding_px = 4
mask_padding_ratio = 0.02
mask_padding_max = 24
mask_close_kernel = 5
```

注意事项：

- 程序运行时通常**优先使用“用户配置目录”中的 `config.ini`**，不一定是仓库根目录的 `config.ini`。
- 你可以用下面命令打印“当前实际生效的配置文件路径”：

```powershell
python -c "from app.config.config_manager import ConfigManager; print(ConfigManager.get_config_path())"
```

- 这些参数在检测器初始化时读取，修改后一般需要**重启程序**生效。

---

## 2. 这 4 个参数分别控制什么

这 4 项参数的目标是：把 YOLO 输出的检测框（bbox）转换为修复用的二值掩码（mask）时，让边界更贴合水印，避免“误伤”或“漏修”。

### 2.1 `mask_padding_px`（最小 padding，像素）

含义：对检测框在 x/y 方向扩张时的**最小扩张像素**。

特点：

- 值越大：掩码更大，漏修更少，但误伤风险更高、修复耗时更高。
- 值越小：更保守，误伤更少，但可能出现边缘残留。

建议起点：

- 文字水印、小 Logo：`2-6`
- 若素材分辨率普遍较大（如 1080p+）：可先从 `4` 起步，再配合 `mask_padding_ratio` 微调。

### 2.2 `mask_padding_ratio`（动态 padding，比例）

含义：根据检测框尺寸自适应扩张的比例项，按**每个轴方向**计算：

- 横向扩张参考 bbox 宽度
- 纵向扩张参考 bbox 高度

特点：

- 对不同分辨率、不同水印尺寸更“自适应”。
- 过大时会明显扩大掩码范围，导致误伤。

建议起点：

- `0.01-0.05`（一般从 `0.02` 起步）

### 2.3 `mask_padding_max`（最大 padding，像素上限）

含义：对扩张像素设置**上限**，防止大框被比例项扩得过大。

规则：当 `mask_padding_max > 0` 时生效；当为 `0` 时等价于“不限制上限”。

建议起点：

- 1080p 常见场景：`16-48`
- 误伤明显但又不能无限调小 ratio 时，优先用这个参数“封顶”。

### 2.4 `mask_close_kernel`（闭运算核大小）

含义：对生成的 mask 做形态学**闭运算**（Close）的核大小，用来：

- 连接相邻的断裂区域
- 填补小孔洞

规则：

- `0` 表示关闭闭运算
- 推荐使用**奇数**；如果填了偶数，程序会自动调整为下一个奇数

建议起点：

- `3 / 5 / 7`（一般从 `5` 起步）
- 若掩码出现“断裂”“镂空小洞”，可以适当增大；若误伤扩大明显，减小或置 `0`。

---

## 3. 4 项参数的组合规则（你调参时最该记住的关系）

程序对 bbox 的 padding 不是一次性用一个值，而是按“最小 + 比例 + 上限”组合：

1. 对 bbox 宽/高分别计算动态 padding：

- `dynamic_pad = round(axis_len * mask_padding_ratio)`

2. 取最小值约束：

- `pad = max(mask_padding_px, dynamic_pad)`

3. 若设置了上限（`mask_padding_max > 0`），再封顶：

- `pad = min(pad, mask_padding_max)`

4. 最后对 mask 做轻量后处理，其中闭运算由 `mask_close_kernel` 控制。

理解要点：

- `mask_padding_px` 决定“至少扩多少”，`mask_padding_ratio` 决定“随框变大时扩多少”，`mask_padding_max` 决定“最多扩多少”。
- padding 按 x/y 两个轴分别算，避免长条框在短边方向被过度扩张。

---

## 4. 常见现象与调参顺序（推荐）

### 4.1 水印边缘有残留（漏修）

优先顺序：

1. 小幅增大 `mask_padding_px`（例如 `4 → 6`）
2. 或小幅增大 `mask_padding_ratio`（例如 `0.02 → 0.03`）
3. 若残留是“断裂/小洞”导致，优先调 `mask_close_kernel`（例如 `5 → 7`）

### 4.2 误伤范围太大（把非水印区域也修了）

优先顺序：

1. 先减小 `mask_padding_ratio`（例如 `0.02 → 0.01`）
2. 再减小 `mask_padding_px`（例如 `4 → 2`）
3. 给 `mask_padding_max` 更小的上限（例如 `24 → 16`）
4. 若是闭运算导致“连接过度”，减小或关闭 `mask_close_kernel`（例如 `5 → 3` 或 `0`）

---

## 5. 右侧参数面板文案精简与横向滚动优化（本次改动说明）

现象：

- 右侧“参数设置”面板内存在较长的说明文本，容易撑宽控件，引发横向滚动条与“左右虚拟滚轮”体验。

处理方式：

- 将少量“过长说明”收敛为更短的可读文本，把细节放入控件 `tooltip`（鼠标悬停可查看）。
- 对提示 `QLabel` 启用 `WordWrap`，让文本在窄面板下自动换行。
- 对右侧滚动区域禁用横向滚动条（只保留纵向滚动），并对部分下拉框设置 `SizeAdjustPolicy`，避免因选项过长导致面板必须横向滚动。

---

如需把这 4 项掩码精修参数也放进右侧“参数设置”面板，建议再补一个“掩码精修”小组（SpinBox/DoubleSpinBox）并在应用后提示“需重启生效”，这样更符合桌面用户习惯。
