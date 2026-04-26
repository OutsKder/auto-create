from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    def __init__(self, llm_provider: Any, config: Dict[str, Any] = None):
        """
        初始化 Agent
        :param llm_provider: 统一的大模型提供者实例 (如基于LangChain的 ChatModel)
        :param config: 该Agent特有的配置参数
        """
        self.llm = llm_provider
        self.config = config or {}

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行阶段任务，消费上下文，产出增量上下文
        :param context: Pipeline 传入的全局全量上下文
        :return: 仅含有该阶段计算产物的一个字典，Pipeline会负责将其Merge回总 context
        """
        pass
