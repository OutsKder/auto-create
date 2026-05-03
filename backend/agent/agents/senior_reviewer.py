"""Senior reviewer agent.

This is the contract-first review gate. It intentionally starts deterministic:
the agent validates the structured inputs and produces a structured review
artifact without requiring an LLM call. A later LLM-backed reviewer can reuse
the same input/output contracts.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..base import AgentConfig, BaseAgent
from ..contracts import Review, ReviewAgentInput, ReviewIssue


class SeniorReviewerAgent(BaseAgent):
    """Review code changes against design intent and test results."""

    input_model = ReviewAgentInput
    output_key = "review"
    output_model = Review

    def __init__(self, llm_provider: Any = None, config: AgentConfig | None = None):
        super().__init__(llm_provider=llm_provider, config=config)

    def get_input_keys(self):
        return ["code_diff", "design", "tests"]

    def get_output_key(self):
        return "review"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)
        typed_input = self.input_model.model_validate(
            self._select_input_payload(context)
        )

        issues: List[ReviewIssue] = []
        blockers: List[str] = []

        code_diff = typed_input.code_diff
        tests = typed_input.tests
        design = typed_input.design

        if not code_diff.patches:
            issues.append(
                ReviewIssue(
                    severity="medium",
                    title="No code patches were produced",
                    detail="The code generation stage returned an empty patch list.",
                    suggestion="Regenerate code_diff from design.file_change_plan.",
                )
            )
            blockers.append("code_diff.patches is empty")

        planned_files = {item.file_path for item in design.file_change_plan}
        changed_files = set(code_diff.files_changed)
        unplanned_files = sorted(path for path in changed_files if path not in planned_files)
        for path in unplanned_files:
            issues.append(
                ReviewIssue(
                    severity="high",
                    title="Changed file is outside the approved plan",
                    detail=f"{path} was changed but is not listed in design.file_change_plan.",
                    file_path=path,
                    suggestion="Update the design plan or remove the unplanned change.",
                )
            )
        if unplanned_files:
            blockers.append("code_diff contains files outside design.file_change_plan")

        sandbox_result = tests.sandbox_result
        if sandbox_result is None:
            issues.append(
                ReviewIssue(
                    severity="medium",
                    title="Tests were not executed",
                    detail="tests.sandbox_result is missing.",
                    suggestion="Run TestingWorkflow before final review.",
                )
            )
        elif not sandbox_result.passed:
            issues.append(
                ReviewIssue(
                    severity="critical",
                    title="Generated tests failed",
                    detail=f"Test command exited with code {sandbox_result.exit_code}.",
                    suggestion="Inspect sandbox_result.logs and rerun the fix loop.",
                )
            )
            blockers.append("tests.sandbox_result.passed is false")

        patch_risks = [patch.risk_level for patch in code_diff.patches]
        if "critical" in patch_risks:
            blockers.append("code_diff contains critical-risk patches")
        risk_level = self._aggregate_risk([issue.severity for issue in issues] + patch_risks)

        passed = not blockers and risk_level not in {"critical"}
        review = Review(
            **{
                "pass": passed,
                "risk_level": risk_level,
                "issues": issues,
                "suggestions": self._build_suggestions(passed, issues),
                "release_blockers": blockers,
            }
        )

        output = {"review": review.model_dump(by_alias=True)}
        self._validate_output(output)
        return output

    def _aggregate_risk(self, risks: List[str]) -> str:
        order = ["unknown", "low", "medium", "high", "critical"]
        highest = "low"
        for risk in risks:
            if risk in order and order.index(risk) > order.index(highest):
                highest = risk
        return highest

    def _build_suggestions(
        self, passed: bool, issues: List[ReviewIssue]
    ) -> List[str]:
        if passed and not issues:
            return ["Structured review passed; changes are ready for delivery."]
        return [issue.suggestion for issue in issues if issue.suggestion]

