"""
配置文件
"""
import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings

# 配置日志
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "AI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # API配置
    API_PREFIX: str = "/api/v1"

    # CORS配置
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # LLM配置（OpenAI兼容接口）
    # 支持任何兼容OpenAI API的大模型服务：
    # - OpenAI官方 (https://api.openai.com/v1)
    # - 本地Ollama (http://localhost:11434/v1)
    # - vLLM (http://localhost:8000/v1)
    # - LM Studio (http://localhost:1234/v1)
    # - 阿里千问 (https://dashscope.aliyuncs.com/compatible-mode/v1)
    # - 其他兼容服务...
    OPENAI_API_KEY: str = "sk-dummy-key"  # 本地模型可能不需要真实的key
    OPENAI_BASE_URL: str = "http://localhost:11434/v1"  # 默认Ollama地址
    LLM_MODEL: str = "qwen2.5:latest"  # 模型名称
    LLM_TEMPERATURE: float = 0.7  # 温度参数，控制输出随机性
    LLM_MAX_TOKENS: int = 2000  # 最大生成token数
    LLM_MAX_RETRIES: int = 2  # 失败重试次数
    LLM_PROVIDER: str = "ollama"  # 提供商标识，用于日志和调试
    USE_TOOL_CALL_ADAPTER: bool = False  # 是否使用 Tool Call 适配器（临时方案）

    # Agent配置
    AGENT_MAX_ITERATIONS: int = 5
    AGENT_VERBOSE: bool = True

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/app.log"

    # MySQL数据库配置
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_DATABASE: str = "smart_chat_bi_meta"
    MYSQL_CHARSET: str = "utf8mb4"

    # 时区配置
    TIMEZONE: str = "Asia/Shanghai"  # 东八区（北京时间）

    # StarRocks数据库配置
    STARROCKS_HOST: str = "127.0.0.1"
    STARROCKS_PORT: int = 9030
    STARROCKS_USER: str = "admin"
    STARROCKS_PASSWORD: str = "123456"

    # JWT认证配置
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_required_config(self):
        """验证必需的配置项"""
        errors = []

        # 验证 OpenAI API Key（本地模型可能不需要真实的key，所以只做基本检查）
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY 未配置，请在 .env 文件中设置（本地模型可使用任意值如 'sk-dummy-key'）")

        # 验证 Base URL
        if not self.OPENAI_BASE_URL:
            errors.append("OPENAI_BASE_URL 未配置")

        # 验证模型名称
        if not self.LLM_MODEL:
            errors.append("LLM_MODEL 未配置，请指定要使用的模型名称")

        if errors:
            error_msg = "\n".join([f"  - {err}" for err in errors])
            raise ValueError(f"\n配置验证失败:\n{error_msg}\n")

    def mask_sensitive_value(self, value: str, show_chars: int = 4) -> str:
        """脱敏处理敏感信息"""
        if not value or len(value) <= show_chars:
            return "***"
        return value[:show_chars] + "*" * (len(value) - show_chars)

    def print_config(self):
        """打印配置信息（敏感信息脱敏）"""
        logger.info("=" * 60)
        logger.info("应用配置信息")
        logger.info("=" * 60)
        logger.info(f"应用名称: {self.APP_NAME}")
        logger.info(f"应用版本: {self.APP_VERSION}")
        logger.info(f"调试模式: {self.DEBUG}")
        logger.info(f"API前缀: {self.API_PREFIX}")
        logger.info("-" * 60)
        logger.info("大模型配置 (OpenAI兼容接口):")
        logger.info(f"  提供商: {self.LLM_PROVIDER}")
        logger.info(f"  API Key: {self.mask_sensitive_value(self.OPENAI_API_KEY)}")
        logger.info(f"  Base URL: {self.OPENAI_BASE_URL}")
        logger.info(f"  模型: {self.LLM_MODEL}")
        logger.info(f"  温度: {self.LLM_TEMPERATURE}")
        logger.info(f"  最大Token: {self.LLM_MAX_TOKENS}")
        logger.info(f"  最大重试: {self.LLM_MAX_RETRIES}")
        logger.info(f"  Tool Call 适配器: {'启用 (临时方案)' if self.USE_TOOL_CALL_ADAPTER else '禁用'}")
        logger.info("-" * 60)
        logger.info("Agent配置:")
        logger.info(f"  最大迭代次数: {self.AGENT_MAX_ITERATIONS}")
        logger.info(f"  详细日志: {self.AGENT_VERBOSE}")
        logger.info("-" * 60)
        logger.info("数据库配置:")
        logger.info(f"  MySQL: {self.MYSQL_USER}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}")
        logger.info(f"  StarRocks: {self.STARROCKS_USER}@{self.STARROCKS_HOST}:{self.STARROCKS_PORT}")
        logger.info("=" * 60)


# 创建全局配置实例
settings = Settings()

# 验证配置
try:
    settings.validate_required_config()
    settings.print_config()
except ValueError as e:
    logger.error(str(e))
    raise
