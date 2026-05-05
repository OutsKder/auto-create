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
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from ..base import BaseAgent, AgentConfig
from ..callbacks import TraceCallbackHandler
from ..contracts import RequirementAnalystInput, RequirementStructured
from ..prompts.requirement_analyst import (
    REQUIREMENT_ANALYST_SYSTEM_PROMPT,
    REQUIREMENT_ANALYST_HUMAN_PROMPT,
)
from ..prompts.common import (
    JSON_RETRY_SYSTEM_PROMPT,
    JSON_RETRY_HUMAN_PROMPT,
)


class RequirementAnalyst(BaseAgent):
    """需求分析 Agent - 扮演资深产品经理"""

    input_model = RequirementAnalystInput
    output_key = "requirement_structured"
    output_model = RequirementStructured

    def __init__(self, llm_provider: Any, config: Optional[AgentConfig] = None):
        super().__init__(llm_provider, config)
        self.parser = PydanticOutputParser(pydantic_object=RequirementStructured)
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

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
        self._validate_input(context)
        requirement_raw = context.get("requirement_raw", "")
        self.logger.info(
            "RequirementAnalyst.execute started; requirement_chars=%d",
            len(requirement_raw or ""),
        )
        if not requirement_raw or not requirement_raw.strip():
            self.logger.error("Missing requirement_raw in context")
            raise ValueError("context 中缺少 requirement_raw")

        if len(requirement_raw.strip()) < 5:
            self.logger.warning("Input too short, handling as short input")
            result = self._handle_short_input()
            self._validate_output(result)
            self.logger.info("RequirementAnalyst.execute completed with clarification")
            return result

        token_count = self._count_tokens(requirement_raw)
        MAX_TOKENS_LIMIT = 10000
        if token_count > MAX_TOKENS_LIMIT:
            self.logger.error("Input too long: %d tokens", token_count)
            raise ValueError(
                f"需求文档过长 (预估 {token_count} Tokens)，"
                f"请将需求精简至 {MAX_TOKENS_LIMIT} Tokens 以内，或拆分单次任务进行。"
            )

        tracer = TraceCallbackHandler()
        self.logger.debug("Token count estimate: %s", token_count)

        try:
            self.logger.info("Invoking LLM for requirement analysis")
            response = self._invoke_llm(requirement_raw, tracer)
            self.logger.debug(
                "LLM response received; response_type=%s", type(response).__name__
            )
            result = self._parse_response(response, tracer)
        except Exception as e:
            self.logger.exception("Fatal error during RequirementAnalyst execution")
            raise RuntimeError(f"RequirementAnalyst 执行过程中发生致命错误: {str(e)}")

        self.logger.info("Requirement analysis completed successfully")
        output = {
            "requirement_structured": result.model_dump(),
            "meta_trace": tracer.meta_info,
        }
        self._validate_output(output)
        return output

    def _handle_short_input(self) -> Dict[str, Any]:
        """处理极端短输入"""
        self.logger.warning(
            "Input considered too short - returning clarifying question"
        )
        output = {
            "requirement_structured": {
                "is_clear": False,
                "clarifying_questions": [
                    "您的输入过短或无具体意义，请详细描述您的核心业务需求。"
                ],
                "goal": "",
                "features": [],
                "constraints": [],
                "acceptance_criteria": [],
            }
        }
        self._validate_output(output)
        return output

    def _count_tokens(self, text: str) -> int:
        """计算 Token 数量"""
        try:
            # 尝试使用 tiktoken 进行精确的 token 计算
            import tiktoken

            # 使用 cl100k_base 编码器，这是 LLM 通常使用的编码器
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # 如果 tiktoken 未安装，则退化为按字符长度估算
            return len(text)

    def _invoke_llm(self, requirement_raw: str, tracer: TraceCallbackHandler) -> Any:
        """调用 LLM 获取响应"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REQUIREMENT_ANALYST_SYSTEM_PROMPT),
                ("human", REQUIREMENT_ANALYST_HUMAN_PROMPT),
            ]
        )

        # 构建 LLM 输入，注入原始需求和输出格式要求
        _input = prompt.format_prompt(
            # 注入原始需求
            requirement_raw=requirement_raw,
            # 注入输出格式要求
            format_instructions=self.parser.get_format_instructions(),
        )

        self.logger.debug(
            "Submitting prompt to LLM; prompt length=%d", len(str(_input))
        )
        response = self.llm.invoke(
            _input, config={"callbacks": [tracer]}
        )  # 调用 LLM 并记录 trace
        self.logger.info("LLM invocation complete for requirement analysis")
        try:
            tracer.print_trace_report()
        except Exception:
            self.logger.debug("Trace printing failed, continuing")
        return response

    # 解析 LLM 响应，失败时触发重试
    # 解析失败时触发重试自愈
    # 解析成功后返回结构化需求
    # 解析失败后返回重试结果
    def _parse_response(
        self, response: Any, tracer: TraceCallbackHandler
    ) -> RequirementStructured:
        """解析 LLM 响应，失败时触发重试"""
        try:
            self.logger.debug("Parsing LLM response into RequirementStructured")
            parsed = self.parser.parse(response.content)
            self.logger.info("Parsing successful")
            return parsed
        except Exception as parse_e:
            self.logger.warning("Parse failed, attempting retry fix: %s", parse_e)
            return self._retry_with_fix(response.content, parse_e, tracer)

    def _retry_with_fix(
        self, wrong_output: str, error_msg: str, tracer: TraceCallbackHandler
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
        self.logger.info("Invoking LLM for retry/fix of malformed JSON")
        retry_response = self.llm.invoke(
            retry_input, config={"callbacks": [retry_tracer]}
        )
        try:
            retry_tracer.print_trace_report()
        except Exception:
            self.logger.debug("Retry trace print failed")
        tracer.meta_info.update({"retry_meta": retry_tracer.meta_info})

        parsed = self.parser.parse(retry_response.content)
        self.logger.info("Retry parsing succeeded")
        return parsed
