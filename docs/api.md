# 智能视频水印去除工具 - API 接口文档

**版本**: v0.3.0-refactored
**更新时间**: 2025-01-15
**作者**: 

## 📋 目录

1. [核心模块 API](#核心模块-api)
2. [UI 模块 API](#ui-模块-api)
3. [配置模块 API](#配置模块-api)
4. [工具模块 API](#工具模块-api)
5. [类型定义](#类型定义)
6. [使用示例](#使用示例)

---

## 核心模块 API

### WatermarkDetector (水印检测器)

**模块路径**: `app.core.ai.watermark_detector`

#### 类定义

```python
class WatermarkDetector:
    """
    水印检测器 - 基于OpenCV的传统图像处理方法检测水印区域

    属性:
        config (Optional[ConfigParser]): 配置对象
        logger (logging.Logger): 日志记录器
        detection_model (Optional[str]): 检测模型名称
    """
```

#### 构造函数

```python
def __init__(self, config: Optional[ConfigParser] = None) -> None:
    """
    初始化水印检测器

    参数:
        config: 配置对象（可选）

    示例:
        >>> detector = WatermarkDetector()
        >>> detector_with_config = WatermarkDetector(config)
    """
```

#### 核心方法

##### load_model()

```python
def load_model(self) -> bool:
    """
    加载检测模型

    返回:
        bool: 成功返回True，失败返回False

    说明:
        当前使用OpenCV传统方法，未来可扩展深度学习模型

    示例:
        >>> detector = WatermarkDetector()
        >>> success = detector.load_model()
        >>> assert success is True
    """
```

##### detect_watermark()

```python
def detect_watermark(
    self,
    image: np.ndarray,
    sensitivity: float = 0.5
) -> Optional[np.ndarray]:
    """
    检测图像中的水印区域

    参数:
        image: 输入图像（BGR格式，numpy数组）
        sensitivity: 检测敏感度 (0.0-1.0)
            - 0.0: 最不敏感，只检测明显的水印
            - 0.5: 中等敏感度（默认）
            - 1.0: 最敏感，可能产生误检

    返回:
        Optional[np.ndarray]: 二值掩码（0/255），None表示检测失败

    异常:
        ValueError: 如果image为空或格式不正确
        RuntimeError: 如果检测过程出错

    检测流程:
        1. 灰度转换
        2. 边缘检测 (Canny)
        3. 形态学操作（膨胀、闭运算）
        4. 轮廓检测和筛选
        5. 生成二值掩码

    示例:
        >>> import cv2
        >>> image = cv2.imread("input.jpg")
        >>> detector = WatermarkDetector()
        >>> detector.load_model()
        >>> mask = detector.detect_watermark(image, sensitivity=0.5)
        >>> if mask is not None:
        ...     print(f"检测到水印区域: {np.sum(mask > 0)} 像素")
    """
```

#### 常量

```python
# 边缘检测阈值
EDGE_THRESHOLD_LOW: int = 50
EDGE_THRESHOLD_HIGH: int = 150

# 形态学操作核大小
MORPH_KERNEL_SIZE: int = 5

# 轮廓面积阈值
MIN_CONTOUR_AREA: int = 100
MAX_CONTOUR_AREA_RATIO: float = 0.5  # 相对于图像面积
```

---

### ImageInpainter (图像修复器)

**模块路径**: `app.core.ai.image_inpainter`

#### 类定义

```python
class ImageInpainter:
    """
    图像修复器 - 基于mask修复图像中的水印区域

    支持的修复算法:
        - TELEA: 快速，适合小到中等区域
        - Navier-Stokes: 高质量，适合大区域
        - Custom: 自定义方法，适合极小区域

    属性:
        config (Optional[ConfigParser]): 配置对象
        logger (logging.Logger): 日志记录器
        inpainting_model (Optional[str]): 修复模型名称
    """
```

#### 构造函数

```python
def __init__(self, config: Optional[ConfigParser] = None) -> None:
    """
    初始化图像修复器

    参数:
        config: 配置对象（可选）

    示例:
        >>> inpainter = ImageInpainter()
        >>> inpainter_with_config = ImageInpainter(config)
    """
```

#### 核心方法

##### load_model()

```python
def load_model(self) -> bool:
    """
    加载修复模型

    返回:
        bool: 成功返回True，失败返回False

    说明:
        当前使用OpenCV修复算法，未来可扩展GAN等深度学习方法

    示例:
        >>> inpainter = ImageInpainter()
        >>> success = inpainter.load_model()
        >>> assert success is True
    """
```

##### inpaint_frame()

```python
def inpaint_frame(
    self,
    image: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    根据掩码修复图像

    参数:
        image: 输入图像（BGR格式，numpy数组）
        mask: 二值掩码（单通道或三通道，numpy数组）
            - None: 返回原图
            - 全0掩码: 返回原图
            - 有效掩码: 执行修复

    返回:
        np.ndarray: 修复后的图像（BGR格式）

    异常:
        ValueError: 如果image或mask格式不正确
        RuntimeError: 如果修复过程出错

    算法选择逻辑:
        - 掩码面积 < 5%: Custom方法
        - 掩码面积 5%-15%: TELEA算法
        - 掩码面积 > 15%: Navier-Stokes算法

    示例:
        >>> import cv2
        >>> image = cv2.imread("input.jpg")
        >>> mask = cv2.imread("mask.png", cv2.IMREAD_GRAYSCALE)
        >>> inpainter = ImageInpainter()
        >>> inpainter.load_model()
        >>> result = inpainter.inpaint_frame(image, mask)
        >>> cv2.imwrite("output.jpg", result)
    """
```

##### _custom_inpaint() (私有方法)

```python
def _custom_inpaint(
    self,
    image: np.ndarray,
    mask: np.ndarray
) -> np.ndarray:
    """
    自定义修复方法（适合极小区域）

    参数:
        image: 输入图像
        mask: 二值掩码

    返回:
        np.ndarray: 修复后的图像

    算法:
        1. 使用高斯模糊平滑边界
        2. 查找掩码边界像素
        3. 用周围像素均值填充掩码区域

    注意:
        这是一个简单的方法，适合极小的水印区域
        对于较大区域，建议使用TELEA或NS算法
    """
```

#### 常量

```python
# 掩码二值化阈值
MASK_BINARY_THRESHOLD: int = 127

# 修复半径
INPAINT_RADIUS: int = 3

# 面积阈值（相对于图像总面积）
SMALL_AREA_THRESHOLD: float = 0.05    # 5%
MEDIUM_AREA_THRESHOLD: float = 0.15   # 15%
```

---

### AIHandler (AI 处理协调器)

**模块路径**: `app.core.ai.ai_handler`

#### 类定义

```python
class AIHandler:
    """
    AI处理协调器 - 协调水印检测和图像修复流程

    职责:
        1. 管理检测器和修复器的生命周期
        2. 协调检测和修复流程
        3. 处理用户手动选择的掩码
        4. 返回处理结果和元数据

    属性:
        config (Optional[ConfigParser]): 配置对象
        ai_params (Dict[str, Any]): AI参数
        detector (Optional[WatermarkDetector]): 检测器实例
        inpainter (Optional[ImageInpainter]): 修复器实例
    """
```

#### 构造函数

```python
def __init__(
    self,
    config: Optional[ConfigParser] = None,
    ai_params: Optional[Dict[str, Any]] = None
) -> None:
    """
    初始化AI处理协调器

    参数:
        config: 配置对象（可选）
        ai_params: AI参数字典（可选）
            - auto_detect: bool, 是否自动检测（默认True）
            - detection_sensitivity: float, 检测敏感度（默认0.5）
            - inpainting_method: str, 修复方法（默认"auto"）

    示例:
        >>> ai_handler = AIHandler()
        >>> ai_params = {
        ...     "auto_detect": True,
        ...     "detection_sensitivity": 0.6,
        ...     "inpainting_method": "auto"
        ... }
        >>> ai_handler_with_params = AIHandler(config, ai_params)
    """
```

#### 核心方法

##### load_models()

```python
def load_models(self) -> bool:
    """
    加载所有AI模型

    返回:
        bool: 成功返回True，失败返回False

    说明:
        加载检测器和修复器的模型

    示例:
        >>> ai_handler = AIHandler()
        >>> success = ai_handler.load_models()
        >>> assert success is True
    """
```

##### process_frame()

```python
def process_frame(
    self,
    frame: np.ndarray,
    processing_params: Optional[Dict[str, Any]] = None
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    处理单个图像帧

    参数:
        frame: 输入帧（BGR格式，numpy数组）
        processing_params: 处理参数字典（可选）
            - auto_detect: bool, 是否自动检测（默认True）
            - detection_sensitivity: float, 检测敏感度（默认0.5）
            - user_mask: np.ndarray, 用户手动选择的掩码（可选）

    返回:
        Tuple[np.ndarray, Dict[str, Any]]:
            - processed_frame: 处理后的帧
            - processing_info: 处理信息字典
                - "watermark_areas_found": int, 检测到的水印区域数量
                - "processing_time": float, 处理耗时（秒）
                - "inpainting_method": str, 使用的修复方法
                - "error": str, 错误信息（如果有）

    异常:
        ValueError: 如果frame格式不正确
        RuntimeError: 如果处理过程出错

    处理流程:
        1. 如果提供user_mask，直接使用
        2. 否则，如果auto_detect=True，调用检测器
        3. 如果检测到mask或提供了user_mask，调用修复器
        4. 返回处理结果和元数据

    示例:
        >>> import cv2
        >>> frame = cv2.imread("input.jpg")
        >>> ai_handler = AIHandler()
        >>> ai_handler.load_models()
        >>>
        >>> # 自动检测模式
        >>> params_auto = {"auto_detect": True, "detection_sensitivity": 0.5}
        >>> result, info = ai_handler.process_frame(frame, params_auto)
        >>> print(f"检测到 {info['watermark_areas_found']} 个水印区域")
        >>> print(f"使用方法: {info['inpainting_method']}")
        >>>
        >>> # 手动选择模式
        >>> user_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        >>> user_mask[100:200, 100:200] = 255  # 手动框选区域
        >>> params_manual = {"auto_detect": False, "user_mask": user_mask}
        >>> result, info = ai_handler.process_frame(frame, params_manual)
    """
```

---

### VideoProcessorThread (视频处理线程)

**模块路径**: `app.core.video.video_processor`

#### 类定义

```python
class VideoProcessorThread(QThread):
    """
    视频处理线程 - 在独立线程中处理视频，避免UI冻结

    信号:
        progress: pyqtSignal(int) - 进度更新 (0-100)
        status: pyqtSignal(str) - 状态消息
        finished: pyqtSignal(str) - 处理完成，参数为输出文件路径
        error: pyqtSignal(str) - 错误消息
        preview_update: pyqtSignal(object) - 预览帧更新

    属性:
        input_path (str): 输入文件路径
        output_path (str): 输出文件路径
        ai_params (Dict[str, Any]): AI参数
        config (Optional[ConfigParser]): 配置对象
    """
```

#### 构造函数

```python
def __init__(
    self,
    input_path: str,
    output_path: str,
    ai_params: Optional[Dict[str, Any]] = None,
    config: Optional[ConfigParser] = None,
    parent: Optional[QThread] = None
) -> None:
    """
    初始化视频处理线程

    参数:
        input_path: 输入文件路径
        output_path: 输出文件路径
        ai_params: AI参数字典（可选）
        config: 配置对象（可选）
        parent: 父线程（可选）

    示例:
        >>> processor = VideoProcessorThread(
        ...     input_path="input.mp4",
        ...     output_path="output.mp4",
        ...     ai_params={"auto_detect": True}
        ... )
    """
```

#### 核心方法

##### run()

```python
def run(self) -> None:
    """
    主处理循环（重写QThread.run）

    流程:
        1. 初始化AI Handler
        2. 判断文件类型（图片/视频）
        3. 调用相应的处理方法
        4. 发射信号更新UI

    信号发射:
        - status: 状态更新
        - progress: 进度更新
        - preview_update: 预览更新
        - finished: 处理完成
        - error: 错误发生

    示例:
        >>> processor = VideoProcessorThread("input.mp4", "output.mp4")
        >>> processor.progress.connect(lambda p: print(f"Progress: {p}%"))
        >>> processor.finished.connect(lambda f: print(f"Done: {f}"))
        >>> processor.start()  # 开始处理
    """
```

##### stop()

```python
def stop(self) -> None:
    """
    停止处理

    说明:
        设置内部标志，在下一次循环迭代时停止处理

    示例:
        >>> processor.start()
        >>> # ... 用户点击停止按钮
        >>> processor.stop()
    """
```

---

### FFmpegAudioProcessor (FFmpeg 音频处理器)

**模块路径**: `app.core.audio.ffmpeg_audio_processor`

#### 类定义

```python
class FFmpegAudioProcessor:
    """
    FFmpeg音频处理器 - 处理视频音频轨道

    功能:
        1. 检测FFmpeg可用性
        2. 提取视频音频轨道
        3. 合并视频和音频

    属性:
        config (Optional[ConfigParser]): 配置对象
        logger (logging.Logger): 日志记录器
        ffmpeg_path (str): FFmpeg可执行文件路径
    """
```

#### 核心方法

##### is_available()

```python
def is_available(self) -> bool:
    """
    检查FFmpeg是否可用

    返回:
        bool: FFmpeg可用返回True，否则返回False

    示例:
        >>> processor = FFmpegAudioProcessor()
        >>> if processor.is_available():
        ...     print("FFmpeg is ready")
    """
```

##### process_video_with_audio_preservation()

```python
def process_video_with_audio_preservation(
    self,
    original_video_path: str,
    processed_video_path: str,
    final_output_path: str
) -> bool:
    """
    保留音频的视频处理

    参数:
        original_video_path: 原始视频路径（含音频）
        processed_video_path: 处理后视频路径（无音频）
        final_output_path: 最终输出路径（含音频）

    返回:
        bool: 成功返回True，失败返回False

    处理流程:
        1. 从原视频提取音频轨道
        2. 合并处理后的视频和原音频
        3. 输出最终文件
        4. 清理临时文件

    示例:
        >>> processor = FFmpegAudioProcessor()
        >>> success = processor.process_video_with_audio_preservation(
        ...     original_video_path="original.mp4",
        ...     processed_video_path="processed_no_audio.mp4",
        ...     final_output_path="final.mp4"
        ... )
        >>> if success:
        ...     print("Audio preserved successfully")
    """
```

---

## UI 模块 API

### SignalHandler (信号处理器)

**模块路径**: `app.ui.signal_handler`

#### 类定义

```python
class SignalHandler(QObject):
    """
    信号处理器 - 分离UI和业务逻辑

    设计模式: 组合模式
    职责: 处理MainWindow的所有信号响应逻辑

    信号:
        status_updated: pyqtSignal(str) - 状态更新信号

    属性:
        file_panel: 文件面板组件
        preview_panel: 预览面板组件
        control_panel: 控制面板组件
        log_panel: 日志面板组件
        preferences: 偏好设置管理器
        style_manager: 样式管理器
    """
```

#### 核心方法

##### handle_import_file()

```python
def handle_import_file(self, parent_widget) -> None:
    """
    处理文件导入请求

    参数:
        parent_widget: 父窗口组件，用于显示对话框

    流程:
        1. 显示文件选择对话框
        2. 更新预览面板
        3. 启用开始按钮
        4. 发射状态信号

    示例:
        >>> signal_handler.handle_import_file(main_window)
    """
```

##### handle_start_processing()

```python
def handle_start_processing(self) -> None:
    """
    处理开始处理请求

    流程:
        1. 检查是否已选择文件
        2. 创建VideoProcessorThread
        3. 连接信号
        4. 启动处理线程

    示例:
        >>> signal_handler.handle_start_processing()
    """
```

---

## 配置模块 API

### ConfigManager (配置管理器)

**模块路径**: `app.config.config_manager`

#### 类方法

##### load_config()

```python
@staticmethod
def load_config(config_path: Optional[str] = None) -> ConfigParser:
    """
    加载配置文件

    参数:
        config_path: 配置文件路径（可选，默认为"config.ini"）

    返回:
        ConfigParser: 配置对象

    行为:
        - 如果配置文件存在，读取并返回
        - 如果不存在，创建默认配置并返回

    示例:
        >>> config = ConfigManager.load_config()
        >>> config = ConfigManager.load_config("custom_config.ini")
    """
```

##### save_config()

```python
@staticmethod
def save_config(
    config: ConfigParser,
    config_path: Optional[str] = None
) -> bool:
    """
    保存配置到文件

    参数:
        config: 配置对象
        config_path: 配置文件路径（可选）

    返回:
        bool: 成功返回True，失败返回False

    示例:
        >>> config = ConfigManager.load_config()
        >>> config.set("ui", "theme", "light")
        >>> ConfigManager.save_config(config)
    """
```

##### get_default_config()

```python
@staticmethod
def get_default_config() -> ConfigParser:
    """
    获取默认配置

    返回:
        ConfigParser: 默认配置对象

    示例:
        >>> default_config = ConfigManager.get_default_config()
        >>> theme = default_config.get("ui", "theme")
    """
```

---

## 类型定义

### 通用类型

```python
from typing import Optional, Dict, Any, Tuple, List
import numpy as np
from configparser import ConfigParser

# 图像类型
ImageArray = np.ndarray  # BGR格式，shape=(H, W, 3)
MaskArray = np.ndarray   # 单通道灰度，shape=(H, W)

# AI参数类型
AIParams = Dict[str, Any]  # {"auto_detect": bool, "sensitivity": float, ...}

# 处理结果类型
ProcessingResult = Tuple[ImageArray, Dict[str, Any]]
```

### 配置类型

```python
# 配置节
class ConfigSection:
    PROCESSING = "processing"
    UI = "ui"
    PATHS = "paths"
    ADVANCED = "advanced"

# 配置键
class ConfigKey:
    # processing
    DEFAULT_SENSITIVITY = "default_detection_sensitivity"
    DEFAULT_METHOD = "default_inpainting_method"
    PRESERVE_AUDIO = "preserve_audio"

    # ui
    THEME = "theme"
    WINDOW_WIDTH = "window_width"
    WINDOW_HEIGHT = "window_height"
```

---

## 使用示例

### 完整的图像处理流程

```python
import cv2
from app.core.ai.watermark_detector import WatermarkDetector
from app.core.ai.image_inpainter import ImageInpainter
from app.core.ai.ai_handler import AIHandler

# 方式一：使用AI Handler（推荐）
def process_image_with_handler(image_path, output_path):
    # 读取图像
    image = cv2.imread(image_path)

    # 创建AI Handler
    ai_handler = AIHandler()
    ai_handler.load_models()

    # 处理图像
    params = {
        "auto_detect": True,
        "detection_sensitivity": 0.6
    }
    result, info = ai_handler.process_frame(image, params)

    # 保存结果
    cv2.imwrite(output_path, result)

    # 打印处理信息
    print(f"检测到 {info['watermark_areas_found']} 个水印区域")
    print(f"处理耗时: {info['processing_time']:.2f}秒")
    print(f"使用方法: {info['inpainting_method']}")

# 方式二：手动使用检测器和修复器
def process_image_manually(image_path, output_path):
    # 读取图像
    image = cv2.imread(image_path)

    # 创建检测器
    detector = WatermarkDetector()
    detector.load_model()

    # 检测水印
    mask = detector.detect_watermark(image, sensitivity=0.6)

    if mask is not None:
        # 创建修复器
        inpainter = ImageInpainter()
        inpainter.load_model()

        # 修复图像
        result = inpainter.inpaint_frame(image, mask)

        # 保存结果
        cv2.imwrite(output_path, result)
        print("处理完成！")
    else:
        print("未检测到水印")
```

### 视频处理流程

```python
from PyQt6.QtWidgets import QApplication
from app.core.video.video_processor import VideoProcessorThread

def process_video(input_path, output_path):
    app = QApplication([])

    # 创建处理线程
    processor = VideoProcessorThread(
        input_path=input_path,
        output_path=output_path,
        ai_params={
            "auto_detect": True,
            "detection_sensitivity": 0.5
        }
    )

    # 连接信号
    processor.progress.connect(lambda p: print(f"Progress: {p}%"))
    processor.status.connect(lambda s: print(f"Status: {s}"))
    processor.finished.connect(lambda f: print(f"Finished: {f}"))
    processor.error.connect(lambda e: print(f"Error: {e}"))

    # 开始处理
    processor.start()

    # 运行事件循环
    app.exec()
```

### 配置管理示例

```python
from app.config.config_manager import ConfigManager

# 加载配置
config = ConfigManager.load_config()

# 读取配置
theme = config.get("ui", "theme", fallback="dark")
sensitivity = config.getfloat("processing", "default_detection_sensitivity", fallback=0.5)

# 修改配置
config.set("ui", "theme", "light")
config.set("processing", "default_detection_sensitivity", "0.7")

# 保存配置
ConfigManager.save_config(config)
```

---

## 错误处理

### 异常类型

```python
# 输入错误
class InvalidInputError(ValueError):
    """输入数据格式错误"""
    pass

# 模型错误
class ModelLoadError(RuntimeError):
    """模型加载失败"""
    pass

# 处理错误
class ProcessingError(RuntimeError):
    """处理过程出错"""
    pass
```

### 错误处理示例

```python
try:
    detector = WatermarkDetector()
    detector.load_model()
    mask = detector.detect_watermark(image)
except InvalidInputError as e:
    print(f"输入错误: {e}")
except ModelLoadError as e:
    print(f"模型加载失败: {e}")
except ProcessingError as e:
    print(f"处理失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 最佳实践

### 1. 资源管理

```python
# ✅ 正确：使用完毕后释放资源
def process_video(input_path):
    cap = cv2.VideoCapture(input_path)
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            # 处理帧
            ...
    finally:
        cap.release()  # 确保释放资源
```

### 2. 错误处理

```python
# ✅ 正确：详细的错误处理
def process_with_error_handling(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"文件不存在: {image_path}")

    image = cv2.imread(image_path)
    if image is None:
        raise InvalidInputError(f"无法读取图像: {image_path}")

    # ... 处理逻辑
```

### 3. 类型注解

```python
# ✅ 正确：完整的类型注解
def process_frame(
    frame: np.ndarray,
    sensitivity: float = 0.5
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """处理帧，返回结果和元数据"""
    ...
```

---

**相关文档**:
- [架构设计文档](architecture.md)
- [测试文档](testing.md)
- [开发指南](development.md)
