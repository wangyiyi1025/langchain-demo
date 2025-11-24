"""
Agent基类定义
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage


class BaseAgent(ABC):
    """Agent基类，所有Agent都需要继承此类"""

    def __init__(self):
        self.agent_type = self.get_agent_type()
        self.agent_name = self.get_agent_name()
        self.agent_description = self.get_agent_description()

    @abstractmethod
    def get_agent_type(self) -> str:
        """
        获取Agent类型标识
        Returns:
            str: Agent类型标识（如 'chat', 'chatbi'）
        """
        pass

    @abstractmethod
    def get_agent_name(self) -> str:
        """
        获取Agent名称
        Returns:
            str: Agent名称
        """
        pass

    @abstractmethod
    def get_agent_description(self) -> str:
        """
        获取Agent描述
        Returns:
            str: Agent描述
        """
        pass

    @abstractmethod
    def invoke(self, message: str, chat_history: Optional[List] = None, **kwargs) -> str:
        """
        同步调用Agent处理消息
        Args:
            message: 用户消息
            chat_history: 对话历史
            **kwargs: 其他参数
        Returns:
            str: Agent响应
        """
        pass

    @abstractmethod
    def stream(self, message: str, chat_history: Optional[List] = None, **kwargs):
        """
        流式调用Agent处理消息
        Args:
            message: 用户消息
            chat_history: 对话历史
            **kwargs: 其他参数
        Yields:
            str: Agent响应片段
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """
        获取Agent信息
        Returns:
            Dict: Agent信息字典
        """
        return {
            "type": self.agent_type,
            "name": self.agent_name,
            "description": self.agent_description,
        }

    def format_chat_history(self, chat_history: List[Dict]) -> List:
        """
        格式化对话历史为LangChain消息格式
        Args:
            chat_history: 对话历史列表
        Returns:
            List: LangChain消息列表
        """
        formatted_history = []
        for msg in chat_history:
            if msg["role"] == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                formatted_history.append(AIMessage(content=msg["content"]))
        return formatted_history
