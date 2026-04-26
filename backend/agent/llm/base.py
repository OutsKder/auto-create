from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
    def invoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步调用 LLM

        Args:
            messages: 消息列表，格式为 [{"role": "system"/"user"/"assistant", "content": "..."}]
            **kwargs: 其他参数，如 temperature, max_tokens 等

        Returns:
            响应字典，包含:
            - content: 响应内容
            - usage: token 使用量
            - model: 模型名称
            - response_metadata: 其他元数据
        """
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ):
        """
        流式调用 LLM

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Yields:
            每个 chunk 的内容
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """获取当前使用的模型名称"""
        pass

    def get_config(self) -> LLMConfig:
        """获取当前配置"""
        return self.config

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.get_model_name()}>"
