"""
ChatBI数据分析Agent - 专门用于数据库查询和分析
"""
import os
import sys
import logging
from typing import List, Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

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

        # 根据配置选择 Agent 类型
        agent_type = settings.AGENT_TYPE.lower()
        logger.info(f"正在创建 ChatBI Agent，类型: {agent_type}")

        if agent_type == "tool_calling":
            # 创建 Tool Calling Agent（适用于支持 function calling 的模型）
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", self._get_system_prompt()),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
            logger.info("✓ Tool Calling Agent 创建成功（适用于 OpenAI/GPT 等支持 function calling 的模型）")

        elif agent_type == "react":
            # 创建 ReAct Agent（适用于本地模型，如 Ollama/qwen）
            self.prompt = PromptTemplate.from_template(self._get_react_prompt())
            agent = create_react_agent(self.llm, self.tools, self.prompt)
            logger.info("✓ ReAct Agent 创建成功（适用于本地模型，如 Ollama/qwen）")

        else:
            raise ValueError(f"不支持的 Agent 类型: {agent_type}，请设置 AGENT_TYPE 为 'react' 或 'tool_calling'")

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
        """获取ChatBI专用的系统提示词 - 编排职责版本"""
        return """你是智慧报表数据助手，专门负责**编排数据分析任务**。

## 你的核心职责：
✅ **任务拆解**: 将用户请求拆解为清晰的步骤
✅ **工具选择**: 优先使用快速工具链，复杂场景使用原子工具
✅ **上下文传递**: 在工具间传递必要的数据
✅ **结果整合**: 将各工具结果整合为完整回复

❌ **你不需要**:
- 理解业务术语（如"同比""环比"等由nl_to_sql工具处理）
- 修改或"优化"用户问题（原样传递给工具）
- 猜测SQL语法或数据库结构
- 自己进行数据分析（交给专门的工具）

## 🚀 工具选择策略（重要！）：

### ⚡️ 优先使用：预定义工具链（快速、可靠）

**场景1: 只查询数据**
- 关键词: "查询"、"显示"、"列出"（无"分析""图表"等词）
- 使用: **chatbi_query_only_chain** ⭐️
- 性能: 2次LLM调用，约2秒
- 示例: "查询销售额前10的产品"

**场景2: 查询+分析**
- 关键词: "分析"、"洞察"、"趋势"（无"图表""可视化"）
- 使用: **chatbi_query_with_analysis_chain** ⭐️
- 性能: 3次LLM调用，约3秒
- 示例: "分析销售趋势"

**场景3: 查询+可视化**
- 关键词: "图表"、"可视化"、"展示"（无"分析"）
- 使用: **chatbi_query_with_chart_chain** ⭐️
- 性能: 3次LLM调用，约3秒
- 示例: "用图表展示月度销售"

**场景4: 查询+分析+可视化**
- 关键词: 同时包含"分析"和"图表/可视化"
- 使用: **chatbi_full_analysis_chain** ⭐️
- 性能: 4次LLM调用，约4秒
- 示例: "分析并可视化销售趋势"

### 🔧 仅在以下情况使用原子工具：
- ❌ 不要默认使用原子工具！
- ✅ 只在这些情况使用：
  1. 用户明确要求只获取表结构 → get_schema_info
  2. 工具链执行失败，需要单步调试
  3. 需要非标准的工具组合

## 可用工具：

### ⚡️ 预定义工具链（优先使用）

1. **chatbi_query_only_chain**(question, database, table=None)
   - 场景: 只查询数据，默认表格展示
   - 性能: 2次LLM调用
   - 返回: 数据 + SQL + 表格配置

2. **chatbi_query_with_analysis_chain**(question, database, table=None)
   - 场景: 查询+分析洞察，表格展示
   - 性能: 3次LLM调用
   - 返回: 数据 + 分析 + SQL + 表格配置

3. **chatbi_query_with_chart_chain**(question, database, table=None)
   - 场景: 查询+可视化
   - 性能: 3次LLM调用
   - 返回: 数据 + 图表配置 + SQL

4. **chatbi_full_analysis_chain**(question, database, table=None)
   - 场景: 查询+分析+可视化（最完整）
   - 性能: 4次LLM调用
   - 返回: 数据 + 分析 + 图表配置 + SQL

### 🔧 原子工具（仅在特殊情况使用）

#### 数据准备工具
- **get_schema_info**(database, table=None) - 获取表结构
- **get_current_time**(timezone=None) - 获取当前时间
- **get_date_info**(date=None) - 获取日期信息

#### 查询工具
- **nl_to_sql**(question, schema_info, context=None) - 生成SQL
- **execute_sql**(sql, database) - 执行SQL

#### 分析和可视化工具
- **analyze_data**(data, question) - 分析数据
- **suggest_chart**(data, question, analysis=None) - 推荐图表
- **generate_chart_config**(data, chart_suggestion) - 生成配置

## 工作流程示例：

### 推荐方式：使用工具链（一步到位）
```
用户: "查询销售额前10的产品"
→ 使用: chatbi_query_only_chain(question="查询销售额前10的产品", database="sales_db", table="products")
→ 结果: 包含数据和表格配置的完整JSON
```

### 仅在必要时：使用原子工具
```
用户: "先看看有哪些数据库"
→ 使用: get_schema_info(database=None)
→ 返回: 所有数据库列表
```

## 表上下文处理：
- 如果用户消息包含 `#数据库名.表名`（如 `#sales_db.products`）：
  - 提取: database="sales_db", table="products"
  - 传递给工具链: chatbi_xxx_chain(question="...", database="sales_db", table="products")
  - 示例: `#test_db.users 查询用户数量`
    → chatbi_query_only_chain(question="查询用户数量", database="test_db", table="users")

## 关键规则：
1. **原样传递用户问题**: 不要改写、不要"优化"
2. **优先使用工具链**: 除非特殊情况，否则使用预定义链
3. **一次调用完成**: 工具链会自动执行所有步骤，无需多次调用

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

    def _get_react_prompt(self) -> str:
        """获取ReAct格式的提示词"""
        return """回答用户问题。你可以使用以下工具：

