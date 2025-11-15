import logging
import logging.handlers
import os
import sys
from datetime import datetime


def setup_logging(config=None):
    """
    配置应用程序日志系统 - 统一输出到logs目录
    采用本地logs目录，便于用户查看和管理
    """
    # 确保logs目录存在
    log_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            print(f"❌ 无法创建日志目录 {log_dir}: {e}")
            return False

    # 设置日志级别
    log_level_str = "INFO"
    if config:
        log_level_str = config.get("Logging", "log_level", fallback="INFO").upper()

    log_level = getattr(logging, log_level_str, logging.INFO)

    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file_path = os.path.join(log_dir, f"watermark_remover_{timestamp}.log")

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建文件处理器 - 支持日志轮转
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(log_level)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # 控制台只显示警告及以上级别

        # 设置日志格式
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")

        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # 添加处理器到根日志记录器
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # 记录日志系统启动信息
        logging.info("=" * 50)
        logging.info("智能视频水印去除工具 - 日志系统启动")
        logging.info(f"日志级别: {log_level_str}")
        logging.info(f"日志文件: {log_file_path}")
        logging.info(f"Python版本: {sys.version}")
        logging.info("=" * 50)

        return True

    except Exception as e:
        print(f"❌ 日志系统配置失败: {e}")
        return False
