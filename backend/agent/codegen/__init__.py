"""Code generation runtime exports.

Canonical data contracts live in ``backend.agent.contracts``. This package
exports codegen executors and the most common contract classes for convenient
runtime imports.
"""

from ..contracts import (
    DiffBundle,
    Patch,
    PatchResult,
    SandboxResult,
    TestBundle,
    TestFile,
    TestPlanItem,
)
from .code_generator import CodeGeneratorAgent
from .patcher import PatchApplyError, Patcher
from .runner import Runner
from .sdet import SDETAgent
from .testing_workflow import TestingWorkflow, TestingWorkflowConfig

__all__ = [
    "DiffBundle",
    "Patch",
    "PatchResult",
    "SandboxResult",
    "TestBundle",
    "TestFile",
    "TestPlanItem",
    "PatchApplyError",
    "Patcher",
    "Runner",
    "CodeGeneratorAgent",
    "SDETAgent",
    "TestingWorkflow",
    "TestingWorkflowConfig",
]
