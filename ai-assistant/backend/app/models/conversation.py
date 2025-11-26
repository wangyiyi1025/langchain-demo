"""
对话相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MessageBase(BaseModel):
    """消息基础模型"""
    role: str = Field(..., description="消息角色: user, assistant, system")
    content: str = Field(..., description="消息内容")


class MessageCreate(MessageBase):
    """消息创建模型"""
    conversation_id: int = Field(..., description="对话ID")


class MessageResponse(MessageBase):
    """消息响应模型"""
    id: int
    conversation_id: int
    created_at: datetime


class ConversationBase(BaseModel):
    """对话基础模型"""
    title: str = Field(..., max_length=255, description="对话标题")


class ConversationCreate(BaseModel):
    """对话创建模型"""
    title: str = Field(default="新对话", max_length=255, description="对话标题")


class ConversationUpdate(BaseModel):
    """对话更新模型"""
    title: str = Field(..., max_length=255, description="对话标题")


class SelectedTableInfo(BaseModel):
    """选中的表信息"""
    database: str = Field(..., description="数据库名")
    table: str = Field(..., description="表名")
    comment: Optional[str] = Field(None, description="表注释")


class ConversationTableUpdate(BaseModel):
    """对话选中表更新模型"""
    selected_table: Optional[SelectedTableInfo] = Field(None, description="选中的表信息")


class ConversationResponse(BaseModel):
    """对话响应模型"""
    id: int
    user_id: int
    title: str
    selected_table: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0


class ConversationDetailResponse(ConversationResponse):
    """对话详情响应模型（包含消息列表）"""
    messages: List[MessageResponse] = []


class ConversationListResponse(BaseModel):
    """对话列表响应模型"""
    total: int
    conversations: List[ConversationResponse]
