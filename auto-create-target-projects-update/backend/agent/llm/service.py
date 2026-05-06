"""统一的 LLM 入口。

这个模块负责三件事：
1. 从配置文件/环境变量构建默认 LLM
2. 对外提供统一的 create/get/chat/stream 接口
3. 保留豆包历史接口，避免现有调用点一次性失效
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from .base import BaseLLMProvider, LLMConfig
from .config import load_config
from .factory import LLMFactory

DEFAULT_PROVIDER = "doubao"


def _normalize_provider(provider: Optional[str]) -> str:
    if not provider:
        return DEFAULT_PROVIDER
    return provider.strip().lower()


def get_llm_config(
    provider: Optional[str] = None,
    config_file: Optional[str] = None,
) -> LLMConfig:
    """加载指定 provider 的配置。

    统一优先读取 config/llm.yaml，再由环境变量覆盖。
    """

    return load_config(_normalize_provider(provider), config_file=config_file)


def create_llm(
    provider: Optional[str] = None,
    config: Optional[LLMConfig] = None,
    config_file: Optional[str] = None,
    **overrides: Any,
) -> BaseLLMProvider:
    """创建一个 LLM provider 实例。"""

    provider_name = _normalize_provider(
        provider or (config.provider if config else None)
    )
    resolved_config = config or get_llm_config(provider_name, config_file=config_file)

    if overrides:
        config_dict = resolved_config.dict()
        config_dict.update(overrides)
        resolved_config = LLMConfig(**config_dict)

    return LLMFactory.create(provider_name, config=resolved_config)


def get_default_llm(config_file: Optional[str] = None) -> BaseLLMProvider:
    """获取默认 LLM provider。"""

    return create_llm(DEFAULT_PROVIDER, config_file=config_file)


def chat_with_llm(
    prompt: str,
    system_prompt: str = "你是一个强大的人工智能助手。",
    provider: Optional[str] = None,
    config_file: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """使用统一入口完成一次对话调用。"""

    llm = create_llm(provider=provider, config_file=config_file, **kwargs)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    response = llm.invoke(messages)
    return str(getattr(response, "content", response))


def stream_chat_with_llm(
    prompt: str,
    system_prompt: str = "你是一个强大的人工智能助手。",
    provider: Optional[str] = None,
    config_file: Optional[str] = None,
    **kwargs: Any,
):
    """使用统一入口完成流式对话调用。"""

    llm = create_llm(provider=provider, config_file=config_file, **kwargs)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    yield from llm.stream(messages)


default_llm = get_default_llm()
llm = default_llm


def chat_with_doubao(
    prompt: str,
    system_prompt: str = "你是一个强大的人工智能助手。",
    **kwargs: Any,
) -> str:
    """保留历史接口：默认走豆包 provider。"""

    return chat_with_llm(
        prompt, system_prompt=system_prompt, provider="doubao", **kwargs
    )


def stream_chat_with_doubao(
    prompt: str,
    system_prompt: str = "你是一个强大的人工智能助手。",
    **kwargs: Any,
):
    """保留历史流式接口：默认走豆包 provider。"""

    yield from stream_chat_with_llm(
        prompt,
        system_prompt=system_prompt,
        provider="doubao",
        **kwargs,
    )


__all__ = [
    "DEFAULT_PROVIDER",
    "create_llm",
    "get_default_llm",
    "get_llm_config",
    "chat_with_llm",
    "stream_chat_with_llm",
    "chat_with_doubao",
    "stream_chat_with_doubao",
    "default_llm",
    "llm",
]
