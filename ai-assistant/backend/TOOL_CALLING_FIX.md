# Tool Calling 问题修复指南

## 问题描述

切换到本地大模型后，Agent 不执行工具调用，而是返回文本描述：

```
好的，我将为您查询 `salary_tracking` 表的结构。

​```python
result = get_schema_info(database="chatbi_data", table="salary_tracking")
​```

请稍等，我将返回表结构信息。
```

**根本原因**：本地模型可能不支持 OpenAI 的 Tool Calling 格式。

---

## 🔍 步骤 1: 测试你的模型

首先，运行测试脚本检查模型是否支持 Tool Calling：

```bash
cd /home/user/langchain-demo/ai-assistant/backend
python test_tool_calling.py
```

**可能的测试结果**：

### ✅ 结果 A: 测试通过
```
✅ 成功！模型正确调用了工具并返回了结果
✅ 你的模型支持 Tool Calling，可以正常使用当前的 Agent 架构
```

**解决方案**：你的模型支持 Tool Calling，问题可能在其他地方：
- 检查 `.env` 配置是否正确
- 检查 Ollama 服务是否正常运行
- 尝试重启后端服务

### ❌ 结果 B: 测试失败（模型不支持 Tool Calling）
```
⚠️  警告：模型可能没有真正调用工具
⚠️  建议：考虑切换到 ReAct Agent 模式
```

**解决方案**：继续阅读下面的修复方案。

---

## 🛠️ 步骤 2: 选择修复方案

### 方案 A: 切换到支持 Tool Calling 的模型（推荐）

#### Option 1: 使用官方 Qwen2.5 模型（最简单）

```bash
# 拉取官方 Qwen2.5 模型（已验证支持 Tool Calling）
ollama pull qwen2.5:7b
# 或者更大的模型
ollama pull qwen2.5:14b
```

更新 `.env`:
```bash
LLM_MODEL=qwen2.5:7b
```

#### Option 2: 使用 Llama 3.1/3.2（已验证支持）

```bash
ollama pull llama3.1:8b
```

更新 `.env`:
```bash
LLM_MODEL=llama3.1:8b
```

#### Option 3: 检查 qwen-72b-w8a16 的 Modelfile

如果你坚持使用 `qwen-72b-w8a16`，可能需要自定义 Modelfile 来启用 Tool Calling：

```bash
# 查看当前模型信息
ollama show qwen-72b-w8a16 --modelfile

# 创建自定义 Modelfile
cat > Modelfile.qwen72b <<EOF
FROM qwen-72b-w8a16

# 确保模板支持 Tool Calling
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Tools }}<|im_start|>system
You have access to the following functions:
{{ range .Tools }}
{{ . }}
{{ end }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
EOF

# 创建新模型
ollama create qwen-72b-tools -f Modelfile.qwen72b
```

更新 `.env`:
```bash
LLM_MODEL=qwen-72b-tools
```

---

### 方案 B: 切换到 ReAct Agent（通用方案）

如果上述方案都不行，或者你想使用不支持 Tool Calling 的模型，可以切换到 **ReAct Agent**。

**优点**：
- ✅ 适用于所有大模型
- ✅ 不依赖 Tool Calling
- ✅ 通过提示词引导模型推理

**缺点**：
- ⚠️ 可能需要更多 token
- ⚠️ 对模型的指令遵循能力要求更高

#### 实现步骤：

**1. 创建 ReAct Agent 实现**

创建文件 `app/agents/chatbi_agent_react.py`:

