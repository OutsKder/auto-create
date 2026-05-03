from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel

from .logging_config import setup_logging


class AgentConfig(BaseModel):
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    retry_count: int = 3


class BaseAgent(ABC):
    """Agent 基类，定义标准接口契约"""

    input_model: Optional[Type[BaseModel]] = None
    output_key: str = ""
    output_model: Optional[Type[BaseModel]] = None

    def __init__(
        self,
        llm_provider: Any,
        config: Optional[AgentConfig] = None
    ):
        setup_logging()
        self.llm = llm_provider
        self.config = config or AgentConfig()
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.logger.debug(
            "Agent initialized; config=%s; llm_provider=%s",
            self.config.model_dump(),
            type(llm_provider).__name__ if llm_provider is not None else None,
        )

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
        return self.output_key

    def _validate_input(self, context: Dict[str, Any]) -> None:
        """验证输入是否包含必要的键"""
        if self.input_model is not None:
            payload = self._select_input_payload(context)
            self.logger.debug(
                "Validating input with %s; fields=%s",
                self.input_model.__name__,
                sorted(payload.keys()),
            )
            self.input_model.model_validate(payload)
            self.logger.debug("Input validation passed")
            return

        required_keys = self.get_input_keys()
        missing_keys = [k for k in required_keys if k not in context]
        if missing_keys:
            self.logger.error("Input validation failed; missing=%s", missing_keys)
            raise ValueError(
                f"Agent {self.__class__.__name__} missing required keys: {missing_keys}"
            )
        self.logger.debug("Input validation passed; required_keys=%s", required_keys)

    def _validate_output(self, result: Dict[str, Any]) -> None:
        """验证 Agent 输出是否符合声明的结构化契约。"""
        output_key = self.get_output_key()
        if output_key and output_key not in result:
            self.logger.error("Output validation failed; missing key=%s", output_key)
            raise ValueError(
                f"Agent {self.__class__.__name__} missing output key: {output_key}"
            )

        if self.output_model is not None and output_key:
            self.logger.debug(
                "Validating output key=%s with %s",
                output_key,
                self.output_model.__name__,
            )
            self.output_model.model_validate(result[output_key])
            self.logger.debug("Output validation passed; output_key=%s", output_key)

    def _select_input_payload(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Select only fields declared by input_model from the full pipeline context."""
        if self.input_model is None:
            return context

        fields = getattr(self.input_model, "model_fields", {})
        return {key: context[key] for key in fields if key in context}
