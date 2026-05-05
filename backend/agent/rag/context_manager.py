import json
from typing import Any, Dict

from ..tools.codebase_context import CodebaseContextTool


class ContextManager:
    """Legacy compatibility wrapper for the original context synthesis prototype.

    The real implementation now lives in backend.agent.tools.codebase_context.
    This adapter is kept only so older scripts can keep importing ContextManager.
    """

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    def generate_codebase_context(self, requirement_structured: Dict[str, Any]) -> str:
        """Return the legacy JSON string expected by old scripts."""
        tool = CodebaseContextTool(self.workspace_root)
        context = tool.extract_context(
            context={"codebase": {"repo_path": self.workspace_root}},
            query=str(requirement_structured.get("goal", "") or ""),
        )
        payload = {
            "repo_skeleton": context.get("repo_skeleton", ""),
            "hot_files": context.get("hot_files", []),
            "dependency_signatures": context.get("dependency_signatures", []),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
