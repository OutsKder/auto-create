from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


class LLMConfig(BaseModel):
    """LLM 配置模型"""

    provider: str = Field(description="Provider 类型: doubao, qwen, openai")
    model: str = Field(description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API Key")
    base_url: Optional[str] = Field(default=None, description="API 基础 URL")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="最大 token 数")
    timeout: int = Field(default=120, description="超时时间(秒)")
    streaming: bool = Field(default=True, description="是否启用流式输出")
    retry_count: int = Field(default=3, description="重试次数")


class LLMResponse(dict):
    """兼容 ChatOpenAI 响应对象和 dict 的轻量包装。"""

    def __init__(
        self,
        content: str = "",
        usage: Optional[Dict[str, Any]] = None,
        model: str = "",
        response_metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        super().__init__(
            content=content,
            usage=usage or {},
            model=model,
            response_metadata=response_metadata or {},
        )
        if error is not None:
            self["error"] = error

    @property
    def content(self) -> str:
        return str(self.get("content", ""))

    @property
    def usage(self) -> Dict[str, Any]:
        value = self.get("usage", {})
        return value if isinstance(value, dict) else {}

    @property
    def response_metadata(self) -> Dict[str, Any]:
        value = self.get("response_metadata", {})
        return value if isinstance(value, dict) else {}

    @property
    def model(self) -> str:
        return str(self.get("model", ""))

    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


class BaseLLMProvider(ABC):
    """
    LLM Provider 抽象基类

    所有 LLM Provider 必须继承此类并实现以下方法：
    - invoke: 同步调用
    - stream: 流式调用
    - get_model_name: 获取模型名称

    设计原则：
    1. 依赖注入：Agent 通过构造函数接收 Provider 实例，不绑定特定服务商
    2. 统一接口：所有 Provider 实现相同接口，方便切换
    3. 配置驱动：通过 LLMConfig 传递配置，支持动态配置
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化 Provider

        Args:
            config: LLM 配置对象，如果为 None 则使用默认配置
        """
        self.config = config or self._get_default_config()
        self._validate_config()

    @abstractmethod
    def _get_default_config(self) -> LLMConfig:
        """获取默认配置，子类必须实现"""
        pass

    @abstractmethod
    def _validate_config(self) -> None:
        """验证配置有效性，子类必须实现"""
        pass

    @abstractmethod
    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """
        同步调用 LLM

        Args:
            messages: 消息列表，格式为 [{"role": "system"/"user"/"assistant", "content": "..."}]
            **kwargs: 其他参数，如 temperature, max_tokens 等

        Returns:
            响应对象，既支持 .content/.response_metadata，也支持 dict 访问。
        """
        pass

    @abstractmethod
    def stream(self, messages: List[Dict[str, str]], **kwargs):
        """流式调用 LLM。"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """获取当前使用的模型名称"""
        pass

    def get_config(self) -> LLMConfig:
        """获取当前配置"""
        return self.config

    def _normalize_messages(self, messages: Any) -> List[Any]:
        """把不同消息输入统一转换为 LangChain 消息列表。"""

        raw_messages = messages
        if hasattr(raw_messages, "to_messages"):
            raw_messages = raw_messages.to_messages()
        elif hasattr(raw_messages, "messages"):
            raw_messages = raw_messages.messages

        normalized_messages: List[Any] = []
        for message in raw_messages:
            if isinstance(message, dict):
                role = message.get("role", "user")
                content = message.get("content", "")
            elif isinstance(message, tuple) and len(message) >= 2:
                role, content = message[0], message[1]
            else:
                role = getattr(message, "role", getattr(message, "type", "user"))
                content = getattr(message, "content", str(message))

            if role == "system":
                normalized_messages.append(SystemMessage(content=content))
            elif role in {"assistant", "ai"}:
                normalized_messages.append(AIMessage(content=content))
            else:
                normalized_messages.append(HumanMessage(content=content))

        return normalized_messages

    def _get_runnable_config(self, kwargs: Dict[str, Any]) -> Any:
        """Build LangChain RunnableConfig from provider invoke kwargs."""

        runnable_config = kwargs.get("config") or {}
        if not isinstance(runnable_config, dict):
            return runnable_config

        runnable_config = dict(runnable_config)
        if "callbacks" in kwargs and "callbacks" not in runnable_config:
            runnable_config["callbacks"] = kwargs["callbacks"]

        return runnable_config or None

    def _bind_runtime_options(self, client: Any, kwargs: Dict[str, Any]) -> Any:
        """Bind per-call model options without dropping RunnableConfig."""

        model_kwargs: Dict[str, Any] = {}
        if "temperature" in kwargs:
            model_kwargs["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            model_kwargs["max_tokens"] = kwargs["max_tokens"]

        return client.bind(**model_kwargs) if model_kwargs else client

    @property
    def model(self) -> str:
        """兼容旧接口：直接读取模型名称。"""

        return self.get_model_name()

    @property
    def base_url(self) -> Optional[str]:
        """兼容旧接口：直接读取基础地址。"""

        return self.config.base_url

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.get_model_name()}>"
