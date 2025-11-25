"""
系统相关 API
"""
from fastapi import APIRouter
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import settings
from app.models.schemas import SystemInfo, ToolInfo
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/system", tags=["系统"])
from dotenv import load_dotenv
load_dotenv("../../.env")

@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """
    获取系统信息
    
    Returns:
        系统信息
    """
    tools = conversation_service.get_tools_info()
    tool_list = [
        ToolInfo(name=tool['name'], description=tool['description'])
        for tool in tools
    ]
    
    return SystemInfo(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        status="running",
        available_tools=tool_list
    )


@router.get("/health")
async def health_check():
    """
    健康检查
    
    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


@router.get("/tools")
async def get_tools():
    """
    获取可用工具列表
    
    Returns:
        工具列表
    """
    tools = conversation_service.get_tools_info()
    return {
        "success": True,
        "tools": tools
    }