# 四类场景检测参数推荐

## 文档说明

本文档整理了 4 类常见素材的检测参数建议，目标是提供一套可以直接照抄的起始配置。

- 适用版本：`v0.6.0`
- 更新日期：`2026-03-23`
- 适用范围：当前项目的 `YOLO boxes -> mask` 检测后处理链路

本建议基于当前代码中的真实生效参数整理，主要覆盖：

- `检测敏感度` -> `conf_threshold`
- `检测方法` -> `device`
- `最小检测区域` -> `min_area_pixels`
- `启用高斯模糊预处理`
- `启用锐化预处理`
- `启用降噪预处理`

另外，文档也附带了 `config.ini` 的 `[YOLO]` 细调建议，适合需要进一步微调检测边界的人使用。

## 参数真实含义

### 1. 检测敏感度

当前实现里，`检测敏感度` 实际映射到 `conf_threshold`。

- 调大：阈值更高，检测更严格，误检更少，漏检更多
- 调小：阈值更低，检测更宽松，漏检更少，误检更多

### 2. 检测方法

当前实现里，`检测方法` 本质是设备选择。

- `YOLO v11x 深度学习auto (推荐)`：优先 GPU，失败自动回退 CPU，最稳
- `YOLO v11x GPU 加速`：速度最快，但环境要求最高
- `YOLO v11x CPU 模式`：最稳、最慢

这项主要影响速度和稳定性，通常不改变检测逻辑本身。

### 3. 最小检测区域

当前实现里，`最小检测区域` 已经真正接入 `YOLO boxes -> mask` 后处理。

- 调大：更容易过滤小噪点、小误检，但会漏掉小水印、小字
- 调小：更容易抓到小角标、小字，但误检会增多

说明：当前这项主要作用在 `boxes -> mask` 路径；如果未来切到真正的 segmentation masks 模型，还需要再补一版对应过滤逻辑。

### 4. 三个预处理开关

- `启用高斯模糊预处理`
  - 开：更适合压缩噪声重、块状伪影多的素材
  - 关：更保留细节，适合边缘本来就弱的小水印
- `启用锐化预处理`
  - 开：有利于增强字幕描边、Logo 边缘
  - 关：更稳，避免把噪声也一起放大
- `启用降噪预处理`
  - 开：适合高压缩、噪点多的素材
  - 关：适合本来就比较干净的素材

## 四类场景推荐

下面每套都分成两层：

- `UI`：软件界面里可以直接照抄的参数
- `config.ini [YOLO]`：可选的进阶细调

如果只是先快速试，优先照抄 `UI` 部分即可。

## 1. 透明角标水印

```yaml
UI:
  检测敏感度: 0.24
  检测方法: "YOLO v11x 深度学习auto (推荐)"
  最小检测区域: 64
  启用高斯模糊预处理: false
  启用锐化预处理: true
  启用降噪预处理: true

config.ini [YOLO]:
  iou_threshold: 0.45
  mask_padding_px: 3
  mask_padding_ratio: 0.03
  mask_padding_max: 18
  mask_erode_iterations: 0
  mask_dilate_iterations: 1
  mask_close_kernel: 3
```

适用判断：

- 水印半透明
- 面积偏小
- 边缘偏淡、容易漏检

推荐思路：

- `检测敏感度` 偏低，优先保召回
- `最小检测区域` 不能设太大，否则容易把小角标直接滤掉
- `锐化 + 降噪` 组合用于拉起弱边缘，同时压掉一部分脏噪点

## 2. 白色字幕样水印

```yaml
UI:
  检测敏感度: 0.28
  检测方法: "YOLO v11x 深度学习auto (推荐)"
  最小检测区域: 36
  启用高斯模糊预处理: false
  启用锐化预处理: true
  启用降噪预处理: true

config.ini [YOLO]:
  iou_threshold: 0.50
  mask_padding_px: 2
  mask_padding_ratio: 0.01
  mask_padding_max: 10
  mask_erode_iterations: 0
  mask_dilate_iterations: 1
  mask_close_kernel: 7
```

