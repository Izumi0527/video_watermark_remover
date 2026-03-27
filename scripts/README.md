# scripts 目录说明（`vwr.ps1` 纯交互式入口）

本仓库的自动化脚本入口为 `.\scripts\vwr.ps1`。  
脚本仅支持 **Windows PowerShell**，并且已经调整为**纯交互式菜单模式**。

## 1. 使用方式

直接运行：

```powershell
.\scripts\vwr.ps1
```

脚本启动后会显示主菜单：

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

> 说明：旧的尾参命令形式已经移除，不再支持 `.\scripts\vwr.ps1 help/setup/run/test/...`

---

## 2. 常用操作

### 环境初始化

在菜单中选择 `1. 环境初始化`，脚本会继续询问：

- 是否安装开发依赖
- Python 版本
- Torch 后端
- 索引源（自动 / 清华镜像 / 自定义）
- 索引策略

### 启动程序

在菜单中选择 `2. 启动程序`，脚本会继续询问：

- 是否自动修复常见问题
- 是否跳过启动前检查

### 运行测试

在菜单中选择 `4. 运行测试`，脚本会继续询问：

- 测试类型：`unit / integration / all / audio / preferences / e2e / quality`
- 是否启用快速模式
- 是否附带覆盖率
- 是否附带性能测试
- 是否保存 JSON 报告

### 清理缓存与临时文件

在菜单中选择 `8. 清理缓存与临时文件`，脚本支持四种级别：

- `basic`：基础缓存与日志
- `temp`：运行期和测试期临时目录
- `all`：基础缓存 + 临时目录
- `deep`：`all` + 工具缓存

其中：

- `basic` 会清理 `.mypy_cache`、`.pytest_cache`、`.coverage*`、`logs/*.log`
- `temp` 会清理 `.cache/tmp`、`.cache/pytest`、`.cache/tests`、`.pytest_tmp`、`.tmp_*`、`tmp_*`、`pytest-cache-files-*`、`test_output`、`tests/.cache`、`tests/test_data/runtime_tmp`
- 所有级别都会递归清理 `src/` 与 `tests/` 下的 `__pycache__`、`*.pyc`、`*.pyo`
- 不会删除 `.venv`、`models`、`release`
- `deep` 还会额外清理 `.uv-cache`、`.cache/uv`、`.cache/setup-state`、`src/video_watermark_remover.egg-info`

---

## 3. LaMa TorchScript 权重

如果需要 TorchScript 版 `big-lama.pt`，可使用以下公开下载源：

```text
https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt
```

下载后可设置：

```powershell
$env:VWR_LAMA_MODEL_PATH="C:/path/to/big-lama.pt"
```

---

## 4. 提示

- 需要详细日志时，可继续使用 PowerShell 公共参数 `-Verbose`
- 若脚本提示缺少开发依赖，请重新运行脚本，并在“环境初始化”中开启“安装开发依赖”
- 若脚本提示虚拟环境不存在，请重新运行脚本，并在菜单中选择“环境初始化”
