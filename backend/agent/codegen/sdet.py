"""
sdet.py
测试生成 Agent 的完整实现：
- 读取 `code_diff` 与 `requirement_structured.acceptance_criteria`
- 使用 PromptManager 组装系统提示词、上下文提示词和指令提示词
- 调用 LLM 生成结构化 Test Bundle
- 对结果做 JSON 解析和结构校验
- 可选：自动执行测试并收集结果
如果 prompt 模板不可用，则退化为基于验收标准的最小可执行 Test Bundle，保证链路可用。
核心流程：
1. 构建提示词负载（系统提示词 + 上下文提示词 + 指令提示词）
2. 调用 LLM 生成测试代码
3. 解析响应并转换为 TestBundle 对象
4. 标准化测试运行命令
5. 根据配置决定是否自动执行测试
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..base import BaseAgent
from ..prompts.manager import PromptManager
from ..workspace import WorkspaceManager
from .models import Patch, TestBundle, TestFile, TestPlanItem, SandboxResult
from .patcher import Patcher
from .runner import Runner


class TestPlanSchema(BaseModel):
    """测试计划项的 Schema 定义。

    用于 LLM 响应的结构校验和数据转换。
    """

    acceptance_criterion: str = Field(...)  # 验收标准描述
    test_type: str = Field(...)  # 测试类型：unit、integration、e2e
    coverage_target: List[str] = Field(default_factory=list)  # 覆盖的目标文件


class TestFileSchema(BaseModel):
    """测试文件的 Schema 定义。

    用于 LLM 响应的结构校验和数据转换。
    """

    file_path: str = Field(...)  # 测试文件路径
    test_type: str = Field(...)  # 测试类型
    covers: List[str] = Field(default_factory=list)  # 覆盖的源代码文件


class SandboxResultSchema(BaseModel):
    """沙箱运行结果的 Schema 定义。
    用于 LLM 响应的结构校验和数据转换。
    """

    passed: bool = Field(default=False)  # 是否通过测试
    exit_code: int = Field(default=0)  # 进程退出码
    logs: str = Field(default="")  # 运行日志


class TestBundleSchema(BaseModel):
    """测试包的 Schema 定义。
    用于 LLM 响应的结构校验和数据转换。
    """

    stage: str = Field(default="testing")  # 当前阶段
    test_plan: List[TestPlanSchema] = Field(default_factory=list)  # 测试计划列表
    test_files: List[TestFileSchema] = Field(default_factory=list)  # 测试文件列表
    test_code: str = Field(default="")  # 生成的测试代码
    runner_commands: List[str] = Field(default_factory=list)  # 测试运行命令
    sandbox_result: SandboxResultSchema = Field(
        default_factory=SandboxResultSchema
    )  # 沙箱运行结果


class SDETAgent(BaseAgent):
    """测试生成 Agent（SDET Agent）。
    负责将代码变更和验收标准转换为结构化测试包。
    核心职责：
    - 读取代码变更和验收标准
    - 使用 PromptManager 组装提示词
    - 调用 LLM 生成测试代码和测试计划
    - 解析和校验结果
    - 可选：自动执行测试
    SDET: Software Development Engineer in Test
    """

    def __init__(
        self,
        llm_provider: Any,
        prompt_manager: Optional[PromptManager] = None,
        config: Any = None,
    ):
        """初始化 SDET Agent。

        Args:
            llm_provider: LLM 服务提供者，用于调用大语言模型生成测试代码
            prompt_manager: 提示词管理器，用于获取和渲染提示词模板
            config: 配置对象
        """
        super().__init__(llm_provider=llm_provider, config=config)
        self.prompt_manager = prompt_manager or PromptManager()

    def get_input_keys(self) -> List[str]:
        """获取 Agent 所需的输入键列表。
        Returns:
            输入键列表：code_diff（代码变更包）、requirement_structured（结构化需求）
        """
        return ["code_diff", "requirement_structured"]

    def get_output_key(self) -> str:
        """获取 Agent 输出的键名。
        Returns:
            输出键名：tests（测试包）
        """
        return "tests"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行测试生成的主入口方法。
        执行流程：
        1. 验证输入参数
        2. 构建提示词负载
        3. 调用 LLM 生成测试
        4. 解析响应并转换为 TestBundle
        5. 标准化测试运行命令
        6. 根据配置决定是否自动执行测试
        Args:
            context: 包含输入数据的上下文字典
        Returns:
            包含测试包的字典，键为 tests
        """
        # 验证输入参数
        self._validate_input(context)

        # 构建提示词负载
        prompt_payload = self._build_prompt_payload(context)

        # 调用 LLM 生成测试代码
        raw_response = self._call_llm(prompt_payload)

        # 解析响应并转换为 TestBundle
        bundle = self._parse_response(raw_response, context)

        # 标准化测试运行命令
        self._normalize_runner_commands(bundle)

        # 根据配置决定是否自动执行测试
        self._maybe_execute_tests(bundle, context)

        # 返回测试包
        return {"tests": bundle.model_dump()}

    def _normalize_runner_commands(self, bundle: TestBundle) -> None:
        """标准化测试运行命令。
        清理空命令，确保命令列表格式正确。
        Args:
            bundle: TestBundle 对象
        """
        commands = [
            str(cmd).strip()
            for cmd in (bundle.runner_commands or [])
            if str(cmd).strip()
        ]
        bundle.runner_commands = commands

    def _maybe_execute_tests(self, bundle: TestBundle, context: Dict[str, Any]) -> None:
        """根据配置决定是否自动执行测试。
        直接执行测试：先创建临时工作区，应用 code_diff，物化测试文件，再运行命令。
        Args:
            bundle: TestBundle 对象
            context: 上下文字典
        """
        # 解析代码仓库路径
        repo_path = self._resolve_repo_path(context)
        if not repo_path:
            bundle.sandbox_result = SandboxResult(
                passed=False,
                exit_code=1,
                logs="未提供 codebase.repo_path，无法执行测试命令",
            )
            return

        # 检查是否有测试命令
        if not bundle.runner_commands:
            bundle.sandbox_result = SandboxResult(
                passed=False,
                exit_code=1,
                logs="runner_commands 为空，无法执行测试命令",
            )
            return

        workspace_manager = WorkspaceManager()
        workspace_path = ""
        try:
            workspace_path = workspace_manager.create_workspace(repo_path)

            code_diff = context.get("code_diff", {}) or {}
            self._apply_code_diff_to_workspace(code_diff, workspace_path)

            self._materialize_test_bundle(bundle, workspace_path)

            testing_options = context.get("testing_options", {}) or {}
            use_docker = bool(testing_options.get("use_docker", False))
            docker_image = testing_options.get("docker_image")
            timeout = int(testing_options.get("timeout", 300))

            runner = Runner(
                use_docker=use_docker,
                docker_image=docker_image,
                timeout=timeout,
            )
            bundle.sandbox_result = runner.run_commands(
                commands=bundle.runner_commands,
                repo_path=workspace_path,
                sandbox_config=testing_options.get("sandbox_config", {}),
            )
        except Exception as exc:
            bundle.sandbox_result = SandboxResult(
                passed=False,
                exit_code=1,
                logs=f"Runner 执行异常: {exc}",
            )
        finally:
            if workspace_path:
                workspace_manager.cleanup_workspace(repo_path)

    def _apply_code_diff_to_workspace(
        self, code_diff: Dict[str, Any], workspace_path: str
    ) -> None:
        """把 code_diff 中的补丁应用到临时工作区。"""
        patches = code_diff.get("patches", []) or []
        if not patches:
            return

        patcher = Patcher(repo_root=workspace_path)
        applied_errors = []
        for patch_item in patches:
            patch = (
                patch_item
                if isinstance(patch_item, Patch)
                else Patch.model_validate(patch_item)
            )
            result = patcher.apply(patch)
            if not result.applied:
                applied_errors.append(
                    f"{result.file_path}: {result.error or result.message or 'unknown patch failure'}"
                )

        if applied_errors:
            raise RuntimeError("; ".join(applied_errors))

    def _materialize_test_bundle(self, bundle: TestBundle, workspace_path: str) -> None:
        """把 test_code / test_files 物化为临时工作区内的真实测试文件。"""
        file_paths = [
            item.file_path
            for item in (bundle.test_files or [])
            if str(item.file_path).strip()
        ]
        if not file_paths and bundle.test_code.strip():
            file_paths = ["tests/test_autogen.py"]

        if not file_paths:
            return

        for index, relative_path in enumerate(file_paths):
            target_path = self._resolve_workspace_path(workspace_path, relative_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            if index == 0 and bundle.test_code.strip():
                content = self._build_test_file_content(bundle.test_code)
            else:
                content = "# autogenerated placeholder\n"
            with open(target_path, "w", encoding="utf-8") as fh:
                fh.write(content)

    def _build_test_file_content(self, test_code: str) -> str:
        """给自动生成的测试文件补充项目根目录导入路径。"""
        header = (
            "import os\n"
            "import sys\n\n"
            "ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
            "if ROOT_DIR not in sys.path:\n"
            "    sys.path.insert(0, ROOT_DIR)\n\n"
        )
        return f"{header}{test_code.lstrip()}"

    def _resolve_workspace_path(self, workspace_path: str, relative_path: str) -> str:
        """把相对路径解析到工作区内，并阻止越界路径。"""
        normalized = os.path.normpath(relative_path).lstrip("\\/")
        if os.path.isabs(normalized):
            raise ValueError(f"测试文件路径必须是相对路径: {relative_path}")

        target_path = os.path.abspath(os.path.join(workspace_path, normalized))
        workspace_abs = os.path.abspath(workspace_path)
        if os.path.commonpath([workspace_abs, target_path]) != workspace_abs:
            raise ValueError(f"测试文件路径越界: {relative_path}")
        return target_path

    def _resolve_repo_path(self, context: Dict[str, Any]) -> str:
        """从上下文中解析代码仓库路径。

        Args:
            context: 上下文字典

        Returns:
            代码仓库路径，如果路径无效则返回空字符串
        """
        codebase = context.get("codebase", {}) or {}
        repo_path = str(codebase.get("repo_path", "")).strip()
        if repo_path and os.path.isdir(repo_path):
            return repo_path
        return ""

    def _build_prompt_payload(self, context: Dict[str, Any]) -> Dict[str, str]:
        """构建 LLM 调用所需的提示词负载。

        从上下文中提取所需信息，使用 PromptManager 获取并渲染提示词模板。

        Args:
            context: 输入上下文字典

        Returns:
            包含 system 和 user 提示词的字典
        """
        # 从上下文中提取输入数据
        code_diff = context.get("code_diff", {})
        requirement_structured = context.get("requirement_structured", {})
        design = context.get("design", {})
        codebase_context = context.get("codebase_context", {})

        # 提取验收标准
        acceptance_criteria = requirement_structured.get("acceptance_criteria", [])

        # 获取提示词模板
        system_prompt = self.prompt_manager.get_template("sdet", "system")
        context_prompt = self.prompt_manager.render_template(
            "sdet",
            "context",
            {
                "code_diff": code_diff,
                "acceptance_criteria": acceptance_criteria,
                "design": design,
                "codebase_context": codebase_context,
            },
        )
        instruction_prompt = self.prompt_manager.get_template("sdet", "instruction")

        # 如果模板不可用，使用默认提示词（降级策略）
        if not system_prompt:
            system_prompt = "你是一名严格的测试生成 Agent，只输出结构化 JSON。"
        if not instruction_prompt:
            instruction_prompt = '请输出 stage="testing" 的结构化 Test Bundle。'

        return {
            "system": system_prompt,
            "user": f"{context_prompt}\n\n{instruction_prompt}",
        }

    def _call_llm(self, prompt_payload: Dict[str, str]) -> str:
        """调用 LLM 生成测试代码。

        将提示词负载转换为标准的消息格式，调用 LLM 并返回响应内容。

        Args:
            prompt_payload: 包含 system 和 user 提示词的字典

        Returns:
            LLM 返回的响应内容字符串
        """
        messages = [
            {"role": "system", "content": prompt_payload["system"]},
            {"role": "user", "content": prompt_payload["user"]},
        ]
        response = self.llm.invoke(messages)
        if isinstance(response, dict):
            return str(response.get("content", ""))
        return getattr(response, "content", str(response))

    def _parse_response(self, raw_response: str, context: Dict[str, Any]) -> TestBundle:
        """解析 LLM 响应并转换为 TestBundle 对象。
        解析流程：
        1. 从原始响应中提取 JSON 字符串
        2. 解析 JSON 并使用 Pydantic 进行结构校验
        3. 转换为 TestBundle 对象
        4. 如果解析失败，使用降级策略生成最小测试包
        Args:
            raw_response: LLM 返回的原始响应字符串
            context: 输入上下文字典，用于降级时生成测试包
        Returns:
            TestBundle 对象
        """
        json_text = self._extract_json(raw_response)
        if json_text:
            try:
                parsed = json.loads(json_text)
                bundle_schema = TestBundleSchema.model_validate(parsed)
                return self._schema_to_bundle(bundle_schema)
            except Exception:
                pass

        return self._fallback_bundle(context)

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 字符串。

        支持多种格式：
        1. 纯 JSON（以 { 开头，以 } 结尾）
        2. Markdown 代码块包裹的 JSON（```json ... ```）
        3. 任意位置的 JSON 对象

        Args:
            text: 包含 JSON 的文本字符串

        Returns:
            提取出的 JSON 字符串，如果未找到则返回空字符串
        """
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return text

        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
        if match:
            return match.group(1)

        match = re.search(r"(\{.*\})", text, re.S)
        if match:
            return match.group(1)

        return ""

    def _schema_to_bundle(self, bundle_schema: TestBundleSchema) -> TestBundle:
        """将 Schema 对象转换为领域模型对象。

        将 Pydantic Schema 对象转换为业务领域模型对象。

        Args:
            bundle_schema: TestBundleSchema 对象

        Returns:
            TestBundle 对象
        """
        return TestBundle(
            stage=bundle_schema.stage,
            test_plan=[
                TestPlanItem(
                    acceptance_criterion=item.acceptance_criterion,
                    test_type=item.test_type,
                    coverage_target=item.coverage_target,
                )
                for item in bundle_schema.test_plan
            ],
            test_files=[
                TestFile(
                    file_path=item.file_path,
                    test_type=item.test_type,
                    covers=item.covers,
                )
                for item in bundle_schema.test_files
            ],
            test_code=bundle_schema.test_code,
            runner_commands=bundle_schema.runner_commands,
            sandbox_result=SandboxResult(
                passed=bundle_schema.sandbox_result.passed,
                exit_code=bundle_schema.sandbox_result.exit_code,
                logs=bundle_schema.sandbox_result.logs,
            ),
        )

    def _fallback_bundle(self, context: Dict[str, Any]) -> TestBundle:
        """生成降级的最小测试包。

        当 LLM 响应无法解析或解析失败时，使用验收标准生成最小可执行测试包。
        这是一个保底策略，确保即使 LLM 生成失败，系统也能继续运行。

        Args:
            context: 输入上下文字典，包含结构化需求信息

        Returns:
            基于验收标准生成的 TestBundle 对象
        """
        # 从需求中提取验收标准
        requirement_structured = context.get("requirement_structured", {})
        acceptance_criteria = (
            requirement_structured.get("acceptance_criteria", []) or []
        )

        # 根据验收标准生成测试计划
        test_plan = [
            TestPlanItem(
                acceptance_criterion=str(ac),
                test_type="unit",
                coverage_target=[],
            )
            for ac in acceptance_criteria
        ]

        # 生成对应的测试文件列表
        test_files = [
            TestFile(
                file_path=f"tests/test_autogen_{idx}.py",
                test_type="unit",
                covers=[],
            )
            for idx, _ in enumerate(test_plan)
        ]

        # 生成测试运行命令
        runner_commands = ["pytest -q --maxfail=1"] if test_plan else ["pytest -q"]

        # 返回降级的测试包
        return TestBundle(
            stage="testing",
            test_plan=test_plan,
            test_files=test_files,
            test_code="",
            runner_commands=runner_commands,
            sandbox_result=SandboxResult(passed=False, exit_code=0, logs=""),
        )
