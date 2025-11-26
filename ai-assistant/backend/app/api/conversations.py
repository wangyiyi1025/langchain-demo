"""
对话管理 API
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.utils.timezone import get_beijing_time

from app.models.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationTableUpdate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    MessageCreate,
    MessageResponse
)
from app.services.conversation_db_service import conversation_db_service
from app.api.auth import get_current_user_from_token

router = APIRouter(prefix="/conversations", tags=["对话管理"])


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    创建新对话

    Args:
        conversation: 对话信息
        current_user: 当前用户

    Returns:
        创建的对话信息
    """
    try:
        conversation_id = conversation_db_service.create_conversation(
            user_id=current_user["id"],
            title=conversation.title
        )

        # 获取创建的对话信息
        conversation_data = conversation_db_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )

        if not conversation_data:
            raise HTTPException(status_code=500, detail="创建对话失败")

        return ConversationResponse(
            id=conversation_data["id"],
            user_id=conversation_data["user_id"],
            title=conversation_data["title"],
            selected_table=conversation_data.get("selected_table"),
            created_at=conversation_data["created_at"],
            updated_at=conversation_data["updated_at"],
            message_count=0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    获取用户的对话列表

    Args:
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        对话列表
    """
    try:
        conversations = conversation_db_service.list_conversations(
            user_id=current_user["id"],
            limit=limit,
            offset=offset
        )

        total = conversation_db_service.count_conversations(user_id=current_user["id"])

        conversation_list = [
            ConversationResponse(
                id=c["id"],
                user_id=c["user_id"],
                title=c["title"],
                selected_table=c.get("selected_table"),
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                message_count=c["message_count"]
            )
            for c in conversations
        ]

        return ConversationListResponse(
            total=total,
            conversations=conversation_list
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话列表失败: {str(e)}")


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    获取对话详情（包含消息列表）

    Args:
        conversation_id: 对话ID
        current_user: 当前用户

    Returns:
        对话详情
    """
    try:
        conversation_data = conversation_db_service.get_conversation_with_messages(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )

        if not conversation_data:
            raise HTTPException(status_code=404, detail="对话不存在")

        messages = [
            MessageResponse(
                id=m["id"],
                conversation_id=m["conversation_id"],
                role=m["role"],
                content=m["content"],
                created_at=m["created_at"]
            )
            for m in conversation_data.get("messages", [])
        ]

        return ConversationDetailResponse(
            id=conversation_data["id"],
            user_id=conversation_data["user_id"],
            title=conversation_data["title"],
            selected_table=conversation_data.get("selected_table"),
            created_at=conversation_data["created_at"],
            updated_at=conversation_data["updated_at"],
            message_count=len(messages),
            messages=messages
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话详情失败: {str(e)}")


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation: ConversationUpdate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    更新对话标题

    Args:
        conversation_id: 对话ID
        conversation: 更新信息
        current_user: 当前用户

    Returns:
        更新后的对话信息
    """
    try:
        success = conversation_db_service.update_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"],
            title=conversation.title
        )

        if not success:
            raise HTTPException(status_code=404, detail="对话不存在或更新失败")

        # 获取更新后的对话信息
        conversation_data = conversation_db_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )

        if not conversation_data:
            raise HTTPException(status_code=404, detail="对话不存在")

        return ConversationResponse(
            id=conversation_data["id"],
            user_id=conversation_data["user_id"],
            title=conversation_data["title"],
            selected_table=conversation_data.get("selected_table"),
            created_at=conversation_data["created_at"],
            updated_at=conversation_data["updated_at"],
            message_count=0
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新对话失败: {str(e)}")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    删除对话

    Args:
        conversation_id: 对话ID
        current_user: 当前用户

    Returns:
        操作结果
    """
    try:
        success = conversation_db_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )

        if not success:
            raise HTTPException(status_code=404, detail="对话不存在或删除失败")

        return {
            "success": True,
            "message": "对话已删除"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")


@router.delete("/{conversation_id}/messages")
async def clear_conversation_messages(
    conversation_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    清除对话的所有消息

    Args:
        conversation_id: 对话ID
        current_user: 当前用户

    Returns:
        操作结果
    """
    try:
        success = conversation_db_service.clear_messages(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )

        if not success:
            raise HTTPException(status_code=404, detail="对话不存在或清除失败")

        return {
            "success": True,
            "message": "对话消息已清除"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除对话消息失败: {str(e)}")


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    获取对话的消息列表

    Args:
        conversation_id: 对话ID
        limit: 返回数量限制
        current_user: 当前用户

    Returns:
        消息列表
    """
    try:
        messages = conversation_db_service.get_messages(
            conversation_id=conversation_id,
            user_id=current_user["id"],
            limit=limit
        )

        return [
            MessageResponse(
                id=m["id"],
                conversation_id=m["conversation_id"],
                role=m["role"],
                content=m["content"],
                created_at=m["created_at"]
            )
            for m in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取消息列表失败: {str(e)}")


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: int,
    message: MessageCreate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    添加消息到对话

    Args:
        conversation_id: 对话ID
        message: 消息内容
        current_user: 当前用户

    Returns:
        添加的消息信息
    """
    try:
        # 验证对话是否属于当前用户
        conversation = conversation_db_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )

        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        # 添加消息
        message_id = conversation_db_service.add_message(
            conversation_id=conversation_id,
            role=message.role,
            content=message.content
        )

        return MessageResponse(
            id=message_id,
            conversation_id=conversation_id,
            role=message.role,
            content=message.content,
            created_at=get_beijing_time()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加消息失败: {str(e)}")


@router.patch("/{conversation_id}/table", response_model=ConversationResponse)
async def update_conversation_table(
    conversation_id: int,
    table_update: ConversationTableUpdate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    更新对话的选中表

    Args:
        conversation_id: 对话ID
        table_update: 选中表信息
        current_user: 当前用户

    Returns:
        更新后的对话信息
    """
    try:
        # 将Pydantic模型转换为字典
        selected_table_dict = None
        if table_update.selected_table:
            selected_table_dict = table_update.selected_table.model_dump()

        success = conversation_db_service.update_selected_table(
            conversation_id=conversation_id,
            user_id=current_user["id"],
            selected_table=selected_table_dict
        )

        if not success:
            raise HTTPException(status_code=404, detail="对话不存在或更新失败")

        # 获取更新后的对话信息
        conversation_data = conversation_db_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )

        if not conversation_data:
            raise HTTPException(status_code=404, detail="对话不存在")

        return ConversationResponse(
            id=conversation_data["id"],
            user_id=conversation_data["user_id"],
            title=conversation_data["title"],
            selected_table=conversation_data.get("selected_table"),
            created_at=conversation_data["created_at"],
            updated_at=conversation_data["updated_at"],
            message_count=0
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新对话选中表失败: {str(e)}")
