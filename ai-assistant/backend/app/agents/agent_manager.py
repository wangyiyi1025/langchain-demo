"""
Agent管理器 - 负责管理所有Agent实例
"""
from typing import Dict, List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent


class AgentManager:
    """Agent管理器，负责Agent的注册、获取和管理"""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """
        注册一个Agent
        Args:
            agent: Agent实例
        """
        agent_type = agent.get_agent_type()
        if agent_type in self._agents:
            print(f"警告: Agent类型 '{agent_type}' 已存在，将被覆盖")
        self._agents[agent_type] = agent
        print(f"已注册Agent: {agent.get_agent_name()} (类型: {agent_type})")

    def get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """
        根据类型获取Agent
        Args:
            agent_type: Agent类型标识
        Returns:
            BaseAgent: Agent实例，如果不存在则返回None
        """
        return self._agents.get(agent_type)

    def get_all_agents(self) -> List[Dict]:
        """
        获取所有Agent的信息
        Returns:
            List[Dict]: Agent信息列表
        """
        return [agent.get_info() for agent in self._agents.values()]

    def has_agent(self, agent_type: str) -> bool:
        """
        检查是否存在指定类型的Agent
        Args:
            agent_type: Agent类型标识
        Returns:
            bool: 是否存在
        """
        return agent_type in self._agents

    def get_agent_count(self) -> int:
        """
        获取已注册Agent的数量
        Returns:
            int: Agent数量
        """
        return len(self._agents)


# 全局Agent管理器实例
agent_manager = AgentManager()
