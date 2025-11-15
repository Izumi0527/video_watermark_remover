#!/usr/bin/env python3
"""
用户偏好设置默认值定义

提供各类偏好设置的默认配置：
1. UI界面偏好设置
2. 处理参数偏好设置
3. 路径相关偏好设置
4. 高级功能偏好设置
5. 批量处理偏好设置

从 user_preferences_manager.py 重构拆分
作者: Claude Code Assistant
创建时间: 2025-09-06
版本: v1.0 (重构版)
"""

from typing import Dict, Any


class PreferencesDefaults:
    """偏好设置默认值定义类"""

    # 默认偏好设置配置
    DEFAULT_PREFERENCES = {
        "ui": {
            "theme": "dark",  # 界面主题: 'dark' | 'light'
            "window_geometry": [100, 100, 1200, 800],  # 窗口位置和大小 [x, y, width, height]
            "window_maximized": False,  # 是否最大化
            "splitter_sizes": [400, 400],  # 分割器大小
            "active_tab": 0,  # 活动标签页索引
        },
        "processing": {
            "auto_detect": True,  # 自动检测水印
            "detection_sensitivity": 0.5,  # 检测敏感度 (0.1-1.0)
            "default_inpainting_method": "auto",  # 默认修复方法:
            # 'auto' | 'telea' | 'navier_stokes' | 'custom'
            "preserve_audio": True,  # 保留音频
            "output_quality": "high",  # 输出质量: 'low' | 'medium' | 'high'
        },
        "paths": {
            "last_input_dir": "",  # 最后输入目录
            "last_output_dir": "",  # 最后输出目录
            "recent_files": [],  # 最近文件列表 (最多10个)
            "ffmpeg_path": "",  # FFmpeg路径
        },
        "advanced": {
            "max_threads": -1,  # 最大线程数 (-1为自动)
            "cache_size_mb": 512,  # 缓存大小(MB)
            "enable_gpu": False,  # 启用GPU加速
            "log_level": "INFO",  # 日志级别
            "auto_save_interval": 300,  # 自动保存间隔(秒)
        },
        "batch": {
            "max_concurrent_files": 1,  # 最大并发文件数
            "auto_retry_failed": True,  # 自动重试失败的文件
            "delete_temp_files": True,  # 删除临时文件
            "show_progress_details": True,  # 显示详细进度
        },
    }

    @classmethod
    def get_default_preferences(cls) -> Dict[str, Any]:
        """
        获取默认偏好设置的深拷贝
        
        Returns:
            默认偏好设置字典的副本
        """
        import copy
        return copy.deepcopy(cls.DEFAULT_PREFERENCES)

    @classmethod
    def get_ui_defaults(cls) -> Dict[str, Any]:
        """获取UI相关默认设置"""
        return cls.DEFAULT_PREFERENCES["ui"].copy()

    @classmethod
    def get_processing_defaults(cls) -> Dict[str, Any]:
        """获取处理相关默认设置"""
        return cls.DEFAULT_PREFERENCES["processing"].copy()

    @classmethod
    def get_paths_defaults(cls) -> Dict[str, Any]:
        """获取路径相关默认设置"""
        return cls.DEFAULT_PREFERENCES["paths"].copy()

    @classmethod
    def get_advanced_defaults(cls) -> Dict[str, Any]:
        """获取高级功能默认设置"""
        return cls.DEFAULT_PREFERENCES["advanced"].copy()

    @classmethod
    def get_batch_defaults(cls) -> Dict[str, Any]:
        """获取批量处理默认设置"""
        return cls.DEFAULT_PREFERENCES["batch"].copy()