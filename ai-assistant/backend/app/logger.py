"""
日志配置模块
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.config import settings


def setup_logging():
    """配置日志系统"""

    # 创建logs目录
    log_dir = Path(settings.LOG_FILE).parent if settings.LOG_FILE else Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 配置日志格式
    log_format = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 详细格式（用于文件日志）
    detailed_format = logging.Formatter(
        fmt='%(asctime)s - [%(levelname)s] - %(name)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 获取root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 清除已有的handlers
    root_logger.handlers.clear()

    # 1. 控制台处理器 - 输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # 2. 文件处理器 - 输出到文件
    if settings.LOG_FILE:
        file_handler = RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_format)
        root_logger.addHandler(file_handler)

    # 配置特定模块的日志级别
    # 设置 chatbi_tool 的日志为 DEBUG 级别，以便看到详细的LLM调用信息
    logging.getLogger('app.tools.chatbi_tool').setLevel(logging.DEBUG)

    # 减少第三方库的日志噪音
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    # 记录日志系统初始化信息
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {settings.LOG_LEVEL}")
    logger.info(f"日志文件: {settings.LOG_FILE if settings.LOG_FILE else '未配置'}")
    logger.info(f"日志目录: {log_dir.absolute()}")
    logger.info("="*60)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger

    Args:
        name: logger名称，通常使用 __name__

    Returns:
        Logger实例
    """
    return logging.getLogger(name)