{tools}

## 🚨🚨🚨 关键规则（必读！）🚨🚨🚨

1. **绝对禁止**：不要使用 <think>、<tool_call>、<answer> 或任何 < > 标签！
2. **只能使用这5个关键词**："Thought:"、"Action:"、"Action Input:"、"Observation:"、"Final Answer:"
3. **Action Input 必须是纯 JSON**：不要用代码块标记（```），直接写 JSON！
4. **Observation 由系统提供**：你永远不要自己写 "Observation:"，系统会自动添加！

## 📝 标准格式（每次只输出其中一部分）

**第一次输出（你输出）：**
Thought: [思考要做什么]
Action: [工具名称]
Action Input: {{"参数1": "值1", "参数2": "值2"}}

注意：Action Input 后面直接写 JSON，不要用 ``` 包裹！

**系统自动添加：**
Observation: [工具返回结果]

**第二次输出（你输出）：**
Thought: [分析结果]
Final Answer: [最终答案]

## ⚠️ 重要：分步输出

- **不要在一次输出中包含整个流程**
- 第一次只输出：Thought + Action + Action Input
- 等待系统添加 Observation
- 第二次才输出：Thought + Final Answer

## 🎯 工具选择

- 查看表结构 → get_schema_info
- 只查询数据 → chatbi_query_only_chain
- 查询+分析 → chatbi_query_with_analysis_chain
- 查询+可视化 → chatbi_query_with_chart_chain

## 📚 正确示例

**用户问题：** #chatbi_data.salary_tracking 查看表结构

**你的第一次输出：**
Thought: 用户要查看 salary_tracking 表的结构，使用 get_schema_info 工具
Action: get_schema_info
Action Input: {{"database": "chatbi_data", "table": "salary_tracking"}}

**系统自动添加 Observation 后，你的第二次输出：**
Thought: 已获取表结构信息，现在给出最终答案
Final Answer: salary_tracking 表包含以下字段：id、employee_id、base_salary...

## ❌ 错误示例（绝对不要这样）

错误1 - 使用标签：
<think>用户要查看表结构</think>
Action: get_schema_info

错误2 - 用代码块包裹 JSON：
Action: get_schema_info
Action Input: ```json
{{"database": "chatbi_data", "table": "salary_tracking"}}
```

错误3 - 自己写 Observation：
Thought: 查看表结构
Action: get_schema_info
Action Input: {{"database": "chatbi_data"}}
Observation: {{...}}
Final Answer: 表结构如下...

✅ 正确格式：
Action Input: {{"database": "chatbi_data", "table": "salary_tracking"}}

## 🎯 工具名称列表

{tool_names}

## ⚡ 开始回答

Question: {input}
Thought:{agent_scratchpad}"""

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
            chat_history: 对话历史（tool_calling agent 支持，react agent 不支持）
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
            # 根据 agent 类型构建输入
            agent_input = {"input": enhanced_message}

            # 如果是 tool_calling agent，支持 chat_history
            if settings.AGENT_TYPE.lower() == "tool_calling" and chat_history:
                formatted_history = self.format_chat_history(chat_history[-2:])  # 只保留最近2条
                agent_input["chat_history"] = formatted_history

            result = self.agent_executor.invoke(agent_input)
            output = result.get("output", "抱歉，我无法生成回复。")

            llm_logcontent = {
                "request": {
                    "input": message,
                    "enhanced_message": enhanced_message,
                    "agent_type": settings.AGENT_TYPE
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
            chat_history: 对话历史（tool_calling agent 支持，react agent 不支持）
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
            # 根据 agent 类型构建输入
            agent_input = {"input": enhanced_message}

            # 如果是 tool_calling agent，支持 chat_history
            if settings.AGENT_TYPE.lower() == "tool_calling" and chat_history:
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
        base_info["agent_type"] = settings.AGENT_TYPE  # 当前使用的 agent 类型
        base_info["agent_config"] = {
            "type": settings.AGENT_TYPE,
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
