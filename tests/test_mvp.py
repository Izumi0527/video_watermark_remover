#!/usr/bin/env python3
# -*- coding: utf-8 BOM-*-
"""
MVP测试脚本 - 智能视频水印去除工具

用于测试基础功能是否正常工作：
1. 配置系统加载
2. 日志系统初始化  
3. GUI界面启动
4. 基础模块导入

运行方式:
python test_mvp.py
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """测试所有核心模块的导入"""
    print("[测试] 测试模块导入...")
    
    try:
        # 测试配置管理
        from app.config.config_manager import ConfigManager
        print("[OK] ConfigManager 导入成功")
        
        # 测试日志系统
        from app.utils.logger_setup import setup_logging
        print("[OK] Logger 模块导入成功")
        
        # 测试工具函数
        from app.utils.utils import ensure_directory_exists, format_duration
        print("[OK] Utils 模块导入成功")
        
        # 测试GUI模块
        from app.ui.main_window import MainWindow
        print("[OK] MainWindow 导入成功")
        
        # 测试PyQt6
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        print("[OK] PyQt6 导入成功")
        
        assert True  # 所有导入成功
        
    except ImportError as e:
        print(f"[ERROR] 导入失败: {e}")
        assert False, f"模块导入失败: {e}"

def test_config_system():
    """测试配置系统"""
    print("\n[配置] 测试配置系统...")
    
    try:
        from app.config.config_manager import ConfigManager
        
        # 加载配置
        config = ConfigManager.load_config()
        print("[OK] 配置文件加载成功")
        
        # 测试配置读取
        ffmpeg_path = config.get('Paths', 'ffmpeg_path', fallback='未配置')
        log_level = config.get('Logging', 'log_level', fallback='INFO')
        
        print(f"   FFmpeg路径: {ffmpeg_path}")
        print(f"   日志级别: {log_level}")
        print(f"   配置文件路径: {ConfigManager.get_config_path()}")
        
        assert config is not None, "配置对象应该不为空"
        
    except Exception as e:
        print(f"[ERROR] 配置系统测试失败: {e}")
        assert False, f"配置系统测试失败: {e}"

def test_logging_system():
    """测试日志系统"""
    print("\n[日志] 测试日志系统...")
    
    try:
        from app.utils.logger_setup import setup_logging
        import logging
        
        # 初始化日志系统
        setup_logging()
        print("[OK] 日志系统初始化成功")
        
        # 测试日志记录
        logger = logging.getLogger(__name__)
        logger.info("测试INFO级别日志")
        logger.warning("测试WARNING级别日志")
        
        print("[OK] 日志记录测试成功")
        assert logger is not None, "日志对象应该不为空"
        
    except Exception as e:
        print(f"[ERROR] 日志系统测试失败: {e}")
        assert False, f"日志系统测试失败: {e}"

def test_gui_creation():
    """测试GUI创建（不显示）"""
    print("\n[GUI] 测试GUI创建...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from app.ui.main_window import MainWindow
        from app.config.config_manager import ConfigManager
        
        # 创建应用实例
        app = QApplication([])
        print("[OK] QApplication 创建成功")
        
        # 加载配置
        config = ConfigManager.load_config()
        
        # 创建主窗口（但不显示）
        window = MainWindow(config)
        print("[OK] MainWindow 创建成功")
        print(f"   窗口标题: {window.windowTitle()}")
        print(f"   窗口大小: {window.size().width()}x{window.size().height()}")
        
        # 清理
        app.quit()
        assert window is not None, "主窗口应该创建成功"
        
    except Exception as e:
        print(f"[ERROR] GUI创建测试失败: {e}")
        assert False, f"GUI创建测试失败: {e}"

def test_utility_functions():
    """测试工具函数"""
    print("\n[工具] 测试工具函数...")
    
    try:
        from app.utils.utils import ensure_directory_exists, format_duration, get_file_basename
        
        # 测试目录创建
        test_dir = "temp_test_dir"
        result = ensure_directory_exists(test_dir)
        print(f"[OK] 目录创建测试: {result}")
        
        # 清理测试目录
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
        
        # 测试时间格式化
        duration_str = format_duration(3661)  # 1小时1分1秒
        print(f"[OK] 时间格式化测试: {duration_str}")
        
        # 测试文件名提取
        basename = get_file_basename("path/to/video.mp4")
        print(f"[OK] 文件名提取测试: {basename}")
        
        assert duration_str is not None, "时间格式化函数应该返回结果"
        assert basename is not None, "文件名提取函数应该返回结果"
        
    except Exception as e:
        print(f"[ERROR] 工具函数测试失败: {e}")
        assert False, f"工具函数测试失败: {e}"

def main():
    """主测试函数"""
    print("智能视频水印去除工具 - MVP功能测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("配置系统", test_config_system),
        ("日志系统", test_logging_system),
        ("GUI创建", test_gui_creation),
        ("工具函数", test_utility_functions),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            test_func()  # 调用测试函数
            passed += 1  # 如果没有抛出异常，说明测试通过
        except AssertionError as e:
            print(f"[ERROR] {test_name}测试失败: {e}")
        except Exception as e:
            print(f"[ERROR] {test_name}测试发生异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"[统计] 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("[成功] 所有测试通过！MVP版本准备就绪。")
        print("\n[提示] 接下来可以运行: python main.py")
        return 0
    else:
        print("[警告] 部分测试失败，请检查依赖和配置。")
        print("\n[提示] 建议运行: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)