"""
对话服务
"""
from typing import Dict, List
from langchain_core.messages import HumanMessage, AIMessage
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.chat_agent import ChatAgent


class ConversationService:
    """对话服务类"""
    
    def __init__(self):
        """初始化服务"""
        self.conversations: Dict[str, List] = {}
        self.agent = ChatAgent()
    
    def get_or_create_conversation(self, session_id: str) -> List:
        """
        获取或创建会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            对话历史列表
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        添加消息到历史
        
        Args:
            session_id: 会话ID
            role: 角色（user/assistant）
            content: 消息内容
        """
        history = self.get_or_create_conversation(session_id)
        
        if role == "user":
            history.append(HumanMessage(content=content))
        elif role == "assistant":
            history.append(AIMessage(content=content))
    
    def clear_conversation(self, session_id: str):
        """
        清空会话历史
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.conversations:
            self.conversations[session_id] = []
    
    def get_conversation_count(self, session_id: str) -> int:
        """
        获取会话消息数量
        
        Args:
            session_id: 会话ID
        
        Returns:
            消息数量
        """
        return len(self.get_or_create_conversation(session_id))
    
    async def chat_stream(self, session_id: str, message: str):
        """
        流式对话
        
        Args:
            session_id: 会话ID
            message: 用户消息
        
        Yields:
            响应内容片段
        """
        import asyncio
        
        history = self.get_or_create_conversation(session_id)
        
        # 在后台线程中执行Agent
        result = await asyncio.to_thread(
            self.agent.chat,
            message,
            history
        )
        
        if result['success']:
            response = result['output']
            
            # 保存到历史
            self.add_message(session_id, "user", message)
            self.add_message(session_id, "assistant", response)
            
            # 模拟流式输出
            chunk_size = 5  # 每次发送5个字符
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.03)  # 控制速度
        else:
            error_msg = result['output']
            yield error_msg
    
    def chat(self, session_id: str, message: str) -> Dict:
        """
        同步对话（用于非流式场景）
        
        Args:
            session_id: 会话ID
            message: 用户消息
        
        Returns:
            响应字典
        """
        history = self.get_or_create_conversation(session_id)
        
        result = self.agent.chat(message, history)
        
        if result['success']:
            # 保存到历史
            self.add_message(session_id, "user", message)
            self.add_message(session_id, "assistant", result['output'])
        
        return result
    
    def get_tools_info(self) -> List[Dict]:
        """
        获取工具信息
        
        Returns:
            工具列表
        """
        return self.agent.get_tool_descriptions()


# 创建全局服务实例
conversation_service = ConversationService()