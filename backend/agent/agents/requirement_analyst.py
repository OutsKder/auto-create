"""
需求分析 Agent (Requirement Analyst)

角色定位：资深产品经理
输入：requirement_raw (用户原始描述)
输出：requirement_structured (结构化需求文档)

核心功能：
1. 理解用户需求的隐含逻辑
2. 将非结构化文本拆解为核心目标、功能点、约束和验收标准
3. 支持模糊需求的澄清追问机制
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from ..base import BaseAgent, AgentConfig
from ..callbacks import TraceCallbackHandler
from ..prompts.requirement_analyst import (
    REQUIREMENT_ANALYST_SYSTEM_PROMPT,
    REQUIREMENT_ANALYST_HUMAN_PROMPT,
)
from ..prompts.common import (
    JSON_RETRY_SYSTEM_PROMPT,
    JSON_RETRY_HUMAN_PROMPT,
)


class RequirementStructured(BaseModel):
    is_clear: bool = Field(
        description="原始需求是否传达了核心意图和基本业务场景。判定标准要对普通用户友好，只要能看出大概要做什么产品（例如包含了主要的业务对象或期待的结果），即使缺少详细规则，也应设为True并由你基于常识补全细节。仅当毫无逻辑、不知所云时才设为False"
    )
    clarifying_questions: List[str] = Field(
        description="如果 is_clear 为 False，提出1-3个需要用户补充确认的关键问题。如果为 True，此列表可为空"
    )
    goal: str = Field(description="核心目标")
    features: List[str] = Field(description="功能点列表")
    constraints: List[str] = Field(description="非功能约束(如性能、边界条件、UI约束等)")
    acceptance_criteria: List[str] = Field(description="验收标准")


class RequirementAnalyst(BaseAgent):
    """需求分析 Agent - 扮演资深产品经理"""

    def __init__(
        self,
        llm_provider: Any,
        config: Optional[AgentConfig] = None
    ):
        super().__init__(llm_provider, config)
        self.parser = PydanticOutputParser(pydantic_object=RequirementStructured)

    def get_input_keys(self) -> List[str]:
        return ["requirement_raw"]

    def get_output_key(self) -> str:
        return "requirement_structured"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        需求分析阶段：提取 requirement_raw 并结构化输出 requirement_structured

        处理流程：
        1. 输入校验与防爆机制
        2. 调用 LLM 生成结构化需求
        3. 解析失败时触发重试自愈
        4. 返回增量 context
        """
        requirement_raw = context.get("requirement_raw", "")
        if not requirement_raw or not requirement_raw.strip():
            raise ValueError("context 中缺少 requirement_raw")

        if len(requirement_raw.strip()) < 5:
            return self._handle_short_input()

        token_count = self._count_tokens(requirement_raw)
        MAX_TOKENS_LIMIT = 10000
        if token_count > MAX_TOKENS_LIMIT:
            raise ValueError(
                f"需求文档过长 (预估 {token_count} Tokens)，"
                f"请将需求精简至 {MAX_TOKENS_LIMIT} Tokens 以内，或拆分单次任务进行。"
            )

        tracer = TraceCallbackHandler()

        try:
            response = self._invoke_llm(requirement_raw, tracer)
            result = self._parse_response(response, tracer)
        except Exception as e:
            raise RuntimeError(f"RequirementAnalyst 执行过程中发生致命错误: {str(e)}")

        return {
            "requirement_structured": result.dict(),
            "meta_trace": tracer.meta_info,
        }

    def _handle_short_input(self) -> Dict[str, Any]:
        """处理极端短输入"""
        print("[RequirementAnalyst] 输入过短，判定为极端无效输入拦截。")
        return {
            "requirement_structured": {
                "is_clear": False,
                "clarifying_questions": ["您的输入过短或无具体意义，请详细描述您的核心业务需求。"],
                "goal": "",
                "features": [],
                "constraints": [],
                "acceptance_criteria": [],
            }
        }

    def _count_tokens(self, text: str) -> int:
        """计算 Token 数量"""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            return len(text)

    def _invoke_llm(
        self,
        requirement_raw: str,
        tracer: TraceCallbackHandler
    ) -> Any:
        """调用 LLM 获取响应"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REQUIREMENT_ANALYST_SYSTEM_PROMPT),
                ("human", REQUIREMENT_ANALYST_HUMAN_PROMPT),
            ]
        )

        _input = prompt.format_prompt(
            requirement_raw=requirement_raw,
            format_instructions=self.parser.get_format_instructions(),
        )

        response = self.llm.invoke(_input, config={"callbacks": [tracer]})
        tracer.print_trace_report()
        return response

    def _parse_response(
        self,
        response: Any,
        tracer: TraceCallbackHandler
    ) -> RequirementStructured:
        """解析 LLM 响应，失败时触发重试"""
        try:
            return self.parser.parse(response.content)
        except Exception as parse_e:
            print(f"[RequirementAnalyst] 解析失败，触发 Retry 容错自愈... ({parse_e})")
            return self._retry_with_fix(response.content, parse_e, tracer)

    def _retry_with_fix(
        self,
        wrong_output: str,
        error_msg: str,
        tracer: TraceCallbackHandler
    ) -> RequirementStructured:
        """重试并修复 JSON 解析错误"""
        retry_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", JSON_RETRY_SYSTEM_PROMPT),
                ("human", JSON_RETRY_HUMAN_PROMPT),
            ]
        )
        retry_input = retry_prompt.format_prompt(
            format_instructions=self.parser.get_format_instructions(),
            wrong_output=wrong_output,
            error_msg=str(error_msg),
        )

        retry_tracer = TraceCallbackHandler()
        retry_response = self.llm.invoke(retry_input, config={"callbacks": [retry_tracer]})
        retry_tracer.print_trace_report()
        tracer.meta_info.update({"retry_meta": retry_tracer.meta_info})

        return self.parser.parse(retry_response.content)
