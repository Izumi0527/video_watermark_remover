# vwr.ps1 纯交互式菜单设计

## 背景

当前 `scripts/vwr.ps1` 以 `.\scripts\vwr.ps1 <command> [options]` 的 CLI 子命令形式工作。  
用户要求将其改为“纯交互式脚本”：

- 直接执行 `.\scripts\vwr.ps1` 时必须进入菜单
- 不再保留 `.\scripts\vwr.ps1 help/setup/run/test/...` 这类外部尾参命令用法
- 菜单中需新增“清除临时文件和缓存文件”能力

## 目标

把 `vwr.ps1` 调整为 Windows PowerShell 下的统一交互式入口，覆盖环境初始化、启动、质量检查、测试、覆盖率、性能、构建、缓存/临时文件清理与 CI 等常见操作。

## 设计原则

1. 保留现有业务函数
- 继续复用 `Invoke-Setup`、`Invoke-Run`、`Invoke-Quality`、`Invoke-Test`、`Invoke-Coverage`、`Invoke-Perf`、`Invoke-Build`、`Invoke-Clean`、`Invoke-CI`
- 只移除“对外 CLI 分发层”，不重写业务主体，降低回归风险

2. 纯交互入口
- 脚本启动后直接展示主菜单
- 所有参数通过 `Read-Host` 逐步询问
- 非法输入允许重试
- 支持在执行完一个动作后回到主菜单

3. 清理能力增强
- 将原 `clean` 扩展为分级清理：
  - `basic`：基础缓存与日志
  - `temp`：运行期与测试期临时目录
  - `all`：基础缓存 + 临时目录
  - `deep`：`all` + 工具缓存
- 递归删除 `__pycache__`、`*.pyc`、`*.pyo` 时改为扫描 `src/` 与 `tests/`

4. 帮助信息同步更新
- `Show-Help` 改为说明“请直接运行脚本进入菜单”
- 移除旧的 `<command> [args] [options]` 用法展示

## 菜单结构

主菜单：

1. 环境初始化
2. 启动程序
3. 代码质量检查
4. 运行测试
5. 覆盖率分析
6. 性能测试
7. 打包构建
8. 清理缓存与临时文件
9. CI 模式
H. 查看帮助
0. 退出

## 交互项

### 1. 环境初始化

- 是否安装开发依赖（默认否）
- Python 版本（默认 `3.12.10`）
- Torch 后端（默认 `auto`）
- 索引源：
  - 自动
  - 清华镜像
  - 自定义
- 索引策略（默认 `first-index`）

### 2. 启动程序

- 是否自动修复（默认是）
- 是否跳过检查（默认否）

### 3. 代码质量检查

- 检查类型：`all/format/style/type/security`
- 是否自动修复
- 是否快速模式

### 4. 运行测试

- 测试类型：`unit/integration/all/audio/preferences/e2e/quality`
- 是否快速模式
- 是否附带覆盖率
- 是否附带性能测试
- 是否保存报告

### 5. 覆盖率分析

- 最低覆盖率阈值（默认 `80`）
- 是否低于阈值即失败
- 是否打开 HTML 报告
- 是否快速模式

### 6. 性能测试

- 是否快速模式
- 迭代次数
- 是否采集内存信息
- 是否采集 GPU 信息

### 7. 打包构建

- 是否跳过构建前测试
- 是否快速模式

### 8. 清理缓存与临时文件

- 清理级别：
  - `basic`
  - `temp`
  - `all`（推荐）
  - `deep`
- 执行前确认

### 9. CI 模式

- 是否快速模式
- 是否跳过覆盖率
- 是否跳过性能测试
- 超时时间（分钟）

## 兼容性策略

- 对外不再支持 `.\scripts\vwr.ps1 help/setup/run/...`
- 如果用户仍然传入尾参，脚本仅提示“当前脚本已改为纯交互模式，请直接运行 `.\scripts\vwr.ps1`”，然后退出

## 风险与对策

### 风险 1：旧测试依赖 CLI 分发

对策：
- 新增菜单函数级测试
- 调整旧的 `help` 测试为“无参执行 + 输入 `H` / `0`”

### 风险 2：清理范围误删非缓存资源

对策：
- 显式白名单目标
- 明确排除 `.venv`、`models`、`release`
- 为不同清理级别分别建立测试

### 风险 3：菜单逻辑与业务函数耦合

对策：
- 把交互询问拆成独立小函数
- 由菜单函数负责设置脚本级状态，再调用现有 `Invoke-*` 函数

## 验证策略

1. 通过 PowerShell harness 验证：
- 无参进入主菜单
- 非法输入会重试
- 选择某项后能设置正确状态并进入对应函数

2. 通过临时目录验证：
- `clean all` 会清掉缓存和临时目录
- `clean deep` 额外清掉工具缓存
- 不会误删 `.venv` / `models` / `release`

3. 通过实际脚本调用验证：
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\vwr.ps1`
- 输入 `H` 查看帮助，再输入 `0` 退出
