"""Workspace manager for isolated execution.

This helper creates a temporary workspace under ``backend/agent/workspace``
using the original repository name as the folder name. The workspace is
intended to be copied from a source repository, mutated, and cleaned up after
execution.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkspaceManager:
    """Manage temporary workspaces under the agent workspace directory."""

    workspace_root: Optional[str] = None

    def __post_init__(self) -> None:
        if self.workspace_root:
            self.workspace_root = os.path.abspath(self.workspace_root)
        else:
            self.workspace_root = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.workspace_root, exist_ok=True)

    def resolve_workspace_path(self, source_repo_path: str) -> str:
        """Return the workspace path derived from the source repository name."""
        repo_name = os.path.basename(os.path.normpath(source_repo_path))
        if not repo_name:
            raise ValueError("source_repo_path must not be empty")
        return os.path.join(self.workspace_root, repo_name)

    def create_workspace(self, source_repo_path: str) -> str:
        """Create a clean workspace by copying the source repository."""
        if not os.path.isdir(source_repo_path):
            raise FileNotFoundError(f"source repo not found: {source_repo_path}")

        workspace_path = self.resolve_workspace_path(source_repo_path)
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)
        shutil.copytree(source_repo_path, workspace_path)
        return workspace_path

    def cleanup_workspace(self, source_repo_path: str) -> None:
        """Remove the workspace for the given source repository if it exists."""
        workspace_path = self.resolve_workspace_path(source_repo_path)
        shutil.rmtree(workspace_path, ignore_errors=True)
