"""
LLM Provider 多服务商实现

该模块提供统一的 LLM Provider 接口，支持多种大模型服务商：
- 字节豆包 (Doubao)
- 阿里通义千问 (Qwen)
- OpenAI 兼容接口

架构设计：
1. BaseLLMProvider: 定义统一的抽象接口
2. LLMFactory: 根据配置动态创建 Provider 实例
3. 各 Provider 实现: 继承 BaseLLMProvider，实现具体调用逻辑

使用方式：
```python
from agent.llm import LLMFactory

# 通过工厂创建 Provider
llm = LLMFactory.create("doubao")

# 或者直接使用
from agent.llm.providers import DoubaoProvider
llm = DoubaoProvider()
```
"""

from .base import BaseLLMProvider, LLMConfig
from .factory import LLMFactory

__all__ = [
    "BaseLLMProvider",
    "LLMConfig",
    "LLMFactory",
]
