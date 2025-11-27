# 智能视频水印去除工具 - 架构设计文档

**版本**: v0.3.0-refactored
**更新时间**: 2025-01-15
**作者**: 

## 📋 目录

1. [概述](#概述)
2. [架构设计原则](#架构设计原则)
3. [系统架构](#系统架构)
4. [模块设计](#模块设计)
5. [数据流设计](#数据流设计)
6. [设计模式](#设计模式)
7. [技术选型](#技术选型)
8. [扩展性设计](#扩展性设计)

---

## 概述

### 项目定位

智能视频水印去除工具是一个基于 AI 技术的桌面应用程序,旨在帮助用户智能检测和去除图片/视频中的水印。项目采用模块化架构设计,支持自动检测和手动选择两种模式,集成了多种图像修复算法。

### 核心功能

- **智能水印检测**: 基于 OpenCV 的传统图像处理方法
- **AI 图像修复**: 使用多种修复算法（TELEA、Navier-Stokes、自定义方法）
- **批量处理**: 支持队列式批量文件处理
- **音频保留**: 集成 FFmpeg 保留视频原始音频
- **用户界面**: 基于 PyQt6 的现代化 GUI

---

## 架构设计原则

### SOLID 原则

#### 1. 单一职责原则 (Single Responsibility Principle)

每个模块/类只负责一个功能领域：

```python
# ✅ 正确：职责分离
class WatermarkDetector:
    """仅负责水印检测"""
    def detect_watermark(self, image): ...

class ImageInpainter:
    """仅负责图像修复"""
    def inpaint_frame(self, image, mask): ...

class AIHandler:
    """协调检测和修复流程"""
    def __init__(self):
        self.detector = WatermarkDetector()
        self.inpainter = ImageInpainter()
```

#### 2. 开放封闭原则 (Open-Closed Principle)

通过继承和组合实现扩展,而不修改现有代码：

```python
# 基础检测器接口
class BaseDetector(ABC):
    @abstractmethod
    def detect(self, image): ...

# 扩展新的检测器
class EdgeDetector(BaseDetector):
    def detect(self, image):
        # 基于边缘检测的实现
        ...
```

#### 3. 依赖倒置原则 (Dependency Inversion Principle)

高层模块不依赖低层模块,都依赖抽象：

```python
# AIHandler 依赖抽象接口,不依赖具体实现
class AIHandler:
    def __init__(self, detector: BaseDetector, inpainter: BaseInpainter):
        self.detector = detector
        self.inpainter = inpainter
```

### 设计模式应用

- **策略模式**: 多种修复算法的选择
- **工厂模式**: 配置管理器的创建
- **观察者模式**: 信号-槽机制（PyQt6）
- **单例模式**: 配置管理、日志管理
- **组合模式**: UI 组件的组装

---

## 系统架构

### 总体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                       Presentation Layer                     │
│                        (UI 表现层)                           │
├─────────────────────────────────────────────────────────────┤
│  MainWindow  │  FilePanel  │  PreviewPanel  │  ControlPanel │
│  LogPanel    │  BatchWidget│  ParamsWidget  │  SignalHandler│
└──────────────┬──────────────────────────────────────────────┘
               │ PyQt6 Signals/Slots
┌──────────────┴──────────────────────────────────────────────┐
│                      Business Logic Layer                    │
│                        (业务逻辑层)                          │
├─────────────────────────────────────────────────────────────┤
│  VideoProcessorThread  │  AIHandler  │  PreferencesManager  │
│  StyleManager          │  ConfigManager                      │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────┴──────────────────────────────────────────────┐
│                        Core Layer                            │
│                        (核心层)                              │
├─────────────────────────────────────────────────────────────┤
│  AI Module           │  Audio Module    │  Video Module     │
│  ├─ WatermarkDetector│  ├─ FFmpegProcessor                  │
│  ├─ ImageInpainter   │                                       │
│  └─ AIHandler        │                                       │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────┴──────────────────────────────────────────────┐
│                      Infrastructure Layer                    │
│                        (基础设施层)                          │
├─────────────────────────────────────────────────────────────┤
│  ConfigManager  │  Logger  │  FileUtils  │  Validators      │
└─────────────────────────────────────────────────────────────┘
```

### 分层说明

#### 表现层 (Presentation Layer)
- **职责**: 用户界面展示和交互
- **技术**: PyQt6
- **关键组件**:
  - `MainWindow`: 主窗口，组装所有UI组件
  - `SignalHandler`: 信号处理器，分离UI和业务逻辑
  - 各种 Panel/Widget: 功能面板组件

#### 业务逻辑层 (Business Logic Layer)
- **职责**: 业务流程编排和状态管理
- **关键组件**:
  - `VideoProcessorThread`: 视频处理线程，避免UI冻结
  - `AIHandler`: AI处理协调器
  - `PreferencesManager`: 用户偏好设置管理

#### 核心层 (Core Layer)
- **职责**: 核心功能实现
- **模块划分**:
  - `ai/`: 水印检测和图像修复
  - `audio/`: 音频处理（FFmpeg）
  - `video/`: 视频编解码

#### 基础设施层 (Infrastructure Layer)
- **职责**: 通用工具和配置管理
- **关键组件**:
  - `ConfigManager`: 配置文件管理
  - `Logger`: 日志系统
  - 各种工具类和验证器

---

## 模块设计

### 核心模块 (app/core/)

#### AI 模块 (app/core/ai/)

**WatermarkDetector (水印检测器)**

```python
class WatermarkDetector:
    """
    水印检测器 - 负责检测图像中的水印区域

    检测方法:
    1. 灰度转换
    2. 边缘检测 (Canny)
    3. 形态学操作 (膨胀、闭运算)
    4. 轮廓检测
    5. 区域筛选
    """

    def detect_watermark(self, image: np.ndarray,
                        sensitivity: float = 0.5) -> Optional[np.ndarray]:
        """检测水印区域，返回二值掩码"""
        ...
```

**常量提取** (Phase 2 重构):
```python
# 常量定义在模块级别，便于调整和测试
EDGE_THRESHOLD_LOW = 50
EDGE_THRESHOLD_HIGH = 150
MORPH_KERNEL_SIZE = 5
MIN_CONTOUR_AREA = 100
MAX_CONTOUR_AREA_RATIO = 0.5
```

**ImageInpainter (图像修复器)**

```python
class ImageInpainter:
    """
    图像修复器 - 根据掩码修复图像

    修复算法:
    1. TELEA (快速，适合小区域)
    2. Navier-Stokes (高质量，适合大区域)
    3. Custom (自定义方法，适合超小区域)
    """

    def inpaint_frame(self, image: np.ndarray,
                     mask: np.ndarray) -> np.ndarray:
        """根据mask修复图像"""
        ...
```

**算法选择策略**:
```python
# 根据mask面积自动选择算法
mask_area_ratio = np.sum(mask > 0) / (mask.shape[0] * mask.shape[1])

if mask_area_ratio < SMALL_AREA_THRESHOLD:    # < 5%
    method = CUSTOM_METHOD
elif mask_area_ratio < MEDIUM_AREA_THRESHOLD: # 5% - 15%
    method = cv2.INPAINT_TELEA
else:                                          # > 15%
    method = cv2.INPAINT_NS
```

**AIHandler (AI 处理协调器)**

```python
class AIHandler:
    """
    AI处理协调器 - 协调检测和修复流程

    职责:
    1. 加载AI模型
    2. 协调 WatermarkDetector 和 ImageInpainter
    3. 处理用户手动选择的mask
    4. 返回处理结果和元数据
    """

    def process_frame(self, frame: np.ndarray,
                     params: Dict[str, Any]) -> Tuple[np.ndarray, Dict]:
        """处理单帧，支持自动检测和手动mask"""
        ...
```

#### 音频模块 (app/core/audio/)

**FFmpegAudioProcessor**

```python
class FFmpegAudioProcessor:
    """
    FFmpeg音频处理器

    功能:
    1. 检测FFmpeg可用性
    2. 从原视频提取音频
    3. 合并处理后的视频和原音频
    """

    def process_video_with_audio_preservation(
        self,
        original_video_path: str,
        processed_video_path: str,
        final_output_path: str
    ) -> bool:
        """保留音频的视频处理"""
        ...
```

#### 视频模块 (app/core/video/)

**VideoProcessorThread**

```python
class VideoProcessorThread(QThread):
    """
    视频处理线程 - 在独立线程中处理视频

    信号:
    - progress: 进度更新 (0-100)
    - status: 状态消息
    - finished: 处理完成
    - error: 错误消息
    - preview_update: 预览帧更新
    """

    def run(self):
        """主处理循环"""
        if file_is_image:
            self._process_image()
        else:
            self._process_video()
```

### UI 模块 (app/ui/)

#### 主窗口 (main_window.py)

```python
class MainWindow(QMainWindow):
    """
    主窗口 - 组装所有UI组件

    组件:
    - file_panel: 文件操作面板
    - preview_panel: 预览面板
    - control_panel: 控制面板
    - log_panel: 日志面板
    - signal_handler: 信号处理器
    """
```

#### 信号处理器 (signal_handler.py)

```python
class SignalHandler(QObject):
    """
    信号处理器 - 分离UI和业务逻辑

    设计模式: 组合模式
    优点:
    1. MainWindow职责单一,只负责UI组装
    2. 业务逻辑集中管理
    3. 便于测试
    """

    def handle_import_file(self, parent_widget): ...
    def handle_start_processing(self): ...
    def handle_theme_toggle(self, callback): ...
```

### 配置模块 (app/config/)

**ConfigManager**

```python
class ConfigManager:
    """
    配置管理器 - 单例模式

    功能:
    1. 加载配置文件
    2. 保存配置变更
    3. 提供默认配置
    4. 验证配置合法性
    """

    @staticmethod
    def load_config(config_path: Optional[str] = None) -> ConfigParser:
        """加载配置文件,不存在则创建默认配置"""
        ...
```

---

## 数据流设计

### 图像处理数据流

```
用户导入文件
    ↓
FilePanel (UI)
    ↓ (emit signal)
SignalHandler.handle_import_file()
    ↓
PreviewPanel.set_image() → 显示预览
    ↓
用户点击"开始处理"
    ↓
SignalHandler.handle_start_processing()
    ↓
VideoProcessorThread.start()
    ↓
读取图像 (cv2.imread)
    ↓
AIHandler.process_frame()
    ├─ WatermarkDetector.detect_watermark() → mask
    └─ ImageInpainter.inpaint_frame(image, mask) → result
    ↓
保存处理结果 (cv2.imwrite)
    ↓
emit finished signal
    ↓
UI 更新显示结果
```

### 视频处理数据流

```
VideoProcessorThread.run()
    ↓
打开视频 (cv2.VideoCapture)
    ↓
创建输出 (cv2.VideoWriter)
    ↓
逐帧处理循环:
    ├─ cap.read() → frame
    ├─ AIHandler.process_frame(frame) → processed_frame
    ├─ out.write(processed_frame)
    ├─ emit progress signal
    └─ (每30帧) emit preview_update signal
    ↓
释放资源 (cap.release, out.release)
    ↓
FFmpegAudioProcessor.process_video_with_audio_preservation()
    ├─ 提取原视频音频轨
    ├─ 合并处理后视频和原音频
    └─ 输出最终文件
    ↓
emit finished signal
```

### 配置数据流

```
应用启动
    ↓
ConfigManager.load_config()
    ├─ 检查配置文件是否存在
    ├─ 存在: 读取并解析
    └─ 不存在: 创建默认配置
    ↓
MainWindow.__init__(config)
    ↓
各组件读取配置初始化
    ↓
用户修改设置
    ↓
SignalHandler处理设置变更
    ↓
PreferencesManager.set_preference()
    ↓
ConfigManager.save_config()
```

---

## 设计模式

### 策略模式 (Strategy Pattern)

**应用场景**: 图像修复算法选择

```python
class InpaintStrategy(ABC):
    @abstractmethod
    def inpaint(self, image, mask): ...

class TeleaStrategy(InpaintStrategy):
    def inpaint(self, image, mask):
        return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)

class NSStrategy(InpaintStrategy):
    def inpaint(self, image, mask):
        return cv2.inpaint(image, mask, 3, cv2.INPAINT_NS)
```

### 观察者模式 (Observer Pattern)

**应用场景**: PyQt6 信号-槽机制

```python
class VideoProcessorThread(QThread):
    progress = pyqtSignal(int)   # 被观察者
    status = pyqtSignal(str)
    finished = pyqtSignal(str)

class ControlPanel(QWidget):
    def __init__(self):
        # 观察者订阅信号
        self.processor.progress.connect(self.update_progress)
        self.processor.status.connect(self.update_status)
```

### 工厂模式 (Factory Pattern)

**应用场景**: 配置管理器创建

```python
class ConfigFactory:
    @staticmethod
    def create_config(config_type: str) -> ConfigParser:
        if config_type == "default":
            return ConfigManager.load_config()
        elif config_type == "custom":
            return ConfigManager.load_config(custom_path)
```

### 单例模式 (Singleton Pattern)

**应用场景**: 日志管理器

```python
class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

---

## 技术选型

### GUI 框架: PyQt6

**选择理由**:
- ✅ 跨平台支持 (Windows/Linux/macOS)
- ✅ 丰富的UI组件
- ✅ 信号-槽机制优雅
- ✅ 良好的文档和社区支持
- ✅ 高性能,适合桌面应用

**替代方案**:
- Tkinter: 功能较弱,不适合复杂UI
- wxPython: 社区较小
- Kivy: 更适合移动应用

### 图像处理: OpenCV

**选择理由**:
- ✅ 计算机视觉领域标准库
- ✅ 高性能 C++ 实现
- ✅ 丰富的图像处理算法
- ✅ Python 绑定完善

**核心算法**:
- `cv2.Canny()`: 边缘检测
- `cv2.morphologyEx()`: 形态学操作
- `cv2.findContours()`: 轮廓检测
- `cv2.inpaint()`: 图像修复

### 音视频处理: FFmpeg

**选择理由**:
- ✅ 行业标准的音视频处理工具
- ✅ 支持几乎所有格式
- ✅ 命令行调用简单
- ✅ 高性能,稳定可靠

**使用方式**:
```bash
# 提取音频
ffmpeg -i input.mp4 -vn -acodec copy audio.aac

# 合并视频和音频
ffmpeg -i video_no_audio.mp4 -i audio.aac -c:v copy -c:a aac output.mp4
```

### 配置管理: ConfigParser

**选择理由**:
- ✅ Python 标准库,无额外依赖
- ✅ INI 格式人类可读
- ✅ 支持分节 (sections)
- ✅ 简单易用

**配置文件示例**:
```ini
[processing]
default_detection_sensitivity = 0.5
default_inpainting_method = auto

[ui]
theme = dark
window_width = 1400
```

---

## 扩展性设计

### 检测算法扩展

**步骤**:
1. 继承 `BaseDetector` 抽象类
2. 实现 `detect()` 方法
3. 在 `AIHandler` 中注册新检测器

**示例**:
```python
class DeepLearningDetector(BaseDetector):
    def detect(self, image):
        # 使用深度学习模型检测
        model = load_model("watermark_detector.pth")
        mask = model.predict(image)
        return mask
```

### 修复算法扩展

**步骤**:
1. 在 `ImageInpainter` 中添加新方法
2. 更新算法选择逻辑
3. 在UI中添加新选项

**示例**:
```python
def _gan_inpaint(self, image, mask):
    """基于GAN的图像修复"""
    generator = load_model("inpainting_gan.pth")
    result = generator(image, mask)
    return result
```

### UI 组件扩展

**步骤**:
1. 在 `app/ui/widgets/` 创建新组件
2. 继承 `QWidget` 或其他PyQt6组件
3. 在 `MainWindow` 中集成

**示例**:
```python
# app/ui/widgets/advanced/histogram_widget.py
class HistogramWidget(QWidget):
    """图像直方图显示组件"""
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def update_histogram(self, image):
        # 计算并显示直方图
        ...
```

### 插件系统设计

**未来扩展方向**:

```python
# app/core/plugins/plugin_manager.py
class PluginManager:
    """插件管理器"""

    def __init__(self):
        self.plugins = {}

    def load_plugin(self, plugin_path):
        """动态加载插件"""
        ...

    def register_detector(self, name, detector_class):
        """注册检测器插件"""
        ...
```

---

## 性能优化

### 多线程处理

```python
# 避免UI冻结
class VideoProcessorThread(QThread):
    def run(self):
        # 在独立线程中执行耗时操作
        for frame in video:
            processed = self.ai_handler.process_frame(frame)
            self.progress.emit(current / total * 100)
```

### 批处理优化

```python
# 队列式批处理，避免内存溢出
class BatchProcessor:
    def process_batch(self, files, max_concurrent=3):
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(self.process_file, f) for f in files]
            for future in as_completed(futures):
                result = future.result()
                yield result
```

### 缓存优化

```python
# 缓存常用计算结果
@lru_cache(maxsize=128)
def get_default_config(section, key):
    return DEFAULT_CONFIG[section][key]
```

---

## 安全性考虑

### 文件路径验证

```python
def validate_file_path(file_path: str) -> bool:
    """验证文件路径安全性"""
    # 防止路径遍历攻击
    if ".." in file_path:
        return False

    # 检查文件扩展名
    allowed_extensions = [".mp4", ".avi", ".jpg", ".png"]
    if not any(file_path.endswith(ext) for ext in allowed_extensions):
        return False

    return True
```

### FFmpeg 命令注入防护

```python
def build_ffmpeg_command(input_file, output_file):
    """构建FFmpeg命令，防止命令注入"""
    # 使用列表形式，避免shell注入
    cmd = [
        "ffmpeg",
        "-i", shlex.quote(input_file),
        "-i", shlex.quote(audio_file),
        "-c:v", "copy",
        "-c:a", "aac",
        shlex.quote(output_file)
    ]
    return cmd
```

---

## 总结

本架构设计遵循以下核心原则：

1. **模块化**: 清晰的模块边界,职责分离
2. **可测试性**: 依赖注入,便于单元测试
3. **可扩展性**: 插件化设计,易于功能扩展
4. **可维护性**: SOLID原则,设计模式应用
5. **性能**: 多线程,批处理,缓存优化
6. **安全性**: 输入验证,防止注入攻击

**下一步计划**:
- [ ] 引入深度学习检测模型
- [ ] 实现插件系统
- [ ] GPU加速支持
- [ ] 分布式批处理

---

**相关文档**:
- [API 接口文档](api.md)
- [测试文档](testing.md)
- [开发指南](development.md)
