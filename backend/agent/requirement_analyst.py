from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from .base import BaseAgent
from .callbacks import TraceCallbackHandler
from .prompt.requirement_analyst_prompt import (
    REQUIREMENT_ANALYST_SYSTEM_PROMPT,
    REQUIREMENT_ANALYST_HUMAN_PROMPT,
)
from .prompt.common_prompt import JSON_RETRY_SYSTEM_PROMPT, JSON_RETRY_HUMAN_PROMPT


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
    def __init__(self, llm_provider: Any, config: Dict[str, Any] = None):
        super().__init__(llm_provider, config)
        self.parser = PydanticOutputParser(pydantic_object=RequirementStructured)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        需求分析阶段: 提取 requirement_raw 并结构化输出 requirement_structured
        """
        requirement_raw = context.get("requirement_raw", "")
        if not requirement_raw or not requirement_raw.strip():
            raise ValueError("context 中缺少 requirement_raw")

        # 1. 稳健性：对抗极端输入 (无意义短字符拦截)
        if len(requirement_raw.strip()) < 5:
            print("[RequirementAnalyst] 输入过短，判定为极端无效输入拦截。")
            return {
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

        # 2. 稳健性：输入长度与 Token 截断防爆机制 (防 OOM 和天价账单)
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            token_count = len(encoding.encode(requirement_raw))
        except ImportError:
            # 兼容未安装 tiktoken 的情况，按粗略字符数估算
            token_count = len(requirement_raw)

        MAX_TOKENS_LIMIT = 10000
        if token_count > MAX_TOKENS_LIMIT:
            print(
                f"[RequirementAnalyst] 触发防爆机制：Token数量 {token_count} 超过限制 {MAX_TOKENS_LIMIT}"
            )
            raise ValueError(
                f"需求文档过长 (预估 {token_count} Tokens)，请将需求精简至 {MAX_TOKENS_LIMIT} Tokens 以内，或拆分单次任务进行。"
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REQUIREMENT_ANALYST_SYSTEM_PROMPT),
                ("human", REQUIREMENT_ANALYST_HUMAN_PROMPT),
            ]
        )

        try:
            _input = prompt.format_prompt(
                requirement_raw=requirement_raw,
                format_instructions=self.parser.get_format_instructions(),
            )

            # 注册自定义回调，记录 trace(Tokens、时间、Prompt、响应) 等全景元数据
            tracer = TraceCallbackHandler()

            # 发起调用并流式打印
            response = self.llm.invoke(_input, config={"callbacks": [tracer]})

            # 记录 trace 信息并汇总供调用方回溯
            tracer.print_trace_report()

            try:
                result: RequirementStructured = self.parser.parse(response.content)
            except Exception as parse_e:
                print(
                    f"[RequirementAnalyst] 解析失败，触发 Retry 容错自愈... ({parse_e})"
                )

                # 自主实现重试机制，免除第三方库版本依赖
                retry_prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", JSON_RETRY_SYSTEM_PROMPT),
                        ("human", JSON_RETRY_HUMAN_PROMPT),
                    ]
                )
                retry_input = retry_prompt.format_prompt(
                    format_instructions=self.parser.get_format_instructions(),
                    wrong_output=response.content,
                    error_msg=str(parse_e),
                )

                # 重试同样支持链路追踪与流式输出
                retry_tracer = TraceCallbackHandler()
                retry_response = self.llm.invoke(
                    retry_input, config={"callbacks": [retry_tracer]}
                )
                retry_tracer.print_trace_report()

                result: RequirementStructured = self.parser.parse(
                    retry_response.content
                )

        except Exception as e:
            raise RuntimeError(f"RequirementAnalyst 执行过程中发生致命错误: {str(e)}")

        return {
            "requirement_structured": result.dict(),
            "meta_trace": tracer.meta_info,  # 将 trace 信息作为额外产物返回给流水线
        }
