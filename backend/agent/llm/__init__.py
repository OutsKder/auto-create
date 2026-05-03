"""LLM Provider 统一入口。

推荐优先使用这里导出的 create_llm / default_llm / chat_with_llm。
"""

from .base import BaseLLMProvider, LLMConfig
from .config import get_default_config_dict, load_config, save_config
from .factory import LLMFactory
from .providers import DoubaoProvider, OpenAICompatibleProvider, QwenProvider
from .service import (
    DEFAULT_PROVIDER,
    chat_with_doubao,
    chat_with_llm,
    create_llm,
    default_llm,
    get_default_llm,
    get_llm_config,
    llm,
    stream_chat_with_doubao,
    stream_chat_with_llm,
)

__all__ = [
    "BaseLLMProvider",
    "LLMConfig",
    "LLMFactory",
    "DoubaoProvider",
    "QwenProvider",
    "OpenAICompatibleProvider",
    "load_config",
    "save_config",
    "get_default_config_dict",
    "DEFAULT_PROVIDER",
    "get_llm_config",
    "create_llm",
    "get_default_llm",
    "default_llm",
    "llm",
    "chat_with_llm",
    "stream_chat_with_llm",
    "chat_with_doubao",
    "stream_chat_with_doubao",
]
