"""
models.py

定义 CodeGen 模块使用的结构化数据模型（Pydantic）：
- Patch: 单个文件的补丁描述（search/replace 格式）
- DiffBundle: 一次 CodeGen 输出的结构化变更包
- PatchResult / SandboxResult: 补丁应用与沙箱运行结果
- TestFile / TestPlanItem / TestBundle: 测试相关模型
这些模型用于 Agent 之间的结构化传递与审计追踪。
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class Patch(BaseModel):
    """单个文件的补丁描述模型。

    描述对一个文件的具体修改操作，支持 search_replace 格式的补丁。
    """

    file_path: str  # 目标文件的相对路径
    change_type: str  # 修改类型：create（新建）、modify（修改）、delete（删除）
    patch_format: str  # 补丁格式：search_replace（搜索替换格式）
    patch: str  # 补丁内容，格式为：<搜索内容>\n=======\n<替换内容>\n>>>>>>> REPLACE
    reason: Optional[str] = None  # 变更原因说明，用于审计追踪
    risk_level: Optional[str] = "unknown"  # 风险等级：low、medium、high、unknown


class DiffBundle(BaseModel):
    """代码变更包模型。

    表示一次完整的代码生成输出，包含多个文件的补丁集合。
    """

    stage: str = "coding"  # 当前阶段：coding（编码阶段）
    mode: str = "diff_bundle"  # 输出模式：diff_bundle（变更包模式）
    files_changed: List[str]  # 变更的文件路径列表
    patches: List[Patch]  # 补丁列表，每个补丁对应一个文件的修改
    diff: Optional[str] = None  # 合并后的统一 diff 字符串（可选）
    validation: Optional[dict] = None  # 校验结果信息，包含静态检查和运行时检查结果


class PatchResult(BaseModel):
    """补丁应用结果模型。

    记录单个补丁应用到目标文件后的执行结果。
    """

    file_path: str  # 目标文件路径
    applied: bool  # 是否成功应用
    message: Optional[str] = None  # 成功时的消息
    error: Optional[str] = None  # 失败时的错误信息


class SandboxResult(BaseModel):
    """沙箱运行结果模型。

    记录代码在隔离环境中运行的结果，用于安全验证和功能测试。
    """

    passed: bool  # 是否通过验证
    exit_code: int  # 进程退出码（0 表示成功）
    logs: str  # 运行日志输出


class TestFile(BaseModel):
    """测试文件模型。

    描述一个测试文件及其覆盖范围。
    """

    file_path: str  # 测试文件路径
    test_type: (
        str  # 测试类型：unit（单元测试）、integration（集成测试）、e2e（端到端测试）
    )
    covers: List[str]  # 该测试文件覆盖的源代码文件路径列表


class TestPlanItem(BaseModel):
    """测试计划项模型。

    描述一个验收标准对应的测试计划。
    """

    acceptance_criterion: str  # 验收标准描述
    test_type: str  # 测试类型：unit、integration、e2e
    coverage_target: List[str]  # 测试覆盖的目标文件或功能点


class TestBundle(BaseModel):
    """测试包模型。

    表示一次完整的测试计划和执行结果。
    """

    stage: str = "testing"  # 当前阶段：testing（测试阶段）
    test_plan: List[TestPlanItem]  # 测试计划列表
    test_files: List[TestFile]  # 测试文件列表
    test_code: Optional[str]  # 生成的测试代码内容（可选）
    runner_commands: List[str]  # 测试运行命令列表
    sandbox_result: Optional[SandboxResult]  # 沙箱运行结果（可选）
