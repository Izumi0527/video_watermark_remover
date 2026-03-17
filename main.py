import logging
import sys

from app.config.config_manager import ConfigManager
from app.utils.logger_setup import setup_logging


def _preload_torch_before_pyqt6(logger: logging.Logger) -> None:
    """
    在导入 PyQt6 / Qt 之前预加载 torch（重要！）

    背景：在部分 Windows 环境中，若先导入 PyQt6（Qt DLL）再导入 PyTorch，可能触发
    `WinError 1114`（c10.dll 初始化失败）。预先导入 torch 可稳定规避该问题。

    说明：该函数只做预加载与日志记录；若 torch 不可用，会记录原因并继续启动 UI。
    """
    try:
        import torch  # noqa: F401

        logger.info("✅ 已在导入 PyQt6 前预加载 torch（用于规避 WinError 1114）")
    except Exception as e:
        # torch 可能因环境缺失/损坏而无法加载，这里不直接中断 UI 启动。
        logger.warning(f"⚠️ torch 预加载失败：{e}")
        logger.warning("   - 若后续 AI 功能不可用，请尝试重新执行：.\\scripts\\vwr.ps1 setup -Dev")
        logger.warning("   - 若仍报 WinError 1114，可尝试先导入 torch 再导入 PyQt6（本程序已做预加载）")


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

        # 必须在导入 PyQt6 之前预加载 torch，避免 WinError 1114（c10.dll 初始化失败）
        _preload_torch_before_pyqt6(logger)

        # Initialize PyQt6 application
        from PyQt6.QtWidgets import QApplication

        # 延迟导入：确保 torch 已在 PyQt6 之前加载
        from app.ui.main_window import MainWindow

        app = QApplication(sys.argv)

        # Set application properties
        app.setApplicationName("智能视频水印去除工具")
        app.setApplicationVersion("0.5.0")
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
