"""
code_generator.py

正式的代码生成 Agent 入口适配层。

职责：
- 从 Pipeline 的 context 中读取 `codebase.repo_path`
- 复用 `backend.agent.codegen.code_generator.CodeGeneratorAgent` 的实现
- 对外暴露和其他 Agent 一致的 `execute(context)` 接口

这样做的好处是：`agent/agents` 保持为统一的编排层，`agent/codegen` 专注实现细节，封装边界更清晰。
"""

from __future__ import annotations

from typing import Any, Dict

from ..base import BaseAgent, AgentConfig
from ..contracts import CodeGeneratorInput, DiffBundle
from ..codegen.code_generator import CodeGeneratorAgent as CoreCodeGeneratorAgent


class CodeGeneratorAgent(BaseAgent):
    """代码生成 Agent 的对外入口。"""

    input_model = CodeGeneratorInput
    output_key = "code_diff"
    output_model = DiffBundle

    def __init__(
        self,
        llm_provider: Any,
        repo_root: str | None = None,
        config: AgentConfig | None = None,
    ):
        super().__init__(llm_provider, config)
        self.repo_root = repo_root

    def get_input_keys(self):
        return ["requirement_structured", "design", "codebase_context"]

    def get_output_key(self):
        return "code_diff"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)

        repo_path = self.repo_root or (context.get("codebase", {}) or {}).get(
            "repo_path"
        )
        if not repo_path:
            raise ValueError("context 中缺少 codebase.repo_path，无法初始化代码生成器")

        core_agent = CoreCodeGeneratorAgent(
            llm_provider=self.llm,
            repo_root=repo_path,
            config=self.config,
        )
        result = core_agent.execute(context)
        self._validate_output(result)
        return result
