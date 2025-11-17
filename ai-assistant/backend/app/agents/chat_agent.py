"""
聊天 Agent
"""
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Dict, Any
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from tools.time_tool import get_current_time, get_date_info
from tools.calculator_tool import calculate
from tools.search_tool import search_web
from tools.wangwei_info import wangwei_info



class ChatAgent:
    """聊天Agent类"""
    
    def __init__(self):
        """初始化Agent"""
        self.llm = ChatTongyi(
            model=settings.QWEN_MODEL,
            temperature=settings.QWEN_TEMPERATURE,
            max_tokens=settings.QWEN_MAX_TOKENS,
        )
        
        # 定义可用工具
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
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
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
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个智能助手，名字叫"小智"。你可以帮助用户完成各种任务。

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

记住：你是一个有帮助、诚实、无害的助手。

返回结果要求：
1. 所有的返回结果都按照标准的三段式结果进行返回。
2. 如果使用了工具，在返回结果中第一段说明使用的工具，第二段说明工具返回结果，第三段说明其他补充信息。
3. 如果没有使用工具，在返回结果中第一段说明未使用工具，第二段说明未使用工具，第三段说明其他补充信息。
4. 遇到无法回答的问题时，需礼貌地告知用户，并提供相关信息或建议。

"""
    
    def chat(self, message: str, chat_history: List = None) -> Dict[str, Any]:
        """
        处理对话
        
        Args:
            message: 用户消息
            chat_history: 对话历史
        
        Returns:
            包含回答和中间步骤的字典
        """
        if chat_history is None:
            chat_history = []
        
        try:
            # 只保留最近的对话历史（避免上下文过长）
            recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
            
            # 调用Agent
            result = self.agent_executor.invoke({
                "input": message,
                "chat_history": recent_history
            })
            
            return {
                "success": True,
                "output": result['output'],
                "intermediate_steps": result.get('intermediate_steps', [])
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