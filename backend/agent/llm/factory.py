"""
LLM Factory - 工厂模式实现

根据配置动态创建不同类型的 LLM Provider 实例

使用方式：
```python
from agent.llm import LLMFactory, LLMConfig

# 方式1: 通过 provider 类型字符串创建
llm = LLMFactory.create("doubao")

# 方式2: 通过 provider 类型字符串 + 配置创建
llm = LLMFactory.create("qwen", config=LLMConfig(
    model="qwen-plus",
    temperature=0.8
))

# 方式3: 直接创建指定 Provider
from agent.llm.providers import DoubaoProvider
llm = DoubaoProvider()

# 方式4: 通过配置文件创建
llm = LLMFactory.create_from_config({
    "provider": "doubao",
    "model": "doubao-pro-32k",
    "temperature": 0.7
})
```

支持的 Provider 类型：
- "doubao": 字节豆包
- "qwen": 阿里通义千问
- "openai": OpenAI 兼容接口
"""

from typing import Dict, Any, Optional

from .base import BaseLLMProvider, LLMConfig
from .providers import DoubaoProvider, QwenProvider, OpenAICompatibleProvider


class LLMFactory:
    """LLM Provider 工厂类"""

    PROVIDER_MAP = {
        "doubao": DoubaoProvider,
        "qwen": QwenProvider,
        "openai": OpenAICompatibleProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }

    @classmethod
    def create(
        cls,
        provider: str,
        config: Optional[LLMConfig] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        创建 LLM Provider 实例

        Args:
            provider: Provider 类型 ("doubao", "qwen", "openai")
            config: LLM 配置对象
            **kwargs: 其他配置参数，会合并到 config 中

        Returns:
            BaseLLMProvider 实例

        Raises:
            ValueError: 不支持的 provider 类型
        """
        provider_class = cls.get_provider_class(provider)

        # 如果传入了 kwargs，合并到 config 中
        if kwargs and config:
            config_dict = config.dict()
            config_dict.update(kwargs)
            config = LLMConfig(**config_dict)
        elif kwargs and not config:
            config = LLMConfig(**kwargs)

        return provider_class(config=config)

    @classmethod
    def create_from_config(cls, config_dict: Dict[str, Any]) -> BaseLLMProvider:
        """
        通过配置字典创建 LLM Provider

        Args:
            config_dict: 配置字典，包含 provider, model 等字段

        Returns:
            BaseLLMProvider 实例
        """
        provider = config_dict.get("provider", "doubao")
        config = LLMConfig(**config_dict)
        return cls.create(provider, config=config)

    @classmethod
    def get_provider_class(cls, provider: str) -> type:
        """
        获取 Provider 类

        Args:
            provider: Provider 类型名称

        Returns:
            Provider 类

        Raises:
            ValueError: 不支持的 provider 类型
        """
        provider_lower = provider.lower()
        if provider_lower not in cls.PROVIDER_MAP:
            supported = ", ".join(cls.PROVIDER_MAP.keys())
            raise ValueError(
                f"不支持的 Provider 类型: {provider}。"
                f"支持的类型有: {supported}"
            )
        return cls.PROVIDER_MAP[provider_lower]

    @classmethod
    def list_providers(cls) -> list:
        """
        列出所有支持的 Provider 类型

        Returns:
            支持的 provider 列表
        """
        return list(cls.PROVIDER_MAP.keys())

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type
    ) -> None:
        """
        注册新的 Provider

        Args:
            name: Provider 名称
            provider_class: Provider 类
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError(f"Provider 类必须继承 BaseLLMProvider")
        cls.PROVIDER_MAP[name.lower()] = provider_class
