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
from app.tools.chatbi_chains import (
    chatbi_query_only_chain,
    chatbi_query_with_analysis_chain,
    chatbi_query_with_chart_chain,
    chatbi_full_analysis_chain
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
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                max_retries=settings.LLM_MAX_RETRIES,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
            logger.info(f"ChatBI Agent LLM 初始化成功: provider={settings.LLM_PROVIDER}, model={settings.LLM_MODEL}, base_url={settings.OPENAI_BASE_URL}")
        except Exception as e:
            logger.error(f"【错误】ChatOpenAI模型初始化失败: {str(e)}")
            raise

        # ChatBI工具：预定义链（快速） + 原子工具（灵活）
        self.tools = [
            # ⚡️ 预定义工具链 - 快速执行标准流程（推荐优先使用）
            chatbi_query_only_chain,           # 场景1: 只查询（2次LLM）
            chatbi_query_with_analysis_chain,  # 场景2: 查询+分析（3次LLM）
            chatbi_query_with_chart_chain,     # 场景3: 查询+可视化（3次LLM）
            chatbi_full_analysis_chain,        # 场景4: 查询+分析+可视化（4次LLM）

            # 🔧 原子工具 - 灵活组合（复杂场景使用）
            get_schema_info,      # 获取表结构
            nl_to_sql,            # 自然语言转SQL（唯一业务理解点）
            execute_sql,          # 执行SQL
            analyze_data,         # 分析数据
            suggest_chart,        # 推荐图表
            generate_chart_config,# 生成图表配置

            # 📅 辅助工具
            get_current_time,     # 获取当前时间
            get_date_info         # 获取日期信息
        ]

        # 创建 Tool Calling Agent
        logger.info("正在创建 ChatBI Agent（Tool Calling）")

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        logger.info("✓ Tool Calling Agent 创建成功")

        # 配置 AgentExecutor（使用配置文件中的参数）
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=settings.AGENT_VERBOSE,
            handle_parsing_errors=settings.AGENT_HANDLE_PARSING_ERRORS,
            max_iterations=settings.AGENT_MAX_ITERATIONS
        )

        logger.info(f"✓ AgentExecutor 配置完成: verbose={settings.AGENT_VERBOSE}, "
                   f"max_iterations={settings.AGENT_MAX_ITERATIONS}, "
                   f"handle_parsing_errors={settings.AGENT_HANDLE_PARSING_ERRORS}")

    def get_agent_type(self) -> str:
        return "chatbi"

    def get_agent_name(self) -> str:
        return "智慧报表数据助手"

    def get_agent_description(self) -> str:
        return "专门用于数据库查询、数据分析和可视化的智能助手。支持自然语言转SQL、数据分析和图表推荐。"

    def _get_system_prompt(self) -> str:
        """获取ChatBI专用的系统提示词 - 精简版本"""
        return """你是数据助手，负责调用工具完成数据查询和分析任务。

## 可用工具

### 预定义工具链（优先使用）
1. **chatbi_query_only_chain**(question, database, table=None) - 只查询
2. **chatbi_query_with_analysis_chain**(question, database, table=None) - 查询+分析
3. **chatbi_query_with_chart_chain**(question, database, table=None) - 查询+可视化
4. **chatbi_full_analysis_chain**(question, database, table=None) - 查询+分析+可视化

### 原子工具（特殊情况使用）
- **get_schema_info**(database, table=None) - 查看表结构
- **nl_to_sql**(question, schema_info) - 生成SQL
- **execute_sql**(sql, database) - 执行SQL
- **analyze_data**(data, question) - 分析数据
- **suggest_chart**(data, question) - 推荐图表
- **generate_chart_config**(data, chart_suggestion) - 生成图表配置

## 工具选择
- 只查询 → chatbi_query_only_chain
- 查询+分析 → chatbi_query_with_analysis_chain
- 查询+可视化 → chatbi_query_with_chart_chain
- 查询+分析+可视化 → chatbi_full_analysis_chain
- 查看表结构 → get_schema_info

## 返回格式（必须严格遵守）

工具调用完成后，必须返回：

1. 简短说明（1句话）
2. 完整JSON结果（必须用markdown代码块包裹）

示例：
```
查询完成，返回10条数据。

\`\`\`json
{{
  "success": true,
  "question": "...",
  "sql": "SELECT ...",
  "row_count": 10,
  "data": [...],
  "chart_config": {{...}}
}}
\`\`\`
```

**关键点：**
- 必须包含完整JSON
- 不要修改工具返回的结果
- 不要只返回文字说明"""

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

        try:
            # 构建输入
            agent_input = {"input": enhanced_message}

            # 添加对话历史
            if chat_history:
                formatted_history = self.format_chat_history(chat_history[-2:])  # 只保留最近2条
                agent_input["chat_history"] = formatted_history

            result = self.agent_executor.invoke(agent_input)
            output = result.get("output", "抱歉，我无法生成回复。")

            llm_logcontent = {
                "request": {
                    "input": message,
                    "enhanced_message": enhanced_message
                },
                "response": output
            }
            logger.info(f"{log_prefix} 【LLM请求】:{llm_logcontent['request']}，【LLM响应】:{llm_logcontent['response']}")

            return output
        except Exception as e:
            logger.error(f"【错误】Agent执行失败: {str(e)}", exc_info=True)
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

        try:
            # 构建输入
            agent_input = {"input": enhanced_message}

            # 添加对话历史
            if chat_history:
                formatted_history = self.format_chat_history(chat_history[-2:])
                agent_input["chat_history"] = formatted_history

            result = self.agent_executor.invoke(agent_input)

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
        base_info["agent_type"] = "tool_calling"
        base_info["agent_config"] = {
            "type": "tool_calling",
            "max_iterations": settings.AGENT_MAX_ITERATIONS,
            "verbose": settings.AGENT_VERBOSE,
            "handle_parsing_errors": settings.AGENT_HANDLE_PARSING_ERRORS
        }
        base_info["tools"] = [tool.name for tool in self.tools]
        base_info["capabilities"] = [
            "任务拆解和编排",
            "智能工具选择（优先使用快速工具链）",
            "4种预定义场景：只查询/查询+分析/查询+可视化/完整分析",
            "自然语言转SQL查询",
            "数据库表结构查询",
            "SQL执行",
            "数据分析和洞察",
            "图表类型推荐",
            "图表配置生成",
            "表上下文管理",
            "时间对比分析（同比、环比、同期）"
        ]
        base_info["architecture"] = "职责分离 + 预定义链 + 原子工具 + 上下文传递"
        base_info["performance"] = {
            "query_only": "2次LLM调用，约2秒",
            "query_with_analysis": "3次LLM调用，约3秒",
            "query_with_chart": "3次LLM调用，约3秒",
            "full_analysis": "4次LLM调用，约4秒"
        }
        return base_info
