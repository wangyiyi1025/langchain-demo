"""
Tool Call 适配器 - 将模型的 XML 格式工具调用转换为 OpenAI 标准格式

警告：这是一个临时方案，用于兼容不完全支持 OpenAI Tool Calling 格式的模型。
建议：生产环境应使用原生支持 Tool Calling 的模型（如 qwen2.5:14b）。

支持的输入格式：
1. XML 格式：<tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>
2. 标准 OpenAI 格式（直接透传）

输出格式：
标准的 AIMessage 包含 tool_calls 列表
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class ToolCallAdapter(ChatOpenAI):
    """
    Tool Call 适配器

    继承自 ChatOpenAI，重写输出处理逻辑以支持 XML 格式的工具调用。

    使用方式：
        from app.utils.tool_call_adapter import ToolCallAdapter

        llm = ToolCallAdapter(
            model="qwen-72b-w8a16",
            base_url="http://localhost:11434/v1",
            api_key="sk-dummy-key"
        )

    注意：
        这是一个临时解决方案，会增加维护成本和潜在的不稳定性。
    """

    def __init__(self, *args, **kwargs):
        """初始化适配器"""
        super().__init__(*args, **kwargs)
        logger.warning(
            "使用 ToolCallAdapter（临时方案）。"
            "建议切换到原生支持 Tool Calling 的模型（如 qwen2.5:14b）。"
        )

    def _parse_xml_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        解析 XML 格式的工具调用

        支持的格式：
        <tool_call>{"name": "get_schema_info", "arguments": {"database": "chatbi_data"}}</tool_call>

        Args:
            text: 模型输出的文本

        Returns:
            工具调用列表，OpenAI 格式
        """
        tool_calls = []

        # 正则匹配 <tool_call>...</tool_call>
        pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(pattern, text, re.DOTALL)

        for match in matches:
            try:
                # 清理内容
                content = match.strip()

                # 尝试解析 JSON
                tool_data = json.loads(content)

                # 验证必需字段
                if "name" not in tool_data:
                    logger.error(f"工具调用缺少 'name' 字段: {content}")
                    continue

                # 构造 OpenAI 格式的工具调用
                tool_call = {
                    "id": f"call_{uuid4().hex[:24]}",  # 生成唯一 ID
                    "type": "function",
                    "function": {
                        "name": tool_data["name"],
                        "arguments": json.dumps(tool_data.get("arguments", {}))
                    }
                }

                tool_calls.append(tool_call)
                logger.info(f"成功解析工具调用: {tool_data['name']}")

            except json.JSONDecodeError as e:
                logger.error(f"解析工具调用 JSON 失败: {content}, 错误: {e}")
                continue
            except Exception as e:
                logger.error(f"处理工具调用时出错: {content}, 错误: {e}")
                continue

        return tool_calls

    def _remove_tool_call_tags(self, text: str) -> str:
        """
        移除文本中的 <tool_call> 标签

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        # 移除 <tool_call>...</tool_call> 及其内容
        cleaned = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)

        # 清理多余的空白
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def _create_chat_result(
        self,
        response: ChatResult,
        tool_calls: List[Dict[str, Any]],
        cleaned_text: str
    ) -> ChatResult:
        """
        创建包含工具调用的 ChatResult

        Args:
            response: 原始响应
            tool_calls: 解析出的工具调用列表
            cleaned_text: 清理后的文本内容

        Returns:
            修改后的 ChatResult
        """
        # 获取原始 generation
        if not response.generations:
            logger.error("响应中没有 generations")
            return response

        original_generation = response.generations[0][0]
        original_message = original_generation.message

        # 创建新的 AIMessage，包含工具调用
        new_message = AIMessage(
            content=cleaned_text,
            additional_kwargs={
                **original_message.additional_kwargs,
                "tool_calls": tool_calls
            },
            tool_calls=[
                {
                    "name": tc["function"]["name"],
                    "args": json.loads(tc["function"]["arguments"]),
                    "id": tc["id"]
                }
                for tc in tool_calls
            ]
        )

        # 创建新的 ChatGeneration
        new_generation = ChatGeneration(
            message=new_message,
            generation_info=original_generation.generation_info
        )

        # 创建新的 ChatResult
        new_result = ChatResult(
            generations=[[new_generation]],
            llm_output=response.llm_output
        )

        return new_result

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        """
        重写 _generate 方法以支持 XML 格式的工具调用

        Args:
            messages: 消息列表
            stop: 停止词
            run_manager: 运行管理器
            **kwargs: 其他参数

        Returns:
            ChatResult，可能包含转换后的工具调用
        """
        # 调用父类的 _generate 获取原始响应
        response = super()._generate(messages, stop, run_manager, **kwargs)

        # 检查响应
        if not response.generations or not response.generations[0]:
            return response

        # 获取模型输出的文本
        message = response.generations[0][0].message
        text = message.content

        if not isinstance(text, str):
            return response

        # 检查是否包含 <tool_call> 标签
        if "<tool_call>" not in text:
            # 没有工具调用，直接返回原始响应
            return response

        logger.info("检测到 XML 格式的工具调用，开始解析...")

        # 解析工具调用
        tool_calls = self._parse_xml_tool_calls(text)

        if not tool_calls:
            logger.warning("未能成功解析任何工具调用，返回原始响应")
            return response

        # 清理文本内容（移除工具调用标签）
        cleaned_text = self._remove_tool_call_tags(text)

        # 创建新的响应
        new_response = self._create_chat_result(response, tool_calls, cleaned_text)

        logger.info(f"成功转换 {len(tool_calls)} 个工具调用为 OpenAI 格式")

        return new_response


def create_adapted_llm(
    model: str,
    base_url: str,
    api_key: str = "sk-dummy-key",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    max_retries: int = 2,
    **kwargs
) -> ToolCallAdapter:
    """
    创建带适配器的 LLM 实例

    Args:
        model: 模型名称
        base_url: API 地址
        api_key: API 密钥
        temperature: 温度参数
        max_tokens: 最大 token 数
        max_retries: 最大重试次数
        **kwargs: 其他参数

    Returns:
        ToolCallAdapter 实例
    """
    logger.info(f"创建 ToolCallAdapter: model={model}, base_url={base_url}")

    return ToolCallAdapter(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=max_retries,
        **kwargs
    )
