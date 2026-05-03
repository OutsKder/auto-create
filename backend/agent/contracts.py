"""Shared Agent contracts.

This module is the single source of truth for structured data passed between
DevFlow agents. Agent implementations may still keep local parsing helpers, but
the artifacts stored in pipeline context should validate against these models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ChangeType = Literal["create", "modify", "delete"]
PatchFormat = Literal["search_replace", "full_content", "unified_diff"]
RiskLevel = Literal["low", "medium", "high", "critical", "unknown"]
TestType = Literal["unit", "integration", "e2e"]
AgentStatus = Literal["ok", "blocked", "failed"]


class ContractModel(BaseModel):
    """Base model for all contracts."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CodebaseRef(ContractModel):
    repo_id: str = ""
    repo_name: str = ""
    repo_path: str
    branch: str = "main"


class RequirementAnalystInput(ContractModel):
    requirement_raw: str = Field(min_length=1)
    codebase: Optional[CodebaseRef] = None


class RequirementStructured(ContractModel):
    is_clear: bool = True
    clarifying_questions: List[str] = Field(default_factory=list)
    goal: str
    features: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)


class HotFile(ContractModel):
    path: str
    content: str = ""
    score: float = 0.0
    evidence: List[str] = Field(default_factory=list)


class CoverageReport(ContractModel):
    requirement_points: List[Dict[str, Any]] = Field(default_factory=list)
    covered_points: List[str] = Field(default_factory=list)
    uncovered_points: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = "unknown"

    @field_validator("risk_level", mode="before")
    @classmethod
    def _normalize_risk_level(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class CodebaseContext(ContractModel):
    query: str = ""
    repo_skeleton: str = ""
    hot_files: List[HotFile] = Field(default_factory=list)
    dependency_signatures: List[str] = Field(default_factory=list)
    coverage_report: CoverageReport = Field(default_factory=CoverageReport)
    context_compaction: Dict[str, Any] = Field(default_factory=dict)


class TechArchitectInput(ContractModel):
    requirement_structured: RequirementStructured
    codebase: CodebaseRef


class FileChangePlan(ContractModel):
    file_path: str
    change_type: ChangeType
    description: str
    reason: str = ""
    risk_level: RiskLevel = "unknown"
    acceptance_links: List[str] = Field(default_factory=list)

    @field_validator("change_type", mode="before")
    @classmethod
    def _normalize_change_type(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("risk_level", mode="before")
    @classmethod
    def _normalize_risk_level(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class Design(ContractModel):
    architecture: str
    api_design: str = ""
    file_change_plan: List[FileChangePlan] = Field(default_factory=list)
    risk_analysis: str = ""


class CodeGeneratorInput(ContractModel):
    requirement_structured: RequirementStructured
    design: Design
    codebase_context: CodebaseContext
    codebase: CodebaseRef


class ValidationReport(ContractModel):
    static_checks: Any = Field(default_factory=list)
    runtime_checks: Any = Field(default_factory=list)


class Patch(ContractModel):
    """Structured code change instruction consumed by the codegen workflow.

    Semantics are shared by the generator and the patcher:
    - create: patch_format must be full_content and patch must be the complete file body.
    - modify: patch_format must be search_replace and patch must be a SEARCH/REPLACE block.
    - delete: patch may be empty, patch_format is accepted but not used by the patcher.
    """

    file_path: str
    change_type: ChangeType
    patch_format: PatchFormat = "search_replace"
    patch: str
    reason: Optional[str] = None
    risk_level: RiskLevel = "unknown"
    plan_item_id: Optional[str] = None

    @field_validator("change_type", "patch_format", "risk_level", mode="before")
    @classmethod
    def _normalize_enum_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def _validate_patch_semantics(self) -> "Patch":
        patch_text = (self.patch or "").strip()

        if self.change_type == "create":
            if self.patch_format != "full_content":
                raise ValueError("create patch must use full_content format")
            if any(
                marker in patch_text
                for marker in ("<<<<<<< SEARCH", "=======", ">>>>>>> REPLACE", "FILE:")
            ):
                raise ValueError(
                    "create patch must be raw full file content, not a SEARCH/REPLACE block"
                )

        if self.change_type == "modify" and self.patch_format != "search_replace":
            raise ValueError("modify patch must use search_replace format")

        return self


class DiffBundle(ContractModel):
    stage: Literal["coding"] = "coding"
    mode: Literal["diff_bundle"] = "diff_bundle"
    files_changed: List[str]
    patches: List[Patch]
    diff: str = ""
    validation: ValidationReport = Field(default_factory=ValidationReport)


class SDETInput(ContractModel):
    code_diff: DiffBundle
    requirement_structured: RequirementStructured
    design: Optional[Design] = None
    codebase_context: Optional[CodebaseContext] = None
    codebase: Optional[CodebaseRef] = None


class SandboxResult(ContractModel):
    passed: bool
    exit_code: int
    logs: str
    failure_stage: Optional[str] = None
    failure_type: Optional[str] = None
    failure_message: Optional[str] = None
    failure_context: Dict[str, Any] = Field(default_factory=dict)
    failed_patches: List[Dict[str, Any]] = Field(default_factory=list)
    failed_command: Optional[str] = None


class TestFile(ContractModel):
    file_path: str
    test_type: TestType
    covers: List[str] = Field(default_factory=list)
    content: str = ""


class TestPlanItem(ContractModel):
    acceptance_criterion: str
    test_type: TestType
    coverage_target: List[str] = Field(default_factory=list)


class TestBundle(ContractModel):
    stage: Literal["testing"] = "testing"
    test_plan: List[TestPlanItem] = Field(default_factory=list)
    test_files: List[TestFile] = Field(default_factory=list)
    test_code: str = ""
    runner_commands: List[str] = Field(default_factory=list)
    sandbox_result: Optional[SandboxResult] = None


class ReviewAgentInput(ContractModel):
    code_diff: DiffBundle
    design: Design
    tests: TestBundle


class ReviewIssue(ContractModel):
    severity: RiskLevel
    title: str
    detail: str
    file_path: Optional[str] = None
    suggestion: Optional[str] = None


class Review(ContractModel):
    passed: bool = Field(alias="pass")
    risk_level: RiskLevel = "unknown"
    issues: List[ReviewIssue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    release_blockers: List[str] = Field(default_factory=list)


class AgentTrace(ContractModel):
    stage: str
    agent: str
    started_at: Optional[datetime] = None
    elapsed_ms: Optional[int] = None
    tokens: Dict[str, int] = Field(default_factory=dict)
    retries: int = 0
    warnings: List[str] = Field(default_factory=list)


class AgentResult(ContractModel):
    stage: str
    output_key: str
    artifact: Dict[str, Any]
    status: AgentStatus = "ok"
    warnings: List[str] = Field(default_factory=list)
    trace: Optional[AgentTrace] = None


class PatchResult(ContractModel):
    file_path: str
    applied: bool
    message: Optional[str] = None
    error: Optional[str] = None
