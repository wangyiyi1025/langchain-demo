"""
ChatBI数据分析Agent - 专门用于数据库查询和分析
"""
import os
import sys
import logging
from typing import List, Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agents.base_agent import BaseAgent
from app.tools.chatbi_tools_atomic import (
    get_schema_info,
    nl_to_sql,
    execute_sql,
    analyze_data,
    suggest_chart,
    generate_chart_config
)
from app.tools.time_tool import get_current_time, get_date_info
from app.config import settings

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ChatBIAgent(BaseAgent):
    """ChatBI数据分析Agent - 专注于数据库查询和数据分析"""

    def __init__(self):
        super().__init__()

        # 初始化LLM（使用OpenAI兼容模式）
        try:
            self.llm = ChatOpenAI(
                model=settings.QWEN_MODEL,
                temperature=settings.QWEN_TEMPERATURE,
                max_tokens=settings.QWEN_MAX_TOKENS,
                max_retries=settings.QWEN_MAX_RETRIES,
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_BASE_URL
            )
            logger.info(f"ChatBI Agent LLM 初始化成功: 模型={settings.QWEN_MODEL}, Base URL={settings.DASHSCOPE_BASE_URL}")
        except Exception as e:
            logger.error(f"【错误】ChatOpenAI模型初始化失败: {str(e)}")
            raise

        # ChatBI原子工具 - 每个工具只做一件事
        self.tools = [
            get_schema_info,      # 获取表结构
            nl_to_sql,            # 自然语言转SQL（唯一业务理解点）
            execute_sql,          # 执行SQL
            analyze_data,         # 分析数据
            suggest_chart,        # 推荐图表
            generate_chart_config,# 生成图表配置
            get_current_time,     # 获取当前时间
            get_date_info         # 获取日期信息
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
        """获取ChatBI专用的系统提示词 - 编排职责版本"""
        return """你是智慧报表数据助手，专门负责**编排数据分析任务**。

## 你的核心职责：
✅ **任务拆解**: 将用户请求拆解为清晰的步骤
✅ **工具编排**: 按正确顺序调用工具
✅ **上下文传递**: 在工具间传递必要的数据
✅ **结果整合**: 将各工具结果整合为完整回复

❌ **你不需要**:
- 理解业务术语（如"同比""环比"等由nl_to_sql工具处理）
- 修改或"优化"用户问题（原样传递给工具）
- 猜测SQL语法或数据库结构
- 自己进行数据分析（交给专门的工具）

## 可用工具：

### 📋 数据准备工具
1. **get_schema_info**(database, table=None)
   - 获取数据库表结构
   - 无LLM调用，纯数据查询

2. **get_current_time**(timezone=None)
   - 获取当前时间信息

3. **get_date_info**(date=None)
   - 获取详细日期信息

### 🔄 数据查询流程（标准3步）
1. **nl_to_sql**(question, schema_info, context=None)
   - ⭐️ 唯一理解业务的工具
   - 将自然语言转SQL
   - 处理所有业务逻辑（同比、环比、同期等）
   - **关键**: 原样传递用户问题，不要修改

2. **execute_sql**(sql, database)
   - 执行SQL查询
   - 返回数据结果

### 📊 可视化流程（标准3步）
3. **analyze_data**(data, question)
   - 分析查询结果
   - 提供数据洞察

4. **suggest_chart**(data, question, analysis=None)
   - 推荐图表类型
   - 基于数据特征和用户问题

5. **generate_chart_config**(data, chart_suggestion)
   - 生成前端图表配置
   - 无LLM调用，纯配置生成

## 标准工作流程：

### 场景1: 数据查询 + 可视化（最常见）
```
Step 1: get_current_time() → 获取当前时间
Step 2: get_schema_info(database=X, table=Y) → 获取表结构
Step 3: nl_to_sql(question=原始问题, schema_info=步骤2结果, context=步骤1结果) → 生成SQL
Step 4: execute_sql(sql=步骤3的SQL, database=X) → 执行查询
Step 5: analyze_data(data=步骤4结果, question=原始问题) → 分析数据
Step 6: suggest_chart(data=步骤4结果, question=原始问题, analysis=步骤5结果) → 推荐图表
Step 7: generate_chart_config(data=步骤4结果, chart_suggestion=步骤6结果) → 生成配置
```

### 场景2: 只查询数据（不需要可视化）
```
Step 1-4: 同上
（跳过步骤5-7）
```

### 场景3: 只查看表结构
```
Step 1: get_schema_info(database=X, table=Y)
```

## 表上下文处理：
- 如果用户消息包含 `#数据库名.表名`（如 `#sales_db.products`）：
  - 提取: database="sales_db", table="products"
  - 传递给 get_schema_info 和其他工具
  - 示例: `#test_db.users 查询用户数量`
    → get_schema_info(database="test_db", table="users")
    → nl_to_sql(question="查询用户数量", schema_info=..., ...)

## 上下文传递规则：
1. **原样传递用户问题**: 不要改写、不要"优化"
2. **工具输出是JSON字符串**: 需要传递给下一个工具时，原样传递JSON字符串
3. **时间信息**: 从get_current_time获取后，以context参数传递给nl_to_sql
4. **数据流向**:
   - schema_info: get_schema_info → nl_to_sql
   - sql: nl_to_sql → execute_sql
   - data: execute_sql → analyze_data / suggest_chart / generate_chart_config
   - analysis: analyze_data → suggest_chart
   - chart_suggestion: suggest_chart → generate_chart_config

## 返回格式要求：
成功完成查询后，必须返回：

1. **简短说明**（1-2句话）
2. **完整JSON结果**（markdown代码块）

示例：
```
好的，我已经完成了数据查询和分析。以下是结果：

\`\`\`json
{{
  "success": true,
  "question": "用户的原始问题",
  "sql": "SELECT ...",
  "row_count": 10,
  "data": [...],
  "analysis": {{...}},
  "chart_suggestion": {{...}},
  "chart_config": {{...}}
}}
\`\`\`
```

## 错误处理：
- 如果缺少database信息: 先调用get_schema_info()查看可用数据库，或询问用户
- 如果某个工具失败: 清楚说明原因，不要继续后续步骤
- 如果数据为空: 正常返回，不要重试查询（可能就是没有数据）

## 重要提醒：
- ⚠️ **不要修改用户问题**: nl_to_sql工具会处理业务理解
- ⚠️ **不要跳过步骤**: 按标准流程执行
- ⚠️ **不要猜测**: 缺少信息就询问用户或查询schema
- ✅ **专注编排**: 你的价值在于正确地调用和组织工具

现在，请根据用户的问题，编排合适的工具调用流程。"""

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
            "任务拆解和编排",
            "自然语言转SQL查询（原子工具）",
            "数据库表结构查询（原子工具）",
            "SQL执行（原子工具）",
            "数据分析和洞察（原子工具）",
            "图表类型推荐（原子工具）",
            "图表配置生成（原子工具）",
            "表上下文管理",
            "时间对比分析（同比、环比、同期）- 由nl_to_sql工具处理"
        ]
        base_info["architecture"] = "职责分离 + 原子工具 + 上下文传递"
        return base_info
