"""
数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息", min_length=1)
    session_id: Optional[str] = Field(None, description="会话ID")
    stream: bool = Field(False, description="是否流式输出")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    session_id: str = Field(..., description="会话ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str = Field(..., description="消息类型: start/stream/end/error")
    content: Optional[str] = Field(None, description="消息内容")
    message: Optional[str] = Field(None, description="用户消息（start类型）")
    full_response: Optional[str] = Field(None, description="完整响应（end类型）")


class ToolInfo(BaseModel):
    """工具信息模型"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")


class SystemInfo(BaseModel):
    """系统信息模型"""
    app_name: str
    version: str
    status: str
    available_tools: List[ToolInfo]


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    detail: Optional[str] = None