```python
"""
ChatBI Agent - ReAct 模式（兼容所有大模型）
"""

import logging
from typing import Optional, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

from app.config import settings
from app.tools.chatbi_chains import (
    chatbi_query_only_chain,
    chatbi_query_with_analysis_chain,
    chatbi_query_with_chart_chain,
    chatbi_full_analysis_chain
)
from app.tools.chatbi_tools_atomic import (
    get_schema_info,
    nl_to_sql,
    execute_sql,
    analyze_data,
    suggest_chart,
    generate_chart_config
)

logger = logging.getLogger(__name__)


class ChatBIAgentReAct:
    """ChatBI Agent - ReAct 模式，兼容所有大模型"""

    def __init__(self):
        """初始化 ChatBI Agent (ReAct 模式)"""
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
            logger.info(f"ChatBI Agent (ReAct) LLM 初始化成功: provider={settings.LLM_PROVIDER}, model={settings.LLM_MODEL}")
        except Exception as e:
            logger.error(f"【错误】ChatOpenAI模型初始化失败: {str(e)}")
            raise

        # ChatBI工具：预定义链（快速） + 原子工具（灵活）
        self.tools = [
            # === 预定义工具链（优先使用，减少LLM调用次数）===
            chatbi_query_only_chain,
            chatbi_query_with_analysis_chain,
            chatbi_query_with_chart_chain,
            chatbi_full_analysis_chain,

            # === 原子工具（灵活组合）===
            get_schema_info,
            nl_to_sql,
            execute_sql,
            analyze_data,
            suggest_chart,
            generate_chart_config,
        ]

        # ReAct Prompt Template
        self.prompt = PromptTemplate.from_template("""你是一个专业的数据分析助手，帮助用户查询和分析数据。

你可以使用以下工具：

{tools}

工具描述：
{tool_names}

请使用以下格式回答：

Question: 用户的问题
Thought: 你应该思考下一步该做什么
Action: 要使用的工具名称，必须是 [{tool_names}] 中的一个
Action Input: 工具的输入参数（JSON格式）
Observation: 工具执行的结果
... (可以重复 Thought/Action/Action Input/Observation 多次)
Thought: 我现在知道最终答案了
Final Answer: 给用户的最终答案（中文，友好的格式）

重要规则：
1. 优先使用预定义工具链（chatbi_开头的工具），它们更高效
2. 只在需要灵活组合时才使用原子工具
3. 必须严格遵循 Thought/Action/Action Input/Observation/Final Answer 格式
4. Action Input 必须是有效的 JSON
5. 最终答案要友好、清晰、结构化

开始！

Question: {input}
Thought: {agent_scratchpad}""")

        # 创建 ReAct Agent
        try:
            agent = create_react_agent(self.llm, self.tools, self.prompt)
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=settings.AGENT_VERBOSE,
                handle_parsing_errors=True,
                max_iterations=settings.AGENT_MAX_ITERATIONS,
                max_execution_time=60,
            )
            logger.info("ChatBI ReAct Agent 创建成功")
        except Exception as e:
            logger.error(f"【错误】创建 ReAct Agent 失败: {str(e)}")
            raise

    def chat(self, message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户消息

        Args:
            message: 用户消息
            conversation_id: 对话ID（可选）

        Returns:
            包含回复内容和元数据的字典
        """
        try:
            logger.info(f"收到用户消息: {message}")

            # 调用 Agent
            result = self.agent_executor.invoke({
                "input": message
            })

            output = result.get("output", "抱歉，我无法生成回复。")

            logger.info(f"Agent 响应: {output}")

            return {
                "content": output,
                "conversation_id": conversation_id,
                "metadata": {
                    "intermediate_steps": len(result.get("intermediate_steps", [])),
                }
            }

        except Exception as e:
            logger.error(f"【错误】处理消息时出错: {str(e)}", exc_info=True)
            return {
                "content": f"抱歉，处理您的请求时出现了错误：{str(e)}",
                "conversation_id": conversation_id,
                "error": str(e)
            }
```

**2. 更新主入口文件**

修改 `app/main.py`，添加环境变量控制 Agent 类型：

```python
# 在 config.py 中添加
AGENT_TYPE: str = "tool_calling"  # 可选: "tool_calling" 或 "react"
```

```python
# 在 main.py 中导入
from app.agents.chatbi_agent import ChatBIAgent
from app.agents.chatbi_agent_react import ChatBIAgentReAct
from app.config import settings

# 根据配置选择 Agent
if settings.AGENT_TYPE == "react":
    agent = ChatBIAgentReAct()
    logger.info("使用 ReAct Agent 模式（兼容所有大模型）")
else:
    agent = ChatBIAgent()
    logger.info("使用 Tool Calling Agent 模式（需要模型支持）")
```

**3. 更新 `.env` 配置**

添加：
```bash
AGENT_TYPE=react
```

**4. 重启服务并测试**

```bash
# 重启后端
python -m uvicorn app.main:app --reload
```

---

## 📊 方案对比

| 特性 | Tool Calling Agent | ReAct Agent |
|------|-------------------|-------------|
| 模型要求 | 必须支持 Tool Calling | 任何大模型 |
| 性能 | ⚡ 快速 | 🐢 较慢 |
| Token 消耗 | 💰 少 | 💰💰 多 |
| 可靠性 | ✅ 高（结构化调用） | ⚠️ 中（依赖提示词） |
| 适用场景 | GPT-4, Qwen2.5, Llama3.1 | 所有模型 |

---

## 🎯 推荐方案

### 对于 qwen-72b-w8a16：

1. **首选**：先运行 `python test_tool_calling.py` 测试
2. **如果测试通过**：检查配置和服务状态
3. **如果测试失败**：
   - 尝试方案 A Option 3（自定义 Modelfile）
   - 或切换到方案 A Option 1（使用官方 qwen2.5）
   - 或使用方案 B（ReAct Agent）

### 性能考虑：

- **72B 模型**非常大，Tool Calling 响应可能较慢
- 建议考虑使用 **qwen2.5:14b** 或 **qwen2.5:32b**，它们：
  - ✅ 确认支持 Tool Calling
  - ✅ 性能更好
  - ✅ 显存需求更合理（14B ~16GB，32B ~32GB）

---

## 🧪 验证修复

修复后，测试以下问题：

```
1. "查询 salary_tracking 表的结构"
2. "查询 2024 年的销售数据"
3. "分析最近一个月的用户增长趋势"
```

**期望结果**：Agent 应该实际执行工具调用并返回结果，而不是返回代码描述。

---

## 📞 需要帮助？

如果上述方案都不能解决问题，请提供：

1. `python test_tool_calling.py` 的完整输出
2. 你的 `.env` 配置（脱敏后）
3. `ollama list` 的输出
4. 后端服务的启动日志

我会根据具体情况提供进一步的帮助。
