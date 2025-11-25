"""
对话服务 - 支持多Agent管理
"""
from typing import Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agents.chatbi_agent import ChatBIAgent
from app.agents.agent_manager import agent_manager


class ConversationService:
    """对话服务类 - 智慧报表数据助手"""

    def __init__(self):
        """初始化服务"""
        self.conversations: Dict[str, List] = {}
        self.table_contexts: Dict[str, Optional[Dict]] = {}  # 存储每个会话的表上下文

        # 初始化并注册所有Agent
        self._initialize_agents()

    def _initialize_agents(self):
        """初始化并注册所有Agent"""
        # 注册智慧报表数据助手（ChatBI）
        chatbi_agent = ChatBIAgent()
        agent_manager.register_agent(chatbi_agent)
    
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

    def set_table_context(self, session_id: str, database: str, table: str):
        """
        设置会话的表上下文
        Args:
            session_id: 会话ID
            database: 数据库名
            table: 表名
        """
        self.table_contexts[session_id] = {
            "database": database,
            "table": table
        }

    def get_table_context(self, session_id: str) -> Optional[Dict]:
        """
        获取会话的表上下文
        Args:
            session_id: 会话ID
        Returns:
            表上下文字典或None
        """
        return self.table_contexts.get(session_id)

    def clear_table_context(self, session_id: str):
        """
        清除会话的表上下文
        Args:
            session_id: 会话ID
        """
        if session_id in self.table_contexts:
            del self.table_contexts[session_id]
    
    async def chat_stream(
        self,
        session_id: str,
        message: str,
        agent_type: str = "chat",
        table_context: Optional[Dict] = None
    ):
        """
        流式对话
        Args:
            session_id: 会话ID
            message: 用户消息
            agent_type: Agent类型
            table_context: 表上下文
        Yields:
            响应内容片段
        """
        import asyncio

        # 获取指定的Agent
        agent = agent_manager.get_agent(agent_type)
        if not agent:
            yield f"错误: 未找到类型为 '{agent_type}' 的Agent"
            return

        history = self.get_or_create_conversation(session_id)

        # 转换历史消息格式为字典列表
        history_dicts = []
        for msg in history:
            if isinstance(msg, HumanMessage):
                history_dicts.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history_dicts.append({"role": "assistant", "content": msg.content})

        try:
            # 在后台线程中执行Agent的stream方法
            def run_stream():
                return list(agent.stream(message, history_dicts, table_context=table_context))

            chunks = await asyncio.to_thread(run_stream)

            # 组合完整响应
            response = ''.join(chunks)

            # 保存到历史
            self.add_message(session_id, "user", message)
            self.add_message(session_id, "assistant", response)

            # 流式输出
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.03)  # 控制速度

        except Exception as e:
            error_msg = f"处理请求时发生错误: {str(e)}"
            yield error_msg
    
    def chat(
        self,
        session_id: str,
        message: str,
        agent_type: str = "chat",
        table_context: Optional[Dict] = None
    ) -> Dict:
        """
        同步对话（用于非流式场景）
        Args:
            session_id: 会话ID
            message: 用户消息
            agent_type: Agent类型
            table_context: 表上下文
        Returns:
            响应字典
        """
        # 获取指定的Agent
        agent = agent_manager.get_agent(agent_type)
        if not agent:
            return {
                "success": False,
                "output": f"错误: 未找到类型为 '{agent_type}' 的Agent",
                "error": "Agent not found"
            }

        history = self.get_or_create_conversation(session_id)

        # 转换历史消息格式
        history_dicts = []
        for msg in history:
            if isinstance(msg, HumanMessage):
                history_dicts.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history_dicts.append({"role": "assistant", "content": msg.content})

        try:
            response = agent.invoke(message, history_dicts, table_context=table_context)

            # 保存到历史
            self.add_message(session_id, "user", message)
            self.add_message(session_id, "assistant", response)

            return {
                "success": True,
                "output": response,
                "intermediate_steps": []
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "error": str(e)
            }

    def get_agents_info(self) -> List[Dict]:
        """
        获取所有Agent信息
        Returns:
            Agent列表
        """
        return agent_manager.get_all_agents()

    def get_tools_info(self) -> List[Dict]:
        """
        获取智慧报表数据助手的工具信息
        Returns:
            工具列表
        """
        agent = agent_manager.get_agent("chatbi")
        if agent and hasattr(agent, 'get_tool_descriptions'):
            return agent.get_tool_descriptions()
        return []


# 创建全局服务实例
conversation_service = ConversationService()