"""
ChatBI数据分析Agent - 专门用于数据库查询和分析
"""
import os
import sys
from typing import List, Optional, Dict, Any
from langchain_community.chat_models import ChatTongyi
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from tools.chatbi_tool import chatbi_query, chatbi_get_schema


class ChatBIAgent(BaseAgent):
    """ChatBI数据分析Agent - 专注于数据库查询和数据分析"""

    def __init__(self):
        super().__init__()

        # 初始化LLM
        self.llm = ChatTongyi(
            model=os.getenv("QWEN_MODEL", "qwen-plus"),
            temperature=float(os.getenv("QWEN_TEMPERATURE", "0.3")),  # 数据分析需要更精确
            max_tokens=int(os.getenv("QWEN_MAX_TOKENS", "2000")),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )

        # ChatBI专用工具
        self.tools = [
            chatbi_query,
            chatbi_get_schema
        ]

        # 创建ChatBI专用的系统提示词
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 创建Agent
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)

        # 配置AgentExecutor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

    def get_agent_type(self) -> str:
        return "chatbi"

    def get_agent_name(self) -> str:
        return "ChatBI数据分析助手"

    def get_agent_description(self) -> str:
        return "专门用于数据库查询、数据分析和可视化的智能助手。支持自然语言转SQL、数据分析和图表推荐。"

    def _get_system_prompt(self) -> str:
        """获取ChatBI专用的系统提示词"""
        return """你是ChatBI数据分析助手，专门帮助用户进行数据库查询和数据分析。

## 你的核心能力：
1. **数据库查询**: 将自然语言转换为SQL查询，获取数据
2. **数据分析**: 分析查询结果，提供洞察和见解
3. **可视化推荐**: 为数据推荐最合适的图表类型
4. **表结构查询**: 获取数据库和表的结构信息

## 可用工具说明：
- `chatbi_query`: 执行数据库查询。参数：
  - question: 用户的查询问题
  - database: 数据库名称（必填）
  - table: 表名称（可选，但强烈推荐提供）

- `chatbi_get_schema`: 获取数据库Schema信息。参数：
  - database: 数据库名称（可选，不提供则返回所有数据库）

## 工作流程：
1. **理解用户意图**: 分析用户想要查询什么数据
2. **检查表上下文**:
   - 如果用户消息中包含"#数据库名.表名"，这是用户选择的表
   - 将这个表信息用于后续查询
3. **构建查询**:
   - 使用chatbi_query工具，必须提供database参数
   - 如果知道表名，务必提供table参数以提高准确性
4. **分析结果**: 解读数据，提供有价值的洞察
5. **推荐可视化**: 建议最适合展示该数据的图表类型

## 表上下文处理规则：
- 用户输入中的"#数据库名.表名"表示当前选择的表
- 提取表信息后，在调用chatbi_query时使用这个表
- 示例：用户输入"#test_db.users 查询用户数量"
  → 应调用: chatbi_query(question="查询用户数量", database="test_db", table="users")

## 响应要求：
1. **简洁清晰**: 用通俗易懂的语言解释查询结果
2. **数据驱动**: 基于实际数据提供分析，不要猜测
3. **可视化建议**: 如果数据适合可视化，明确推荐图表类型
4. **错误处理**: 如果查询失败，清楚地说明原因并建议解决方案

## 注意事项：
- 始终确保SQL查询的安全性，防止SQL注入
- 如果用户没有提供数据库名称，请先询问或使用chatbi_get_schema查看可用数据库
- 对于复杂查询，可以先获取表结构再构建SQL
- 返回的数据量过大时，建议用户限制结果集

现在，请根据用户的问题，使用上述工具帮助他们进行数据分析。"""

    def _extract_table_context(self, message: str) -> tuple[str, Optional[str], Optional[str]]:
        """
        从消息中提取表上下文信息
        Args:
            message: 用户消息
        Returns:
            tuple: (清理后的消息, 数据库名, 表名)
        """
        import re

        # 匹配 #database.table 或 #database.table_name 格式
        pattern = r'#(\w+)\.(\w+)'
        match = re.search(pattern, message)

        if match:
            database = match.group(1)
            table = match.group(2)
            # 移除表标记，保留查询问题
            clean_message = re.sub(pattern, '', message).strip()
            return clean_message, database, table

        return message, None, None

    def invoke(self, message: str, chat_history: Optional[List] = None, **kwargs) -> str:
        """
        同步调用Agent处理消息
        Args:
            message: 用户消息（可能包含#database.table）
            chat_history: 对话历史
            **kwargs: 其他参数（可包含table_context）
        Returns:
            str: Agent响应
        """
        # 从kwargs中获取表上下文，或从消息中提取
        table_context = kwargs.get('table_context')

        if table_context:
            # 如果提供了表上下文，在消息前添加
            enhanced_message = f"#{table_context['database']}.{table_context['table']} {message}"
        else:
            enhanced_message = message

        # 格式化对话历史
        formatted_history = []
        if chat_history:
            formatted_history = self.format_chat_history(chat_history[-6:])  # 只保留最近6条

        try:
            result = self.agent_executor.invoke({
                "input": enhanced_message,
                "chat_history": formatted_history
            })
            return result.get("output", "抱歉，我无法生成回复。")
        except Exception as e:
            return f"处理您的请求时发生错误: {str(e)}"

    def stream(self, message: str, chat_history: Optional[List] = None, **kwargs):
        """
        流式调用Agent处理消息
        Args:
            message: 用户消息（可能包含#database.table）
            chat_history: 对话历史
            **kwargs: 其他参数（可包含table_context）
        Yields:
            str: Agent响应片段
        """
        # 从kwargs中获取表上下文
        table_context = kwargs.get('table_context')

        if table_context:
            enhanced_message = f"#{table_context['database']}.{table_context['table']} {message}"
        else:
            enhanced_message = message

        # 格式化对话历史
        formatted_history = []
        if chat_history:
            formatted_history = self.format_chat_history(chat_history[-6:])

        try:
            result = self.agent_executor.invoke({
                "input": enhanced_message,
                "chat_history": formatted_history
            })

            response = result.get("output", "抱歉，我无法生成回复。")

            # 模拟流式输出
            chunk_size = 5
            for i in range(0, len(response), chunk_size):
                yield response[i:i + chunk_size]

        except Exception as e:
            yield f"处理您的请求时发生错误: {str(e)}"

    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息，包含工具列表"""
        base_info = super().get_info()
        base_info["tools"] = [tool.name for tool in self.tools]
        base_info["capabilities"] = [
            "自然语言转SQL查询",
            "数据库表结构查询",
            "数据分析和洞察",
            "图表类型推荐",
            "表上下文管理"
        ]
        return base_info
