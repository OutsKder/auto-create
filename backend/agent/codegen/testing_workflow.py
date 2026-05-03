"""Workflow for applying generated code and executing generated tests.

SDETAgent is responsible for producing a structured TestBundle. This workflow
owns the side effects around that bundle: creating an isolated workspace,
applying code patches, writing generated tests, running commands, and writing
the SandboxResult back to the bundle.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ..workspace import WorkspaceManager
from ..contracts import Patch, SandboxResult, TestBundle, TestFile
from .patcher import Patcher
from .runner import Runner


class TestingWorkflowConfig(BaseModel):
    """Runtime settings for isolated test execution."""

    use_docker: bool = False
    docker_image: Optional[str] = None
    timeout: int = 300
    sandbox_config: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_context(cls, context: Dict[str, Any]) -> "TestingWorkflowConfig":
        return cls.model_validate(context.get("testing_options", {}) or {})


class TestingWorkflow:
    """Execute a generated TestBundle against a patched workspace."""

    def __init__(
        self,
        workspace_manager: Optional[WorkspaceManager] = None,
        default_config: Optional[TestingWorkflowConfig] = None,
    ):
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.default_config = default_config or TestingWorkflowConfig()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run tests from context and return an updated ``{"tests": ...}``.

        Expected context keys:
        - codebase.repo_path: source repository to copy into an isolated workspace
        - code_diff: DiffBundle-like dict containing patches
        - tests: TestBundle-like dict produced by SDETAgent
        - testing_options: optional Runner settings
        """
        bundle = self._resolve_test_bundle(context.get("tests"))
        executed = self.run(context=context, bundle=bundle)
        return {"tests": executed.model_dump()}

    def run(self, context: Dict[str, Any], bundle: TestBundle) -> TestBundle:
        """Apply code_diff, materialize tests, run commands, and return bundle."""
        repo_path = self._resolve_repo_path(context)
        if not repo_path:
            bundle.sandbox_result = self._build_failure_result(
                stage="workspace",
                failure_type="missing_repo_path",
                exit_code=1,
                message="Missing or invalid codebase.repo_path; cannot run tests.",
                failure_context={"codebase.repo_path": context.get("codebase", {}).get("repo_path")},
            )
            return bundle

        if not bundle.runner_commands:
            bundle.sandbox_result = self._build_failure_result(
                stage="testing",
                failure_type="missing_runner_commands",
                exit_code=1,
                message="runner_commands is empty; cannot run tests.",
                failure_context={"runner_commands": []},
            )
            return bundle

        workspace_path = ""
        try:
            workspace_path = self.workspace_manager.create_workspace(repo_path)
            patch_errors = self._apply_code_diff_to_workspace(
                context.get("code_diff", {}) or {}, workspace_path
            )
            if patch_errors:
                bundle.sandbox_result = self._build_failure_result(
                    stage="patching",
                    failure_type="patch_application_failed",
                    exit_code=1,
                    message="; ".join(
                        f"{item.get('file_path')}: {item.get('error') or item.get('message') or 'unknown patch failure'}"
                        for item in patch_errors
                    ),
                    failure_context={
                        "repo_path": repo_path,
                        "workspace_path": workspace_path,
                        "error_count": len(patch_errors),
                    },
                    failed_patches=patch_errors,
                )
                return bundle

            self._materialize_test_bundle(bundle, workspace_path)

            config = self._resolve_config(context)
            runner = Runner(
                use_docker=config.use_docker,
                docker_image=config.docker_image,
                timeout=config.timeout,
            )
            bundle.sandbox_result = runner.run_commands(
                commands=bundle.runner_commands,
                repo_path=workspace_path,
                sandbox_config=config.sandbox_config,
            )
            if not bundle.sandbox_result.passed:
                bundle.sandbox_result = self._augment_failure_result(
                    bundle.sandbox_result,
                    stage="testing",
                    failure_type="test_command_failed",
                    failure_context={
                        "repo_path": repo_path,
                        "workspace_path": workspace_path,
                        "runner_commands": bundle.runner_commands,
                    },
                    failed_command=self._last_runner_command(bundle.runner_commands),
                )
        except Exception as exc:
            bundle.sandbox_result = self._build_failure_result(
                stage="execution",
                failure_type="workflow_exception",
                exit_code=1,
                message=f"TestingWorkflow execution failed: {exc}",
                failure_context={
                    "repo_path": repo_path,
                    "workspace_path": workspace_path or None,
                },
            )
        finally:
            if workspace_path:
                self.workspace_manager.cleanup_workspace(repo_path)

        return bundle

    def _resolve_config(self, context: Dict[str, Any]) -> TestingWorkflowConfig:
        raw_options = context.get("testing_options")
        if raw_options is None:
            return self.default_config

        merged = self.default_config.model_dump()
        merged.update(raw_options or {})
        return TestingWorkflowConfig.model_validate(merged)

    def _resolve_test_bundle(self, tests: Any) -> TestBundle:
        if isinstance(tests, TestBundle):
            return tests
        if tests is None:
            raise ValueError("TestingWorkflow requires tests in context.")
        return TestBundle.model_validate(tests)

    def _apply_code_diff_to_workspace(
        self, code_diff: Dict[str, Any], workspace_path: str
    ) -> list[Dict[str, Any]]:
        patches = code_diff.get("patches", []) or []
        if not patches:
            return []

        patcher = Patcher(repo_root=workspace_path)
        errors: list[Dict[str, Any]] = []
        for patch_item in patches:
            patch = (
                patch_item
                if isinstance(patch_item, Patch)
                else Patch.model_validate(patch_item)
            )
            self._resolve_workspace_path(workspace_path, patch.file_path)
            result = patcher.apply(patch)
            if not result.applied:
                errors.append(result.model_dump())

        return errors

    def _materialize_test_bundle(self, bundle: TestBundle, workspace_path: str) -> None:
        # Prefer writing per-file content if provided; otherwise fall back to bundle.test_code
        file_items = [item for item in (bundle.test_files or []) if str(item.file_path).strip()]
        if not file_items and bundle.test_code.strip():
            file_items = [TestFile(file_path="tests/test_autogen.py", test_type="unit", covers=[], content=bundle.test_code)]

        for index, file_item in enumerate(file_items):
            relative_path = file_item.file_path
            target_path = self._resolve_workspace_path(workspace_path, relative_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            if getattr(file_item, "content", "") and str(file_item.content).strip():
                content = self._build_test_file_content(file_item.content)
            elif index == 0 and bundle.test_code.strip():
                content = self._build_test_file_content(bundle.test_code)
            else:
                content = "# autogenerated placeholder\n"
            with open(target_path, "w", encoding="utf-8") as fh:
                fh.write(content)

    def _build_test_file_content(self, test_code: str) -> str:
        header = (
            "import os\n"
            "import sys\n\n"
            "ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
            "if ROOT_DIR not in sys.path:\n"
            "    sys.path.insert(0, ROOT_DIR)\n\n"
        )
        return f"{header}{test_code.lstrip()}"

    def _resolve_workspace_path(self, workspace_path: str, relative_path: str) -> str:
        normalized = os.path.normpath(str(relative_path)).lstrip("\\/")
        if not normalized or os.path.isabs(normalized):
            raise ValueError(f"Workspace path must be relative: {relative_path}")

        target_path = os.path.abspath(os.path.join(workspace_path, normalized))
        workspace_abs = os.path.abspath(workspace_path)
        if os.path.commonpath([workspace_abs, target_path]) != workspace_abs:
            raise ValueError(f"Workspace path escapes sandbox: {relative_path}")
        return target_path

    def _resolve_repo_path(self, context: Dict[str, Any]) -> str:
        codebase = context.get("codebase", {}) or {}
        repo_path = str(codebase.get("repo_path", "")).strip()
        if repo_path and os.path.isdir(repo_path):
            return repo_path
        return ""

    def _build_failure_result(
        self,
        stage: str,
        failure_type: str,
        exit_code: int,
        message: str,
        failure_context: Optional[Dict[str, Any]] = None,
        failed_patches: Optional[list[Dict[str, Any]]] = None,
        failed_command: Optional[str] = None,
    ) -> SandboxResult:
        return SandboxResult(
            passed=False,
            exit_code=exit_code,
            logs=message,
            failure_stage=stage,
            failure_type=failure_type,
            failure_message=message,
            failure_context=failure_context or {},
            failed_patches=failed_patches or [],
            failed_command=failed_command,
        )

    def _augment_failure_result(
        self,
        result: SandboxResult,
        stage: str,
        failure_type: str,
        failure_context: Optional[Dict[str, Any]] = None,
        failed_command: Optional[str] = None,
    ) -> SandboxResult:
        return SandboxResult(
            passed=False,
            exit_code=result.exit_code,
            logs=result.logs,
            failure_stage=stage,
            failure_type=failure_type,
            failure_message=(result.logs or "").strip(),
            failure_context=failure_context or {},
            failed_patches=[],
            failed_command=failed_command,
        )

    def _last_runner_command(self, commands: list[str]) -> Optional[str]:
        return commands[-1] if commands else None
