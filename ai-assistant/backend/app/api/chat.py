"""
聊天相关 API
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import ChatRequest, ChatResponse, WebSocketMessage
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
    WebSocket 聊天端点（流式）
    
    Args:
        websocket: WebSocket连接
        session_id: 会话ID
    """
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            # 发送开始标记
            await websocket.send_json({
                "type": "start",
                "message": user_message
            })
            
            # 流式响应
            full_response = ""
            async for chunk in conversation_service.chat_stream(session_id, user_message):
                full_response += chunk
                await websocket.send_json({
                    "type": "stream",
                    "content": chunk
                })
            
            # 发送结束标记
            await websocket.send_json({
                "type": "end",
                "full_response": full_response
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