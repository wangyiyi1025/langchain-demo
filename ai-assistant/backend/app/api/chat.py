"""
聊天相关 API - 支持多Agent和表上下文
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Optional, List
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import ChatRequest, ChatResponse, WebSocketMessage, ChatRequestWithAgent, AgentInfo
from services.conversation_service import conversation_service

router = APIRouter(prefix="/chat", tags=["聊天"])


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送聊天消息（同步）
    
    Args:
        request: 聊天请求
    
    Returns:
        聊天响应
    """
    session_id = request.session_id or f"session_{os.urandom(8).hex()}"
    
    try:
        result = conversation_service.chat(session_id, request.message)
        
        return ChatResponse(
            success=result['success'],
            message=result['output'],
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket 聊天端点（流式） - 支持Agent选择和表上下文
    Args:
        websocket: WebSocket连接
        session_id: 会话ID
    接收的消息格式：
        {
            "message": "用户消息",
            "agent_type": "chat" | "chatbi",  # 可选
            "table_context": {"database": "db_name", "table": "table_name"}  # 可选
        }
    """
    await websocket.accept()

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            agent_type = message_data.get("agent_type", "chat")
            table_context = message_data.get("table_context")

            if not user_message:
                continue

            # 如果有表上下文，保存到会话中
            if table_context and agent_type == "chatbi":
                conversation_service.set_table_context(
                    session_id,
                    table_context.get("database"),
                    table_context.get("table")
                )

            # 发送开始标记
            await websocket.send_json({
                "type": "start",
                "message": user_message,
                "agent_type": agent_type
            })

            # 流式响应
            full_response = ""
            async for chunk in conversation_service.chat_stream(
                session_id,
                user_message,
                agent_type=agent_type,
                table_context=table_context
            ):
                full_response += chunk
                await websocket.send_json({
                    "type": "stream",
                    "content": chunk
                })

            # 发送结束标记
            await websocket.send_json({
                "type": "end",
                "full_response": full_response,
                "agent_type": agent_type
            })

    except WebSocketDisconnect:
        print(f"WebSocket断开: {session_id}")
    except Exception as e:
        print(f"WebSocket错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"发生错误: {str(e)}"
            })
        except:
            pass


@router.delete("/clear/{session_id}")
async def clear_history(session_id: str):
    """
    清除会话历史
    
    Args:
        session_id: 会话ID
    
    Returns:
        操作结果
    """
    conversation_service.clear_conversation(session_id)
    return {
        "success": True,
        "message": "会话历史已清除"
    }


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    获取会话历史
    Args:
        session_id: 会话ID
    Returns:
        历史消息数量
    """
    count = conversation_service.get_conversation_count(session_id)
    return {
        "session_id": session_id,
        "message_count": count
    }


@router.get("/agents", response_model=List[AgentInfo])
async def get_agents():
    """
    获取所有可用的Agent列表
    Returns:
        Agent信息列表
    """
    try:
        agents = conversation_service.get_agents_info()
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent列表失败: {str(e)}")


@router.post("/table-context/{session_id}")
async def set_table_context(session_id: str, database: str, table: str):
    """
    设置会话的表上下文
    Args:
        session_id: 会话ID
        database: 数据库名
        table: 表名
    Returns:
        操作结果
    """
    try:
        conversation_service.set_table_context(session_id, database, table)
        return {
            "success": True,
            "message": "表上下文已设置",
            "table_context": {
                "database": database,
                "table": table
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置表上下文失败: {str(e)}")


@router.get("/table-context/{session_id}")
async def get_table_context(session_id: str):
    """
    获取会话的表上下文
    Args:
        session_id: 会话ID
    Returns:
        表上下文信息
    """
    try:
        context = conversation_service.get_table_context(session_id)
        return {
            "success": True,
            "table_context": context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表上下文失败: {str(e)}")


@router.delete("/table-context/{session_id}")
async def clear_table_context(session_id: str):
    """
    清除会话的表上下文
    Args:
        session_id: 会话ID
    Returns:
        操作结果
    """
    try:
        conversation_service.clear_table_context(session_id)
        return {
            "success": True,
            "message": "表上下文已清除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除表上下文失败: {str(e)}")