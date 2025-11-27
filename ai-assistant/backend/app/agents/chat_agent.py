"""
通用聊天Agent - 不包含数据分析功能
"""
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Dict, Any, Optional
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import settings
from app.tools.time_tool import get_current_time, get_date_info
from app.tools.calculator_tool import calculate
from app.tools.search_tool import search_web
from app.tools.wangwei_info import wangwei_info
from app.agents.base_agent import BaseAgent


class ChatAgent(BaseAgent):
    """聊天Agent类"""
    
    def __init__(self):
        """初始化Agent"""
        super().__init__()

        self.llm = ChatTongyi(
            model=settings.QWEN_MODEL,
            temperature=settings.QWEN_TEMPERATURE,
            max_tokens=settings.QWEN_MAX_TOKENS,
            max_retries=settings.QWEN_MAX_RETRIES,
            dashscope_api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL
        )

        # 定义通用工具（移除了ChatBI工具）
        self.tools = [
            get_current_time,
            get_date_info,
            calculate,
            search_web,
            wangwei_info,
        ]

        # 创建提示词模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 创建Agent
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)

        # 创建Agent执行器
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=settings.AGENT_VERBOSE,
            handle_parsing_errors=True,
            max_iterations=settings.AGENT_MAX_ITERATIONS,
        )

    def get_agent_type(self) -> str:
        return "chat"

    def get_agent_name(self) -> str:
        return "通用聊天助手"

    def get_agent_description(self) -> str:
        return "智能聊天助手，可以帮助您查询时间、进行计算、搜索信息等。适用于日常对话和通用任务。"
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个智能助手，名字叫"小智"。你可以帮助用户完成各种日常任务和通用查询。

你拥有以下工具：

1. **时间相关**
   - get_current_time: 获取当前时间（可指定时区）
   - get_date_info: 获取详细的日期信息

2. **计算相关**
   - calculate: 计算数学表达式（支持基础运算和数学函数）

3. **信息查询**
   - search_web: 搜索网络信息
   - wangwei_info: 查询王唯信息

使用指南：
- 根据用户需求选择合适的工具
- 如果一个工具不够，可以组合使用多个工具
- 用友好、专业的语气回答问题
- 如果不确定，可以询问用户更多信息
- 始终使用中文回答
- 如果用户需要进行数据库查询或数据分析，请建议他们切换到ChatBI数据分析助手

记住：你是一个有帮助、诚实、无害的助手。

返回结果要求：
1. 所有的返回结果都按照标准的三段式结果进行返回。
2. 如果使用了工具，在返回结果中第一段说明使用的工具，第二段说明工具返回结果，第三段说明其他补充信息。
3. 如果没有使用工具，在返回结果中第一段说明未使用工具，第二段说明未使用工具，第三段说明其他补充信息。
4. 遇到无法回答的问题时，需礼貌地告知用户，并提供相关信息或建议。

"""
    
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
        # 格式化对话历史
        formatted_history = []
        if chat_history:
            formatted_history = self.format_chat_history(chat_history[-6:])  # 只保留最近6条

        try:
            result = self.agent_executor.invoke({
                "input": message,
                "chat_history": formatted_history
            })
            return result.get("output", "抱歉，我无法生成回复。")
        except Exception as e:
            return f"处理您的请求时发生错误: {str(e)}"

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
        # 格式化对话历史
        formatted_history = []
        if chat_history:
            formatted_history = self.format_chat_history(chat_history[-6:])

        try:
            result = self.agent_executor.invoke({
                "input": message,
                "chat_history": formatted_history
            })

            response = result.get("output", "抱歉，我无法生成回复。")

            # 模拟流式输出
            chunk_size = 5
            for i in range(0, len(response), chunk_size):
                yield response[i:i + chunk_size]

        except Exception as e:
            yield f"处理您的请求时发生错误: {str(e)}"

    def chat(self, message: str, chat_history: List = None) -> Dict[str, Any]:
        """
        处理对话（兼容旧接口）
        Args:
            message: 用户消息
            chat_history: 对话历史
        Returns:
            包含回答和中间步骤的字典
        """
        if chat_history is None:
            chat_history = []

        try:
            response = self.invoke(message, chat_history)
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

    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """
        获取所有工具的描述
        Returns:
            工具描述列表
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self.tools
        ]