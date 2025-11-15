import logging
import sys

from app.config.config_manager import ConfigManager
from app.ui.main_window import MainWindow
from app.utils.logger_setup import setup_logging


def main():
    """
    Main function to initialize and run the application.
    """
    # Setup logging (call this first)
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = ConfigManager.load_config()

        # Initialize PyQt6 application
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)

        # Set application properties
        app.setApplicationName("智能视频水印去除工具")
        app.setApplicationVersion("0.3.0-refactored")
        app.setOrganizationName("VideoWatermarkRemover")

        # Create and show the main window
        window = MainWindow(config)
        window.show()

        logger.info("✨ 智能视频水印去除工具 重构版本启动成功！")
        logger.info(f"Python 版本: {sys.version}")
        logger.info("🚀 重构后的模块化GUI界面已打开，请在窗口中操作")

        # Execute the application's event loop
        sys.exit(app.exec())

    except ImportError as e:
        logger.error(f"❌ 缺少必要的依赖库: {e}")
        logger.error("请运行: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 应用程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
