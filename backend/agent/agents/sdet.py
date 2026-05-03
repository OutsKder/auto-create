"""Public SDET agent adapter.

This adapter keeps the pipeline-facing Agent contract stable while delegating
test-suite generation to ``backend.agent.codegen.sdet.SDETAgent``. The adapter
does not execute tests; callers should run ``TestingWorkflow`` when they want
to apply patches, materialize tests, and fill ``tests.sandbox_result``.
"""

from __future__ import annotations

from typing import Any, Dict

from ..base import AgentConfig, BaseAgent
from ..codegen.sdet import SDETAgent as CoreSDETAgent
from ..contracts import SDETInput, TestBundle


class SDETAgent(BaseAgent):
    """Pipeline-facing adapter for structured test generation."""

    input_model = SDETInput
    output_key = "tests"
    output_model = TestBundle

    def __init__(self, llm_provider: Any, config: AgentConfig | None = None):
        super().__init__(llm_provider, config)

    def get_input_keys(self):
        return ["code_diff", "requirement_structured"]

    def get_output_key(self):
        return "tests"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)
        core_agent = CoreSDETAgent(llm_provider=self.llm, config=self.config)
        result = core_agent.execute(context)
        self._validate_output(result)
        return result
