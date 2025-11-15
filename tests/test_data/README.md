# 测试数据目录说明

本目录包含智能视频水印去除工具的各种测试数据和样本文件。

## 目录结构

```
tests/test_data/
├── videos/          # 测试视频文件
├── images/          # 测试图像文件  
├── audio/           # 测试音频文件
├── configs/         # 测试配置文件
├── models/          # 测试用AI模型文件
└── README.md        # 本说明文件
```

## 文件类型说明

### videos/ 目录
- **small_test.mp4** - 小型测试视频 (480x320, 5秒)
- **medium_test.avi** - 中等测试视频 (720x480, 10秒)  
- **large_test.mov** - 大型测试视频 (1280x720, 15秒)
- **watermark_test.mp4** - 含水印的测试视频

### images/ 目录
- **test_image_480x320.png** - 小型测试图像
- **test_image_720x480.jpg** - 中型测试图像
- **test_image_1280x720.png** - 高清测试图像
- **watermark_sample.png** - 水印样本图像
- **mask_template.png** - 遮罩模板图像

### audio/ 目录
- **test_audio.wav** - 测试音频文件 (1秒，单声道)
- **background_music.mp3** - 背景音乐样本
- **voice_sample.wav** - 语音样本文件

### configs/ 目录
- **test_config.ini** - 测试配置文件
- **user_prefs_sample.json** - 用户偏好设置样本
- **ai_model_config.yaml** - AI模型配置样本

### models/ 目录
- **dummy_model.pth** - 虚拟PyTorch模型文件
- **test_weights.bin** - 测试权重文件
- **model_metadata.json** - 模型元数据文件

## 使用说明

### 自动生成测试数据
大部分测试数据会在测试执行时自动生成：

```powershell
# 运行音频处理测试时会自动生成音频文件
.\tests\test_audio_processing.ps1

# 运行性能测试时会自动生成图像文件  
.\scripts\test-performance.ps1

# 运行端到端测试时会自动生成配置文件
.\tests\test_end_to_end.ps1
```

### 手动创建测试数据
如需手动创建测试数据，请参考各测试脚本中的数据生成代码。

### 测试数据清理
测试完成后，临时生成的文件会自动清理。如需保留测试数据供调试使用：

```powershell
# 运行测试时添加 -KeepTestFiles 参数
.\tests\test_audio_processing.ps1 -KeepTestFiles
```

## 注意事项

1. **文件大小**: 测试文件都是小型文件，避免影响测试执行速度
2. **格式支持**: 包含多种常见的视频、音频和图像格式
3. **版本控制**: 大型二进制文件不会提交到git，会在测试时生成
4. **隐私保护**: 所有测试数据都是生成的，不包含真实用户内容

## 扩展测试数据

如需添加新的测试数据类型：

1. 在对应目录下添加样本文件
2. 更新相关测试脚本的数据生成逻辑
3. 更新本README文档

## 故障排除

- **文件不存在**: 运行对应的测试脚本会自动生成所需文件
- **权限错误**: 确保有tests/test_data目录的读写权限
- **空间不足**: 清理旧的测试数据文件释放空间