"""
OpenAI 兼容 LLM Provider

适用于任何兼容 OpenAI API 接口的大模型服务

配置示例：
```python
from agent.llm.providers import OpenAICompatibleProvider

provider = OpenAICompatibleProvider(
    config=LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="your-api-key",
        base_url="https://api.openai.com/v1",  # 或其他兼容服务的 URL
        temperature=0.7,
        max_tokens=4096
    )
)
```
"""

import os
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from ..base import BaseLLMProvider, LLMConfig, LLMResponse


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI 兼容 LLM Provider"""

    DEFAULT_MODEL = "gpt-4"
    DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def __init__(self, config: Optional[LLMConfig] = None):
        if config is None:
            config = self._get_default_config()
        super().__init__(config)
        self._client = None

    def _get_default_config(self) -> LLMConfig:
        """获取默认配置"""
        return LLMConfig(
            provider="openai",
            model=os.environ.get("OPENAI_MODEL", self.DEFAULT_MODEL),
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL", self.DEFAULT_BASE_URL),
            temperature=0.7,
            max_tokens=4096,
            timeout=120,
            streaming=True,
        )

    def _validate_config(self) -> None:
        """验证配置"""
        # 设置默认值
        if not self.config.base_url:
            self.config.base_url = self.DEFAULT_BASE_URL
        if not self.config.model:
            self.config.model = self.DEFAULT_MODEL
        # API key 延迟验证，只在真正调用时才检查

    def _get_client(self) -> ChatOpenAI:
        """获取或创建 ChatOpenAI 客户端"""
        if self._client is None:
            # 延迟验证 API key
            if not self.config.api_key:
                raise ValueError(
                    "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
                )
            self._client = ChatOpenAI(
                model=self.config.model,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                streaming=self.config.streaming,
                timeout=self.config.timeout,
            )
        return self._client

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """同步调用 OpenAI 兼容 LLM"""
        try:
            langchain_messages = self._convert_messages(messages)

            client = self._bind_runtime_options(self._get_client(), kwargs)
            response = client.invoke(
                langchain_messages,
                config=self._get_runnable_config(kwargs),
            )

            return self._parse_response(response)

        except Exception as e:
            return LLMResponse(
                content=f"请求失败: {str(e)}",
                error=str(e),
                usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                model=self.get_model_name(),
            )

    def stream(self, messages: List[Dict[str, str]], **kwargs):
        """流式调用 OpenAI 兼容 LLM"""
        try:
            langchain_messages = self._convert_messages(messages)

            client = self._bind_runtime_options(self._get_client(), kwargs)

            for chunk in client.stream(
                langchain_messages,
                config=self._get_runnable_config(kwargs),
            ):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            yield f"\n[请求失败: {str(e)}]"

    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.config.model or self.DEFAULT_MODEL

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List:
        """转换消息格式"""
        return self._normalize_messages(messages)

    def _parse_response(self, response) -> LLMResponse:
        """解析 LangChain 响应"""
        content = response.content if hasattr(response, "content") else str(response)

        usage = {}
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if isinstance(metadata, dict) and "token_usage" in metadata:
                usage = metadata["token_usage"]

        return LLMResponse(
            content=content,
            usage=usage,
            model=self.get_model_name(),
            response_metadata=(
                response.response_metadata
                if hasattr(response, "response_metadata")
                else {}
            ),
        )
