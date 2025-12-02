"""
自定义LangChain回调处理器，用于捕获Agent执行的中间步骤
"""
import time
import json
from typing import Any, Dict, List, Optional
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish


class StepCallbackHandler(BaseCallbackHandler):
    """捕获Agent执行步骤的回调处理器"""

    def __init__(self):
        super().__init__()
        self.steps = []
        self.current_step = None
        self.step_counter = 0

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """工具开始执行时调用"""
        self.step_counter += 1
        tool_name = serialized.get("name", "unknown_tool")

        self.current_step = {
            "step_number": self.step_counter,
            "tool_name": tool_name,
            "status": "executing",
            "input": input_str,
            "output": None,
            "start_time": time.time(),
            "duration_ms": None,
            "error": None
        }

        self.steps.append(self.current_step)

    def on_tool_end(
        self,
        output: str,
        **kwargs: Any,
    ) -> None:
        """工具执行结束时调用"""
        if self.current_step:
            self.current_step["status"] = "completed"
            self.current_step["output"] = output
            self.current_step["duration_ms"] = int((time.time() - self.current_step["start_time"]) * 1000)

            # 生成输出预览（截取前200个字符）
            if isinstance(output, str):
                if len(output) > 200:
                    self.current_step["output_preview"] = output[:200] + "..."
                else:
                    self.current_step["output_preview"] = output
            else:
                self.current_step["output_preview"] = str(output)[:200]

    def on_tool_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """工具执行出错时调用"""
        if self.current_step:
            self.current_step["status"] = "failed"
            self.current_step["error"] = str(error)
            self.current_step["duration_ms"] = int((time.time() - self.current_step["start_time"]) * 1000)

    def on_agent_action(
        self,
        action: AgentAction,
        **kwargs: Any,
    ) -> None:
        """Agent执行动作时调用"""
        # 这里可以记录Agent的思考过程
        pass

    def on_agent_finish(
        self,
        finish: AgentFinish,
        **kwargs: Any,
    ) -> None:
        """Agent执行完成时调用"""
        pass

    def get_steps(self) -> List[Dict[str, Any]]:
        """获取所有步骤"""
        return self.steps

    def get_latest_step(self) -> Optional[Dict[str, Any]]:
        """获取最新的步骤"""
        return self.current_step if self.current_step else None

    def clear(self):
        """清空步骤记录"""
        self.steps = []
        self.current_step = None
        self.step_counter = 0
