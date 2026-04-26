from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    retry_count: int = 3


class BaseAgent(ABC):
    """Agent 基类，定义标准接口契约"""

    def __init__(
        self,
        llm_provider: Any,
        config: Optional[AgentConfig] = None
    ):
        self.llm = llm_provider
        self.config = config or AgentConfig()

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行阶段任务，消费上下文，产出增量上下文

        :param context: Pipeline 传入的全局全量上下文
        :return: 仅含有该阶段计算产物的一个字典，Pipeline 会负责将其 Merge 回总 context
        """
        pass

    def get_input_keys(self) -> List[str]:
        """返回该 Agent 需要的输入键列表"""
        return []

    def get_output_key(self) -> str:
        """返回该 Agent 输出的键名"""
        return ""

    def _validate_input(self, context: Dict[str, Any]) -> None:
        """验证输入是否包含必要的键"""
        required_keys = self.get_input_keys()
        missing_keys = [k for k in required_keys if k not in context]
        if missing_keys:
            raise ValueError(
                f"Agent {self.__class__.__name__} missing required keys: {missing_keys}"
            )
