"""Self-healing workflow coordinator.

The coordinator owns orchestration only. Agents produce structured artifacts,
TestingWorkflow performs the side effects, and Triage/Retry decide whether the
next CodeGen attempt should receive failure feedback.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.agent import RequirementAnalyst, TechArchitect
from backend.agent.agents import CodeGeneratorAgent, SDETAgent
from backend.agent.codegen import SandboxResult, TestingWorkflow, TestingWorkflowConfig
from backend.agent.codegen.testing_options import build_testing_options

from .models import FailureAnalysis, SelfHealingIteration, SelfHealingReport
from .retry_manager import RetryManager
from .triage_agent import TriageAgent


class SelfHealingConfig(BaseModel):
    """Runtime settings for self-healing orchestration."""

    max_retries: int = 3
    use_docker: bool = True
    testing: TestingWorkflowConfig = Field(default_factory=TestingWorkflowConfig)


class SelfHealingCoordinator:
    """Coordinate CodeGen -> SDET -> TestingWorkflow -> Triage retry loops."""

    def __init__(
        self,
        max_retries: int = 3,
        use_docker: bool = True,
        config: Optional[SelfHealingConfig] = None,
        llm_provider: Any = None,
        requirement_agent: Any = None,
        architect_agent: Any = None,
        codegen_agent: Any = None,
        sdet_agent: Any = None,
        testing_workflow: Optional[TestingWorkflow] = None,
        triage_agent: Optional[TriageAgent] = None,
        retry_manager: Optional[RetryManager] = None,
    ):
        self.config = config or SelfHealingConfig(
            max_retries=max_retries,
            use_docker=use_docker,
            testing=TestingWorkflowConfig(use_docker=use_docker),
        )
        provider = llm_provider
        if provider is None and any(
            agent is None
            for agent in (requirement_agent, architect_agent, codegen_agent, sdet_agent)
        ):
            from backend.agent.llm import default_llm

            provider = default_llm

        self.requirement_agent = requirement_agent or RequirementAnalyst(
            llm_provider=provider
        )
        self.architect_agent = architect_agent or TechArchitect(llm_provider=provider)
        self.codegen = codegen_agent or CodeGeneratorAgent(llm_provider=provider)
        self.sdet = sdet_agent or SDETAgent(llm_provider=provider)
        self.testing_workflow = testing_workflow or TestingWorkflow(
            default_config=self.config.testing
        )
        self.triage = triage_agent or TriageAgent()
        self.retry_manager = retry_manager or RetryManager(
            max_retries=self.config.max_retries
        )

        self._failure_history: List[FailureAnalysis] = []
        self._iterations_log: List[SelfHealingIteration] = []
        self._start_time = 0.0

    def execute_with_self_healing(self, context: dict) -> SelfHealingReport:
        """Run the full self-healing loop for a requirement and codebase."""
        self._start_time = time.time()
        self.retry_manager.reset()
        self._failure_history = []
        self._iterations_log = []

        try:
            self._validate_context(context)
            requirement_structured, design, codebase_context = self._prepare(context)
        except Exception as exc:
            return self._failed_report(
                iterations=0,
                final_code=[],
                logs=f"Preparation failed: {exc}",
            )

        iteration = 0
        feedback_for_codegen: Optional[Dict[str, Any]] = None
        final_patches: List[Dict[str, Any]] = []

        while True:
            iteration += 1
            try:
                codegen_result = self._run_codegen(
                    context=context,
                    requirement_structured=requirement_structured,
                    design=design,
                    codebase_context=codebase_context,
                    failure_feedback=feedback_for_codegen,
                )
                code_diff = self._to_plain(codegen_result.get("code_diff", {}) or {})
                final_patches = self._to_plain_list(code_diff.get("patches", []) or [])

                sdet_result = self._run_sdet(
                    context=context,
                    requirement_structured=requirement_structured,
                    design=design,
                    codebase_context=codebase_context,
                    code_diff=code_diff,
                )
                tests = self._to_plain(sdet_result.get("tests", {}) or {})

                runner_result = self._run_testing_workflow(
                    context=context,
                    requirement_structured=requirement_structured,
                    design=design,
                    codebase_context=codebase_context,
                    code_diff=code_diff,
                    tests=tests,
                )

                iteration_log = SelfHealingIteration(
                    iteration_num=iteration,
                    codegen_output=codegen_result,
                    test_result={
                        "passed": runner_result.passed,
                        "exit_code": runner_result.exit_code,
                        "logs_snippet": (runner_result.logs or "")[:200],
                    },
                    passed=runner_result.passed,
                )
                self._iterations_log.append(iteration_log)

                if runner_result.passed:
                    return self._success_report(
                        iterations=iteration,
                        final_code=final_patches,
                        runner_result=runner_result,
                    )

                failure_analysis = self._triage_failure(
                    runner_result=runner_result,
                    patches=final_patches,
                )
                self._failure_history.append(failure_analysis)
                iteration_log.failure_analysis = failure_analysis

                if not self.retry_manager.should_continue(failure_analysis):
                    return self._stopped_report(
                        iterations=iteration,
                        final_code=final_patches,
                        runner_result=runner_result,
                        final_failure=failure_analysis,
                    )

                feedback_for_codegen = self._build_failure_feedback(failure_analysis)
                self.retry_manager.record_failure(failure_analysis)

            except Exception as exc:
                return self._failed_report(
                    iterations=iteration,
                    final_code=final_patches,
                    logs=f"Exception: {exc}",
                )

    def get_retry_status(self) -> dict:
        return self.retry_manager.get_status()

    def _validate_context(self, context: Dict[str, Any]) -> None:
        if not str(context.get("requirement_raw", "")).strip():
            raise ValueError("context.requirement_raw is required")

        codebase = context.get("codebase", {}) or {}
        if not str(codebase.get("repo_path", "")).strip():
            raise ValueError("context.codebase.repo_path is required")

    def _prepare(self, context: Dict[str, Any]):
        analyst_result = self.requirement_agent.execute(
            {"requirement_raw": context["requirement_raw"]}
        )
        requirement_structured = analyst_result.get("requirement_structured", {})

        design_result = self.architect_agent.execute(
            {
                "requirement_structured": requirement_structured,
                "codebase": context["codebase"],
            }
        )
        return (
            self._to_plain(requirement_structured),
            self._to_plain(design_result.get("design", {}) or {}),
            self._to_plain(design_result.get("codebase_context", {}) or {}),
        )

    def _run_codegen(
        self,
        context: Dict[str, Any],
        requirement_structured: Dict[str, Any],
        design: Dict[str, Any],
        codebase_context: Dict[str, Any],
        failure_feedback: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        payload = {
            "requirement_raw": context["requirement_raw"],
            "requirement_structured": requirement_structured,
            "design": design,
            "codebase": context["codebase"],
            "codebase_context": codebase_context,
        }
        if failure_feedback:
            payload["failure_feedback"] = failure_feedback
        return self.codegen.execute(payload)

    def _run_sdet(
        self,
        context: Dict[str, Any],
        requirement_structured: Dict[str, Any],
        design: Dict[str, Any],
        codebase_context: Dict[str, Any],
        code_diff: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.sdet.execute(
            {
                "requirement_structured": requirement_structured,
                "design": design,
                "code_diff": code_diff,
                "codebase": context["codebase"],
                "codebase_context": codebase_context,
            }
        )

    def _run_testing_workflow(
        self,
        context: Dict[str, Any],
        requirement_structured: Dict[str, Any],
        design: Dict[str, Any],
        codebase_context: Dict[str, Any],
        code_diff: Dict[str, Any],
        tests: Dict[str, Any],
    ) -> SandboxResult:
        workflow_result = self.testing_workflow.execute(
            {
                "requirement_structured": requirement_structured,
                "design": design,
                "code_diff": code_diff,
                "codebase": context["codebase"],
                "codebase_context": codebase_context,
                "tests": tests,
                "testing_options": self._testing_options(context),
            }
        )
        sandbox_result = (workflow_result.get("tests", {}) or {}).get("sandbox_result")
        if sandbox_result is None:
            return SandboxResult(
                passed=False,
                exit_code=1,
                logs="TestingWorkflow did not return tests.sandbox_result.",
            )
        return SandboxResult.model_validate(sandbox_result)

    def _testing_options(self, context: Dict[str, Any]) -> Dict[str, Any]:
        profile = str(context.get("testing_profile", "read_write") or "read_write")
        base_options = self.config.testing.model_dump()
        user_options = context.get("testing_options", {}) or {}
        merged = dict(base_options)
        merged.update(user_options)
        return build_testing_options(
            profile=profile,
            overrides=merged,
            default_use_docker=self.config.use_docker,
        )

    def _triage_failure(
        self, runner_result: SandboxResult, patches: List[Dict[str, Any]]
    ) -> FailureAnalysis:
        triage_result = self.triage.execute(
            {
                "sandbox_result": runner_result,
                "code_changes": str(patches),
                "previous_failures": self._failure_history,
            }
        )
        return triage_result["failure_analysis"]

    def _build_failure_feedback(self, failure: FailureAnalysis) -> Dict[str, Any]:
        error_type = (
            failure.error_type
            if isinstance(failure.error_type, str)
            else failure.error_type.value
        )
        return {
            "error_type": error_type,
            "error_message": failure.error_message,
            "suggestion": failure.suggestion,
            "failed_code": failure.code_snippet,
            "root_cause": failure.root_cause,
        }

    def _to_plain(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return {}

    def _to_plain_list(self, values: Any) -> List[Dict[str, Any]]:
        if not values:
            return []
        result = []
        for value in values:
            if isinstance(value, dict):
                result.append(value)
            elif hasattr(value, "model_dump"):
                result.append(value.model_dump())
            else:
                result.append({"value": value})
        return result

    def _success_report(
        self,
        iterations: int,
        final_code: List[Dict[str, Any]],
        runner_result: SandboxResult,
    ) -> SelfHealingReport:
        return SelfHealingReport(
            success=True,
            iterations=iterations,
            final_code=final_code,
            test_results={
                "passed": True,
                "exit_code": runner_result.exit_code,
                "logs": runner_result.logs,
            },
            failure_history=self._failure_history,
            total_time=self._elapsed(),
            iterations_log=self._iterations_log,
        )

    def _stopped_report(
        self,
        iterations: int,
        final_code: List[Dict[str, Any]],
        runner_result: SandboxResult,
        final_failure: FailureAnalysis,
    ) -> SelfHealingReport:
        return SelfHealingReport(
            success=False,
            iterations=iterations,
            final_code=final_code,
            test_results={
                "passed": False,
                "exit_code": runner_result.exit_code,
                "logs": runner_result.logs,
            },
            failure_history=self._failure_history,
            final_failure=final_failure,
            total_time=self._elapsed(),
            iterations_log=self._iterations_log,
        )

    def _failed_report(
        self, iterations: int, final_code: List[Dict[str, Any]], logs: str
    ) -> SelfHealingReport:
        return SelfHealingReport(
            success=False,
            iterations=iterations,
            final_code=final_code,
            test_results={"passed": False, "exit_code": 1, "logs": logs},
            failure_history=self._failure_history,
            final_failure=None,
            total_time=self._elapsed(),
            iterations_log=self._iterations_log,
        )

    def _elapsed(self) -> float:
        return time.time() - self._start_time
