"""DevFlow Agent package exports.

Keep the package import light: contracts and agent classes should be importable
without constructing LLM clients or loading optional provider SDKs. Heavier
objects are resolved lazily through ``__getattr__``.
"""

from .base import AgentConfig, BaseAgent
from .contracts import Design, RequirementStructured

__all__ = [
    "BaseAgent",
    "AgentConfig",
    "RequirementAnalyst",
    "RequirementStructured",
    "TechArchitect",
    "Design",
    "CodeGeneratorAgent",
    "SDETAgent",
    "SeniorReviewerAgent",
    "TraceCallbackHandler",
    "PromptManager",
    "BaseLLMProvider",
    "LLMConfig",
    "LLMFactory",
    "DoubaoProvider",
    "QwenProvider",
    "OpenAICompatibleProvider",
    "ErrorType",
    "FailureAnalysis",
    "SelfHealingIteration",
    "SelfHealingReport",
    "RetryManager",
    "TriageAgent",
    "SelfHealingConfig",
    "SelfHealingCoordinator",
]


def __getattr__(name: str):
    if name in {
        "RequirementAnalyst",
        "TechArchitect",
        "CodeGeneratorAgent",
        "SDETAgent",
        "SeniorReviewerAgent",
    }:
        from .agents import (
            CodeGeneratorAgent,
            RequirementAnalyst,
            SDETAgent,
            SeniorReviewerAgent,
            TechArchitect,
        )

        return {
            "RequirementAnalyst": RequirementAnalyst,
            "TechArchitect": TechArchitect,
            "CodeGeneratorAgent": CodeGeneratorAgent,
            "SDETAgent": SDETAgent,
            "SeniorReviewerAgent": SeniorReviewerAgent,
        }[name]

    if name == "TraceCallbackHandler":
        from .callbacks import TraceCallbackHandler

        return TraceCallbackHandler

    if name == "PromptManager":
        from .prompts.manager import PromptManager

        return PromptManager

    if name in {"BaseLLMProvider", "LLMConfig", "LLMFactory"}:
        from .llm import BaseLLMProvider, LLMConfig, LLMFactory

        return {
            "BaseLLMProvider": BaseLLMProvider,
            "LLMConfig": LLMConfig,
            "LLMFactory": LLMFactory,
        }[name]

    if name in {"DoubaoProvider", "QwenProvider", "OpenAICompatibleProvider"}:
        from .llm.providers import DoubaoProvider, OpenAICompatibleProvider, QwenProvider

        return {
            "DoubaoProvider": DoubaoProvider,
            "QwenProvider": QwenProvider,
            "OpenAICompatibleProvider": OpenAICompatibleProvider,
        }[name]

    if name in {
        "ErrorType",
        "FailureAnalysis",
        "SelfHealingIteration",
        "SelfHealingReport",
        "RetryManager",
        "TriageAgent",
        "SelfHealingConfig",
        "SelfHealingCoordinator",
    }:
        from .self_healing import (
            ErrorType,
            FailureAnalysis,
            RetryManager,
            SelfHealingConfig,
            SelfHealingCoordinator,
            SelfHealingIteration,
            SelfHealingReport,
            TriageAgent,
        )

        return {
            "ErrorType": ErrorType,
            "FailureAnalysis": FailureAnalysis,
            "SelfHealingIteration": SelfHealingIteration,
            "SelfHealingReport": SelfHealingReport,
            "RetryManager": RetryManager,
            "TriageAgent": TriageAgent,
            "SelfHealingConfig": SelfHealingConfig,
            "SelfHealingCoordinator": SelfHealingCoordinator,
        }[name]

    raise AttributeError(name)
