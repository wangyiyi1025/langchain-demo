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

    async def chat_stream_with_steps(
        self,
        session_id: str,
        message: str,
        agent_type: str = "chat",
        table_context: Optional[Dict] = None,
        step_callback = None
    ):
        """
        流式对话（带步骤可见性）
        Args:
            session_id: 会话ID
            message: 用户消息
            agent_type: Agent类型
            table_context: 表上下文
            step_callback: 步骤回调函数，用于实时发送步骤信息
        Yields:
            dict: 包含类型和内容的消息字典
                - {"type": "step", "data": {...}}  # 步骤信息
                - {"type": "chunk", "data": "..."}  # 响应片段
                - {"type": "error", "data": "..."}  # 错误信息
        """
        import asyncio
        import json

        # 获取指定的Agent
        agent = agent_manager.get_agent(agent_type)
        if not agent:
            yield {"type": "error", "data": f"错误: 未找到类型为 '{agent_type}' 的Agent"}
            return

        # 检查agent是否支持步骤可见性
        if not hasattr(agent, 'invoke_with_steps'):
            yield {"type": "error", "data": f"Agent '{agent_type}' 不支持步骤可见性功能"}
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
            # 在后台线程中执行Agent的invoke_with_steps方法
            def run_with_steps():
                return agent.invoke_with_steps(message, history_dicts, table_context=table_context)

            # 使用asyncio.to_thread在后台执行
            response, steps = await asyncio.to_thread(run_with_steps)

            # 先发送所有步骤信息
            for step in steps:
                step_msg = {
                    "type": "step",
                    "data": {
                        "step_number": step.get("step_number"),
                        "tool_name": step.get("tool_name"),
                        "status": step.get("status"),
                        "input": step.get("input", ""),
                        "output_preview": step.get("output_preview", ""),
                        "duration_ms": step.get("duration_ms", 0),
                        "error": step.get("error")
                    }
                }
                yield step_msg
                # 如果提供了回调函数，也调用它
                if step_callback:
                    await step_callback(step_msg)
                await asyncio.sleep(0.05)  # 给前端一点时间处理

            # 保存到历史
            self.add_message(session_id, "user", message)
            self.add_message(session_id, "assistant", response)

            # 流式输出最终响应
            chunk_size = 5
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                yield {"type": "chunk", "data": chunk}
                await asyncio.sleep(0.03)  # 控制速度

        except Exception as e:
            error_msg = f"处理请求时发生错误: {str(e)}"
            yield {"type": "error", "data": error_msg}
    
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