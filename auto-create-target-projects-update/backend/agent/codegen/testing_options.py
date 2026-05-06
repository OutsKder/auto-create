"""Reusable testing_options presets for TestingWorkflow/Runner.

Profiles:
- read_write: for tests that need writing files (history persistence, snapshots, etc.)
- read_only: for strict non-mutating test runs.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


TESTING_OPTIONS_PRESETS: Dict[str, Dict[str, Any]] = {
    "read_write": {
        "use_docker": True,
        "timeout": 300,
        "sandbox_config": {
            "network_disabled": True,
            "read_only": False,
            "cpus": "1",
            "memory": "1g",
            "pids_limit": "256",
            "tmpfs_size": "256m",
        },
    },
    "read_only": {
        "use_docker": True,
        "timeout": 300,
        "sandbox_config": {
            "network_disabled": True,
            "read_only": True,
            "cpus": "1",
            "memory": "512m",
            "pids_limit": "256",
            "tmpfs_size": "256m",
        },
    },
}


def build_testing_options(
    profile: str = "read_write",
    overrides: Dict[str, Any] | None = None,
    default_use_docker: bool = True,
) -> Dict[str, Any]:
    """Return merged testing options from preset profile + caller overrides."""
    preset = TESTING_OPTIONS_PRESETS.get(profile) or TESTING_OPTIONS_PRESETS["read_write"]
    options = deepcopy(preset)
    options["use_docker"] = bool(default_use_docker)

    overrides = overrides or {}
    sandbox_overrides = overrides.get("sandbox_config", {}) or {}

    options.update({k: v for k, v in overrides.items() if k != "sandbox_config"})
    merged_sandbox = dict(options.get("sandbox_config", {}))
    merged_sandbox.update(sandbox_overrides)
    options["sandbox_config"] = merged_sandbox
    return options