适用判断：

- 水印长得像白字字幕、条幅字、角落文字提示
- 容易碎、细、亮
- 最怕漏掉细字或只框住部分字块

推荐思路：

- `最小检测区域` 要偏低，否则细字很容易被过滤
- `mask_close_kernel` 要比普通 Logo 更大，便于把断开的字块连起来
- `锐化 + 降噪` 更适合这类边缘清晰但碎片化的目标

## 3. 右上角 Logo

```yaml
UI:
  检测敏感度: 0.52
  检测方法: "YOLO v11x 深度学习auto (推荐)"
  最小检测区域: 180
  启用高斯模糊预处理: false
  启用锐化预处理: false
  启用降噪预处理: false

config.ini [YOLO]:
  iou_threshold: 0.45
  mask_padding_px: 4
  mask_padding_ratio: 0.02
  mask_padding_max: 20
  mask_erode_iterations: 0
  mask_dilate_iterations: 0
  mask_close_kernel: 3
```

适用判断：

- 角标 Logo 边界清楚
- 对比度高
- 位置稳定

推荐思路：

- `检测敏感度` 可以设高一点，优先压误检
- `最小检测区域` 可以设高一点，过滤掉无关小块
- 这类素材一般不需要额外预处理

## 4. 高压缩短视频

```yaml
UI:
  检测敏感度: 0.34
  检测方法: "YOLO v11x 深度学习auto (推荐)"
  最小检测区域: 160
  启用高斯模糊预处理: true
  启用锐化预处理: false
  启用降噪预处理: true

config.ini [YOLO]:
  iou_threshold: 0.40
  mask_padding_px: 4
  mask_padding_ratio: 0.02
  mask_padding_max: 16
  mask_erode_iterations: 0
  mask_dilate_iterations: 1
  mask_close_kernel: 5
```

适用判断：

- 平台二压明显
- 块效应重
- 噪点多、边缘发脏

推荐思路：

- `降噪 + 模糊` 优先，先压掉压缩噪声
- `锐化` 默认不要开，否则容易把脏边和噪点一起放大
- `最小检测区域` 适当抬高，先砍掉大量微小噪点框

## 快速调参规则

如果是下面这些情况，优先这样调：

- 完全检不出来：先降低 `检测敏感度`
- 总是框出很多小噪点：先提高 `最小检测区域`
- 框到了，但边缘还留一圈：先加 `mask_padding_px` 或 `mask_dilate_iterations`
- 修得太大，误伤正文或人物边缘：先降 `mask_padding_ratio`，再加一点 `mask_erode_iterations`
- 字幕样水印一段一段断开：优先增大 `mask_close_kernel`
- 高压缩素材越锐化越乱：把 `启用锐化预处理` 关掉，只保留降噪和模糊

## 进阶细调参数说明

如果需要继续调 `config.ini` 的 `[YOLO]`，可以重点关注这几项：

- `iou_threshold`
  - 调大：更容易保留重叠框
  - 调小：NMS 更强，重叠框更容易被合并
- `mask_padding_px`
  - 调大：整体向外扩更多，减少残边
  - 调小：更贴边，但更容易留边
- `mask_padding_ratio`
  - 调大：大框扩张更明显
  - 调小：整体更克制
- `mask_padding_max`
  - 调大：允许大框继续扩张
  - 调小：限制过度扩张
- `mask_erode_iterations`
  - 调大：掩码收缩，误伤更少，但更容易留残边
- `mask_dilate_iterations`
  - 调大：掩码膨胀，残边更少，但更容易修大了
- `mask_close_kernel`
  - 调大：更容易连通邻近小块、填小孔
  - 调小：更不容易把无关区域粘在一起

## 边界说明

- 当前 `最小检测区域` 已经作用于主路径 `boxes -> mask`
- 当前没有把同样的最小面积过滤同步到 `segmentation masks` 分支
- 本文档的推荐值是“可靠起步值”，不是所有素材的唯一最优值
- 实际调参时，建议优先改 `检测敏感度` 和 `最小检测区域`，再改 `mask_padding_*`
