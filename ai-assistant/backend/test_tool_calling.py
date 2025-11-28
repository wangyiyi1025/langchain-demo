"""
测试本地大模型的 Tool Calling 支持

运行方式：
    python test_tool_calling.py

说明：
    - 如果模型支持 Tool Calling，会看到实际的工具调用
    - 如果不支持，会看到文本描述或错误
"""

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

# 加载环境变量
load_dotenv()

# 读取配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-dummy-key")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:latest")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

print("=" * 80)
print("Tool Calling 支持测试")
print("=" * 80)
print(f"提供商: {LLM_PROVIDER}")
print(f"Base URL: {OPENAI_BASE_URL}")
print(f"模型: {LLM_MODEL}")
print("=" * 80)
print()


# 定义一个简单的测试工具
@tool
def get_current_weather(location: str) -> str:
    """获取指定城市的天气信息

    Args:
        location: 城市名称，例如 "北京" 或 "上海"

    Returns:
        该城市的天气信息
    """
    return f"{location}的天气：晴天，温度 25°C"


# 初始化 LLM
try:
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.7,
        max_tokens=500,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL
    )
    print("✅ LLM 初始化成功")
except Exception as e:
    print(f"❌ LLM 初始化失败: {e}")
    sys.exit(1)

# 测试1: 直接测试模型是否支持 Tool Calling
print("\n" + "-" * 80)
print("测试 1: 检查模型是否支持 bind_tools")
print("-" * 80)

try:
    llm_with_tools = llm.bind_tools([get_current_weather])
    print("✅ 模型支持 bind_tools 方法")
except Exception as e:
    print(f"❌ 模型不支持 bind_tools: {e}")
    print("\n【结论】此模型不支持 Tool Calling，建议使用 ReAct Agent 模式")
    sys.exit(1)

# 测试2: 实际调用测试
print("\n" + "-" * 80)
print("测试 2: 实际工具调用测试")
print("-" * 80)

try:
    # 创建 Agent
    tools = [get_current_weather]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个helpful的助手。当用户询问天气时，使用 get_current_weather 工具查询。"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=3,
        handle_parsing_errors=True
    )

    print("\n发送测试问题：北京的天气怎么样？\n")
    result = agent_executor.invoke({"input": "北京的天气怎么样？"})

    print("\n" + "=" * 80)
    print("【测试结果】")
    print("=" * 80)
    print(f"输出: {result['output']}")
    print()

    # 检查是否真正调用了工具
    if "晴天，温度 25°C" in result['output']:
        print("✅ 成功！模型正确调用了工具并返回了结果")
        print("✅ 你的模型支持 Tool Calling，可以正常使用当前的 Agent 架构")
    else:
        print("⚠️  警告：模型可能没有真正调用工具")
        print("⚠️  建议：考虑切换到 ReAct Agent 模式")

except Exception as e:
    print(f"\n❌ 工具调用测试失败: {e}")
    print("\n【建议】")
    print("1. 如果是 'bind_tools not supported' 错误 → 模型不支持 Tool Calling")
    print("2. 如果是超时或连接错误 → 检查 Ollama 服务是否正常运行")
    print("3. 如果模型只返回文本描述 → 需要切换到 ReAct Agent 模式")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
