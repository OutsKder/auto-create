"""
codegen 包入口。

这个包承载代码生成链路的核心实现与结构化数据模型：
- models: DiffBundle / TestBundle / SandboxResult 等数据结构
- patcher: Search/Replace 补丁应用器
- runner: 沙盒执行器
- code_generator: 代码生成 Agent 核心实现
- sdet: 测试生成 Agent 核心实现

上层 `backend.agent.agents` 会通过适配器调用这里的实现，以保持职责清晰。
"""

from .models import (
    DiffBundle,
    Patch,
    PatchResult,
    SandboxResult,
    TestBundle,
    TestFile,
    TestPlanItem,
)
from .patcher import PatchApplyError, Patcher
from .runner import Runner
from .code_generator import CodeGeneratorAgent
from .sdet import SDETAgent

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
]
