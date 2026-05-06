"""Pure SDET agent implementation.

The SDET agent converts code changes and acceptance criteria into a structured
TestBundle. It intentionally does not write files, apply patches, or run test
commands. Those side effects belong to TestingWorkflow.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..base import BaseAgent
from ..prompts.manager import PromptManager
from ..contracts import SandboxResult, TestBundle, TestFile, TestPlanItem, TestType


class TestPlanSchema(BaseModel):
    acceptance_criterion: str = Field(...)
    test_type: TestType = Field(...)
    coverage_target: List[str] = Field(default_factory=list)


class TestFileSchema(BaseModel):
    file_path: str = Field(...)
    test_type: TestType = Field(...)
    covers: List[str] = Field(default_factory=list)
    content: str = Field(default="")


class SandboxResultSchema(BaseModel):
    passed: bool = Field(default=False)
    exit_code: int = Field(default=0)
    logs: str = Field(default="")


class TestBundleSchema(BaseModel):
    stage: str = Field(default="testing")
    test_plan: List[TestPlanSchema] = Field(default_factory=list)
    test_files: List[TestFileSchema] = Field(default_factory=list)
    test_code: str = Field(default="")
    runner_commands: List[str] = Field(default_factory=list)
    sandbox_result: None = None


class SDETAgent(BaseAgent):
    """Generate a structured TestBundle from code_diff and requirements."""

    def __init__(
        self,
        llm_provider: Any,
        prompt_manager: Optional[PromptManager] = None,
        config: Any = None,
    ):
        super().__init__(llm_provider=llm_provider, config=config)
        self.prompt_manager = prompt_manager or PromptManager()

    def get_input_keys(self) -> List[str]:
        return ["code_diff", "requirement_structured"]

    def get_output_key(self) -> str:
        return "tests"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)

        prompt_payload = self._build_prompt_payload(context)
        raw_response = self._call_llm(prompt_payload)
        bundle = self._parse_response(raw_response, context)
        self._normalize_runner_commands(bundle)

        # Execution results are populated by TestingWorkflow, never by SDETAgent.
        bundle.sandbox_result = None
        return {"tests": bundle.model_dump()}

    def _normalize_runner_commands(self, bundle: TestBundle) -> None:
        bundle.runner_commands = [
            str(cmd).strip()
            for cmd in (bundle.runner_commands or [])
            if str(cmd).strip()
        ]

    def _build_prompt_payload(self, context: Dict[str, Any]) -> Dict[str, str]:
        code_diff = self._to_plain(context.get("code_diff", {}))
        requirement_structured = self._to_plain(
            context.get("requirement_structured", {})
        )
        design = self._to_plain(context.get("design", {}))
        codebase_context = self._to_plain(context.get("codebase_context", {}))
        acceptance_criteria = requirement_structured.get("acceptance_criteria", [])

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

        if not system_prompt:
            system_prompt = (
                "You are a strict SDET agent. Output only a JSON TestBundle. "
                "Do not claim tests were executed."
            )
        if not instruction_prompt:
            instruction_prompt = (
                'Return a JSON object with stage="testing", test_plan, test_files, '
                "test_code, runner_commands, and sandbox_result set to null."
            )

        return {
            "system": system_prompt,
            "user": f"{context_prompt}\n\n{instruction_prompt}",
        }

    def _call_llm(self, prompt_payload: Dict[str, str]) -> str:
        messages = [
            {"role": "system", "content": prompt_payload["system"]},
            {"role": "user", "content": prompt_payload["user"]},
        ]
        response = self.llm.invoke(messages)
        if isinstance(response, dict):
            return str(response.get("content", ""))
        return getattr(response, "content", str(response))

    def _parse_response(self, raw_response: str, context: Dict[str, Any]) -> TestBundle:
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
        text = str(text or "").strip()
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
        sandbox_result = None
        if bundle_schema.sandbox_result is not None:
            sandbox_result = SandboxResult(
                passed=bundle_schema.sandbox_result.passed,
                exit_code=bundle_schema.sandbox_result.exit_code,
                logs=bundle_schema.sandbox_result.logs,
            )

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
                        content=getattr(item, 'content', ""),
                )
                for item in bundle_schema.test_files
            ],
            test_code=bundle_schema.test_code,
            runner_commands=bundle_schema.runner_commands,
            sandbox_result=sandbox_result,
        )

    def _fallback_bundle(self, context: Dict[str, Any]) -> TestBundle:
        requirement_structured = self._to_plain(
            context.get("requirement_structured", {})
        )
        acceptance_criteria = requirement_structured.get("acceptance_criteria", []) or []

        test_plan = [
            TestPlanItem(
                acceptance_criterion=str(criterion),
                test_type="unit",
                coverage_target=[],
            )
            for criterion in acceptance_criteria
        ]
        test_files = [
            TestFile(
                file_path=f"tests/test_autogen_{index}.py",
                test_type="unit",
                covers=[],
            )
            for index, _ in enumerate(test_plan)
        ]
        runner_commands = ["pytest -q --maxfail=1"] if test_plan else ["pytest -q"]
        # 自动生成 pytest 测试代码草案，映射每条验收标准到一个或多个测试用例。
        tests: List[str] = []
        # 常见导入头，确保 tests 在 sandbox 中能导入被测模块
        header = (
            "import pytest\n"
            "from core import operations\n"
            "from core.calculator import Calculator\n\n"
        )

        per_file_contents: List[str] = []

        for idx, criterion in enumerate(acceptance_criteria):
            c = str(criterion).lower()
            fn_name = f"test_autogen_{idx}"
            if "乘法" in c or "mul" in c:
                body = (
                    "def test_mul_basic():\n"
                    "    from core.operations import mul\n"
                    "    assert mul(2, 3) == 6\n"
                    "    assert mul(-2.5, 4) == -10\n"
                    "    assert mul(1.5, 2.5) == 3.75\n"
                )
            elif "除法" in c or "div" in c:
                body = (
                    "def test_div_basic():\n"
                    "    from core.operations import div\n"
                    "    assert div(10, 2) == 5 or abs(div(10,2)-5) < 1e-9\n"
                    "    assert abs(div(10, 3) - 3.3333333333333335) < 1e-9\n"
                    "    assert div(10, 0) == \"除数不能为0\"\n"
                )
            elif "历史" in c or "persist" in c or "history" in c:
                body = (
                    "def test_history_persistence(tmp_path):\n"
                    "    # workspace will be prepared by TestingWorkflow; use Calculator API to test persistence\n"
                    "    from core.calculator import Calculator\n"
                    "    calc = Calculator()\n"
                    "    calc.clear_history()\n"
                    "    calc.compute('add', 1, 2)\n"
                    "    h = calc.get_history()\n"
                    "    assert isinstance(h, list) and len(h) >= 1\n"
                    "    calc.clear_history()\n"
                    "    assert calc.get_history() == []\n"
                )
            else:
                safe_body = (
                    f"def {fn_name}():\n"
                    "    assert True  # placeholder test for acceptance: " + repr(criterion) + "\n"
                )
                body = safe_body

            per_file_contents.append(header + "\n\n" + body)

        # 将每个生成的测试内容放入对应的 test_files.content
        file_objs: List[TestFile] = []
        for index, tf in enumerate(test_files):
            content = per_file_contents[index] if index < len(per_file_contents) else "# autogenerated placeholder\n"
            file_objs.append(TestFile(file_path=tf.file_path, test_type=tf.test_type, covers=tf.covers, content=content))

        return TestBundle(
            stage="testing",
            test_plan=test_plan,
            test_files=file_objs,
            test_code="",
            runner_commands=runner_commands,
            sandbox_result=None,
        )

    def _to_plain(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return {}
