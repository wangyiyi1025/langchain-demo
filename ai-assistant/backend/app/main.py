"""
FastAPI 应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
import logging

# 添加项目根目录到路径（backend目录），以便能找到 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv("../../.env")

from app.config import settings
from app.logger import setup_logging
from app.api import chat, system, database, auth, conversations
from app.database import init_db
from app.services.cleanup_service import cleanup_service

# 初始化日志系统（在所有其他操作之前）
setup_logging()
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI智能助手后端API - 支持多Agent和数据分析",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix=settings.API_PREFIX)
app.include_router(system.router, prefix=settings.API_PREFIX)
app.include_router(database.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(conversations.router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    try:
        # 初始化数据库
        logger.info("正在初始化数据库...")
        init_db()
        logger.info("✓ 数据库初始化成功")

        # 启动定时清理任务
        logger.info("启动定时清理任务...")
        cleanup_service.start()
        logger.info("✓ 定时清理任务已启动")
    except Exception as e:
        logger.error(f"✗ 启动初始化失败: {str(e)}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    try:
        # 停止定时任务
        logger.info("正在停止定时清理任务...")
        cleanup_service.stop()
        logger.info("✓ 定时清理任务已停止")
    except Exception as e:
        logger.error(f"✗ 关闭清理失败: {str(e)}", exc_info=True)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/api/v1/system/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"全局异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else "请联系管理员"
        }
    )


if __name__ == "__main__":
    import uvicorn

    # 打印启动信息到控制台
    print("=" * 60)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 60)
    print("\n📝 服务信息:")
    print(f"  • 运行地址: http://localhost:8000")
    print(f"  • API文档: http://localhost:8000/api/docs")
    print(f"  • 健康检查: http://localhost:8000/api/v1/system/health")
    print(f"  • 日志文件: {settings.LOG_FILE}")
    print("\n✨ 可用功能:")
    print("  • WebSocket实时对话")
    print("  • HTTP同步对话")
    print("  • 多工具支持")
    print("  • 会话管理")
    print("=" * 60 + "\n")

    # 记录到日志文件
    logger.info("="*60)
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 正在启动")
    logger.info("="*60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )