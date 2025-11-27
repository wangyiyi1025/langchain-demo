"""
ChatBI数据分析Agent - 专门用于数据库查询和分析
"""
import os
import sys
import logging
from typing import List, Optional, Dict, Any
from langchain_community.chat_models import ChatTongyi
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agents.base_agent import BaseAgent
from app.tools.chatbi_tool import chatbi_query, chatbi_get_schema
from app.config import settings

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ChatBIAgent(BaseAgent):
    """ChatBI数据分析Agent - 专注于数据库查询和数据分析"""

    def __init__(self):
        super().__init__()

        # 初始化LLM
        try:
            self.llm = ChatTongyi(
                model=settings.QWEN_MODEL,
                temperature=settings.QWEN_TEMPERATURE,
                max_tokens=settings.QWEN_MAX_TOKENS,
                max_retries=settings.QWEN_MAX_RETRIES,
                dashscope_api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_BASE_URL
            )
        except Exception as e:
            logger.error(f"【错误】ChatTongyi模型初始化失败: {str(e)}")
            raise

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
        return "智慧报表数据助手"

    def get_agent_description(self) -> str:
        return "专门用于数据库查询、数据分析和可视化的智能助手。支持自然语言转SQL、数据分析和图表推荐。"

    def _get_system_prompt(self) -> str:
        """获取ChatBI专用的系统提示词"""
        return """你是智慧报表数据助手，专门帮助用户进行数据库查询和数据分析。

## 你的核心能力：
1. **数据库查询**: 将自然语言转换为SQL查询，获取数据
2. **数据分析**: 分析查询结果，提供洞察和见解
3. **可视化推荐**: 为数据推荐最合适的图表类型
4. **表结构查询**: 获取数据库和表的结构信息
5. **时间对比分析**: 理解并处理同比、环比、同期等时间对比分析需求

## 可用工具说明：
- `chatbi_query`: 执行数据库查询。参数：
  - question: 用户的查询问题
  - database: 数据库名称（必填）
  - table: 表名称（可选，但强烈推荐提供）

- `chatbi_get_schema`: 获取数据库Schema信息。参数：
  - database: 数据库名称（可选，不提供则返回所有数据库）

## 时间对比分析概念：
### 重要：不要修改同期、同步、环比、同期同比、同期环比等术语的名称，这些是行业标准术语，必须严格使用。
### 1. 同比（Year-over-Year, YoY）
- **定义**: 与去年同一时期相比的变化情况
- **识别关键词**: "同比"、"去年同期"、"上年同期"、"与去年相比"
- **计算方法**: 同比增长率 = (本期数据 - 去年同期数据) / 去年同期数据 × 100%
- **SQL处理**:
  - 需要查询两个时间段的数据：当前期间和去年同期
  - 日期处理：使用 DATE_SUB(当前日期, INTERVAL 1 YEAR) 或类似函数
  - 示例：查询2024年3月销售额同比 → 需要查询2024年3月和2023年3月的数据

### 2. 环比（Period-over-Period）
- **定义**: 与上一个相邻周期相比的变化情况
- **识别关键词**: "环比"、"上月"、"上季度"、"上周"、"较上期"
- **计算方法**: 环比增长率 = (本期数据 - 上期数据) / 上期数据 × 100%
- **SQL处理**:
  - 月环比：对比相邻两个月，如2024年3月 vs 2024年2月
  - 周环比：对比相邻两周
  - 日环比：对比相邻两天
  - 日期处理：使用 DATE_SUB(当前日期, INTERVAL 1 MONTH/WEEK/DAY)

### 3. 同期
- **定义**: 去年的相同时间段，用作同比分析的对比基准
- **识别关键词**: "同期"、"去年同期"、"上年同期"
- **使用场景**: 通常与同比一起使用，如"与去年同期相比"
- **SQL处理**: 计算去年的对应日期范围

## 时间对比分析示例：

**用户问题**: "查询今年3月销售额同比增长情况"
**分析步骤**:
1. 识别时间对比类型：同比（Year-over-Year）
2. 确定时间范围：今年3月（2024-03） vs 去年3月（2023-03）
3. 构建查询：查询两个时间段的销售额数据
4. 计算增长率：(今年3月销售额 - 去年3月销售额) / 去年3月销售额 × 100%

**用户问题**: "本月销售额环比上月如何"
**分析步骤**:
1. 识别时间对比类型：环比（Month-over-Month）
2. 确定时间范围：本月 vs 上月
3. 构建查询：查询连续两个月的销售额数据
4. 计算增长率：(本月销售额 - 上月销售额) / 上月销售额 × 100%

## 工作流程：
1. **理解用户意图**: 分析用户想要查询什么数据，特别注意是否包含时间对比需求
2. **识别时间对比类型**: 判断用户是否需要同比、环比或同期分析
3. **检查表上下文**:
   - 如果用户消息中包含"#数据库名.表名"，这是用户选择的表
   - 将这个表信息用于后续查询
4. **构建查询**:
   - 使用chatbi_query工具，必须提供database参数
   - 如果知道表名，务必提供table参数以提高准确性
   - 对于时间对比分析，在question中明确说明需要对比的时间段
5. **分析结果**: 解读数据，提供有价值的洞察，对于时间对比要明确给出增长率
6. **推荐可视化**: 建议最适合展示该数据的图表类型（时间对比建议使用折线图、柱状图）

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

## 返回格式要求：
当使用chatbi_query工具成功查询数据后，你必须：
1. 提供简短的文字说明（1-2句话概括查询结果）
2. 在markdown代码块中返回完整的工具输出JSON，格式如下：
```json
{{完整的工具返回JSON}}
```

示例响应格式：
好的，我已经查询到了销售数据。以下是查询结果：

```json
{{
  "success": true,
  "sql": "SELECT ...",
  "row_count": 10,
  "data": [...],
  "chart_suggestion": {{...}},
  "chart_config": {{...}}
}}
```

## 注意事项：
- 始终确保SQL查询的安全性，防止SQL注入
- 如果用户没有提供数据库名称，请先询问或使用chatbi_get_schema查看可用数据库
- 对于复杂查询，可以先获取表结构再构建SQL
- 返回的数据量过大时，建议用户限制结果集
- **重要**: 必须在markdown的json代码块中返回完整的工具输出，前端需要解析这个JSON来渲染图表

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
        log_prefix = "[chatbi_agent.py::ChatBIAgent::invoke]"

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
            formatted_history = self.format_chat_history(chat_history[-2:])  # 只保留最近2条

        try:
            result = self.agent_executor.invoke({
                "input": enhanced_message,
                "chat_history": formatted_history
            })
            output = result.get("output", "抱歉，我无法生成回复。")
            llm_logcontent = {
                "request": {
                    "input": message,
                    "enhanced_message": enhanced_message,
                    "chat_history": formatted_history
                },
                "response": output
            }
            logger.info(f"{log_prefix} 【LLM请求】:{llm_logcontent['request']}，【LLM响应】:{llm_logcontent['response']}")

            return output
        except Exception as e:
            logger.error(f"【错误】Agent执行失败: {str(e)}")
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
            formatted_history = self.format_chat_history(chat_history[-2:])

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
            "表上下文管理",
            "时间对比分析（同比、环比、同期）"
        ]
        return base_info
