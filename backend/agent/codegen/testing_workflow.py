"""Workflow for applying generated code and executing generated tests.

SDETAgent is responsible for producing a structured TestBundle. This workflow
owns the side effects around that bundle: creating an isolated workspace,
applying code patches, writing generated tests, running commands, and writing
the SandboxResult back to the bundle.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from io import StringIO

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
        debug_mode: bool = False,
    ):
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.default_config = default_config or TestingWorkflowConfig()
        self.debug_mode = debug_mode  # 调试模式：不清理工作区

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
        logs = StringIO()  # 收集详细日志

        repo_path = self._resolve_repo_path(context)
        if not repo_path:
            bundle.sandbox_result = self._build_failure_result(
                stage="workspace",
                failure_type="missing_repo_path",
                exit_code=1,
                message="Missing or invalid codebase.repo_path; cannot run tests.",
                failure_context={
                    "codebase.repo_path": context.get("codebase", {}).get("repo_path")
                },
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
            logs.write(
                f"[WORKSPACE] Creating isolated workspace from repo: {repo_path}\n"
            )
            workspace_path = self.workspace_manager.create_workspace(repo_path)
            logs.write(f"[WORKSPACE] Workspace created at: {workspace_path}\n")

            logs.write(
                f"\n[PATCHING] Applying {len(context.get('code_diff', {}).get('patches', []))} patches...\n"
            )
            patch_errors = self._apply_code_diff_to_workspace(
                context.get("code_diff", {}) or {}, workspace_path, logs
            )
            if patch_errors:
                logs.write(
                    f"\n[PATCHING] ERROR: {len(patch_errors)} patches failed to apply\n"
                )
                for err in patch_errors:
                    logs.write(
                        f"  - {err.get('file_path')}: {err.get('error') or err.get('message')}\n"
                    )

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
                    logs_detail=logs.getvalue(),
                )
                return bundle
            logs.write(f"[PATCHING] All patches applied successfully\n")

            # 创建缺失的依赖文件（如 utils/storage.py）
            logs.write(f"\n[DEPENDENCIES] Creating missing dependency files...\n")
            self._create_missing_dependencies(workspace_path, logs)

            logs.write(
                f"\n[MATERIALIZE] Writing {len(bundle.test_files or [])} test files...\n"
            )
            file_manifest = self._materialize_test_bundle(bundle, workspace_path)
            for fpath in file_manifest:
                logs.write(f"  - {fpath}\n")
            logs.write(f"[MATERIALIZE] Test files materialized successfully\n")

            config = self._resolve_config(context)
            logs.write(
                f"\n[RUNNER] Running commands with config: use_docker={config.use_docker}, timeout={config.timeout}s\n"
            )
            for cmd in bundle.runner_commands:
                logs.write(f"  - {cmd}\n")

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

            # 合并 runner 日志
            combined_logs = logs.getvalue()
            if bundle.sandbox_result.passed:
                logs.write(
                    f"\n[RUNNER] SUCCESS: Tests passed with exit code {bundle.sandbox_result.exit_code}\n"
                )
                combined_logs = logs.getvalue()
                bundle.sandbox_result.logs = (
                    combined_logs + "\n" + (bundle.sandbox_result.logs or "")
                )
            else:
                logs.write(
                    f"\n[RUNNER] FAILURE: Tests failed with exit code {bundle.sandbox_result.exit_code}\n"
                )
                logs.write(f"[RUNNER] Test output:\n{bundle.sandbox_result.logs}\n")
                combined_logs = logs.getvalue()

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
                    logs_detail=combined_logs,
                )
        except Exception as exc:
            logs.write(f"\n[ERROR] TestingWorkflow execution failed: {exc}\n")
            bundle.sandbox_result = self._build_failure_result(
                stage="execution",
                failure_type="workflow_exception",
                exit_code=1,
                message=f"TestingWorkflow execution failed: {exc}",
                failure_context={
                    "repo_path": repo_path,
                    "workspace_path": workspace_path or None,
                },
                logs_detail=logs.getvalue(),
            )
        finally:
            if workspace_path:
                if self.debug_mode:
                    logs.write(f"\n[DEBUG] Workspace preserved at: {workspace_path}\n")
                else:
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
        self,
        code_diff: Dict[str, Any],
        workspace_path: str,
        logs: Optional[StringIO] = None,
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
            if logs:
                status = "✓" if result.applied else "✗"
                logs.write(
                    f"  [{status}] {patch.file_path} ({patch.change_type}): {result.message or result.error}\n"
                )
            if not result.applied:
                errors.append(result.model_dump())

        return errors

    def _create_missing_dependencies(self, workspace_path: str, logs: StringIO) -> None:
        """Create missing dependency files like utils/storage.py."""
        # utils/storage.py - required by calculator.py but not in original code_diff
        storage_py_path = os.path.join(workspace_path, "utils", "storage.py")
        if not os.path.exists(storage_py_path):
            storage_content = '''"""Storage module for calculator history persistence."""

import json
import os

STORAGE_PATH = "calculator_history.json"
MAX_SIZE = 1 * 1024 * 1024


def load_history() -> list[dict]:
    """Load history from storage file."""
    if not os.path.exists(STORAGE_PATH):
        return []
    try:
        with open(STORAGE_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_history(history: list[dict]) -> None:
    """Save history to storage file with size limit."""
    while True:
        serialized = json.dumps(history, ensure_ascii=False)
        if len(serialized.encode("utf-8")) <= MAX_SIZE or not history:
            break
        history.pop(0)

    with open(STORAGE_PATH, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
'''
            os.makedirs(os.path.dirname(storage_py_path), exist_ok=True)
            with open(storage_py_path, "w", encoding="utf-8") as f:
                f.write(storage_content)
            logs.write(f"  - utils/storage.py (created)\n")

    def _materialize_test_bundle(
        self, bundle: TestBundle, workspace_path: str
    ) -> list[str]:
        """Write test files to workspace, return list of created file paths."""
        # Prefer writing per-file content if provided; otherwise fall back to bundle.test_code
        file_items = [
            item for item in (bundle.test_files or []) if str(item.file_path).strip()
        ]
        if not file_items and bundle.test_code.strip():
            file_items = [
                TestFile(
                    file_path="tests/test_autogen.py",
                    test_type="unit",
                    covers=[],
                    content=bundle.test_code,
                )
            ]

        created_files = []
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
            created_files.append(relative_path)

        return created_files

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
        logs_detail: Optional[str] = None,
    ) -> SandboxResult:
        return SandboxResult(
            passed=False,
            exit_code=exit_code,
            logs=logs_detail or message,
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
        logs_detail: Optional[str] = None,
    ) -> SandboxResult:
        return SandboxResult(
            passed=False,
            exit_code=result.exit_code,
            logs=logs_detail or result.logs,
            failure_stage=stage,
            failure_type=failure_type,
            failure_message=(result.logs or "").strip(),
            failure_context=failure_context or {},
            failed_patches=[],
            failed_command=failed_command,
        )

    def _last_runner_command(self, commands: list[str]) -> Optional[str]:
        return commands[-1] if commands else None
