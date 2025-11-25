"""
配置文件
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


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

    # 千问配置
    DASHSCOPE_API_KEY: str
    QWEN_MODEL: str = "qwen-plus"
    QWEN_TEMPERATURE: float = 0.7
    QWEN_MAX_TOKENS: int = 2000

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


# 创建全局配置实例
settings = Settings()