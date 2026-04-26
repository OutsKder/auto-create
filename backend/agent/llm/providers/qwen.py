"""
阿里通义千问 LLM Provider

基于 DashScope 兼容接口实现

配置示例：
```python
from agent.llm.providers import QwenProvider

provider = QwenProvider(
    config=LLMConfig(
        provider="qwen",
        model="qwen-max",  # 或 qwen-plus, qwen-turbo
        api_key="your-api-key",  # 可选，从环境变量读取
        temperature=0.7,
        max_tokens=4096
    )
)
```
"""

import os
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from ..base import BaseLLMProvider, LLMConfig


class QwenProvider(BaseLLMProvider):
    """阿里通义千问 LLM Provider"""

    DEFAULT_MODEL = "qwen-max"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, config: Optional[LLMConfig] = None):
        if config is None:
            config = self._get_default_config()
        super().__init__(config)
        self._client = None

    def _get_default_config(self) -> LLMConfig:
        """获取通义千问默认配置"""
        return LLMConfig(
            provider="qwen",
            model=os.environ.get("QWEN_MODEL", self.DEFAULT_MODEL),
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            base_url=os.environ.get("QWEN_BASE_URL", self.DEFAULT_BASE_URL),
            temperature=0.7,
            max_tokens=4096,
            timeout=120,
            streaming=True,
        )

    def _validate_config(self) -> None:
        """验证通义千问配置"""
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
                    "Qwen API key is required. Set DASHSCOPE_API_KEY environment variable."
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

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """同步调用通义千问 LLM"""
        try:
            langchain_messages = self._convert_messages(messages)

            temperature = kwargs.get("temperature", self.config.temperature)
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)

            client = self._get_client()
            response = client.invoke(
                langchain_messages,
                config={"temperature": temperature, "max_tokens": max_tokens},
            )

            return self._parse_response(response)

        except Exception as e:
            return {
                "content": f"请求失败: {str(e)}",
                "error": str(e),
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "model": self.get_model_name(),
            }

    def stream(self, messages: List[Dict[str, str]], **kwargs):
        """流式调用通义千问 LLM"""
        try:
            langchain_messages = self._convert_messages(messages)

            temperature = kwargs.get("temperature", self.config.temperature)
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)

            client = self._get_client()

            for chunk in client.stream(
                langchain_messages,
                config={"temperature": temperature, "max_tokens": max_tokens},
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
        result = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "user":
                result.append(HumanMessage(content=content))
            else:
                result.append(HumanMessage(content=content))

        return result

    def _parse_response(self, response) -> Dict[str, Any]:
        """解析 LangChain 响应"""
        content = response.content if hasattr(response, "content") else str(response)

        usage = {}
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if isinstance(metadata, dict) and "token_usage" in metadata:
                usage = metadata["token_usage"]

        return {
            "content": content,
            "usage": usage,
            "model": self.get_model_name(),
            "response_metadata": (
                response.response_metadata
                if hasattr(response, "response_metadata")
                else {}
            ),
        }
