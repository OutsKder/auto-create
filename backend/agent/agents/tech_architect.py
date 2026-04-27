"""
方案设计 Agent (Tech Architect)

角色定位：高级架构师
输入：requirement_structured (结构化需求)
输出：design (技术方案设计)

核心功能：
1. 分析结构化需求，理解核心业务逻辑
2. 基于现有代码库，设计技术方案
3. 明确文件变更计划
4. 评估技术风险
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import os
import glob

from ..base import BaseAgent, AgentConfig
from ..callbacks import TraceCallbackHandler
from ..tools.codebase_context import CodebaseContextTool
from ..prompts.tech_architect import (
    TECH_ARCHITECT_SYSTEM_PROMPT,
    TECH_ARCHITECT_HUMAN_PROMPT,
)
from ..prompts.common import (
    JSON_RETRY_SYSTEM_PROMPT,
    JSON_RETRY_HUMAN_PROMPT,
)


class FileChangePlan(BaseModel):
    file_path: str = Field(description="文件路径")
    change_type: str = Field(description="变更类型: Create, Modify, Delete")
    description: str = Field(description="变更描述")


class Design(BaseModel):
    architecture: str = Field(description="架构设计描述")
    api_design: str = Field(description="API 设计描述")
    file_change_plan: List[FileChangePlan] = Field(description="文件变更计划")
    risk_analysis: str = Field(description="风险分析")


class TechArchitect(BaseAgent):
    """方案设计 Agent - 扮演高级架构师"""

    def __init__(self, llm_provider: Any, config: Optional[AgentConfig] = None):
        super().__init__(llm_provider, config)
        self.parser = PydanticOutputParser(pydantic_object=Design)

    def get_input_keys(self) -> List[str]:
        return ["requirement_structured"]

    def get_output_key(self) -> str:
        return "design"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        方案设计阶段：基于结构化需求和代码库分析，输出技术方案

        处理流程：
        1. 输入校验
        2. 分析代码库
        3. 调用 LLM 生成技术方案
        4. 解析失败时触发重试自愈
        5. 返回增量 context
        """
        requirement_structured = context.get("requirement_structured")
        if not requirement_structured:
            raise ValueError("context 中缺少 requirement_structured")

        # 从 context 中获取代码库上下文
        # 如果没有提供，使用默认路径
        codebase_dict = context.get("codebase", {})
        codebase_path = codebase_dict.get("repo_path")
        if not codebase_path:
            # 如果没有提供代码库路径，使用默认路径
            codebase_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ),
                "testcode",
            )

        # 挂载新版工具
        print(
            f"[TechArchitect] 调用 Context Tool 获取代码库上下文 (地址: {codebase_path})"
        )
        tool = CodebaseContextTool(workspace_root=codebase_path)

        # 提取上下文
        query = requirement_structured.get("goal", "")
        codebase_context_obj = tool.extract_context(query=query)

        # 将对象转为字符串喂给大模型
        import json

        codebase_context_str = json.dumps(
            codebase_context_obj, ensure_ascii=False, indent=2
        )

        tracer = TraceCallbackHandler()

        try:
            response = self._invoke_llm(
                requirement_structured, codebase_context_str, tracer
            )
            result = self._parse_response(response, tracer)
        except Exception as e:
            raise RuntimeError(f"TechArchitect 执行过程中发生致命错误: {str(e)}")

        return {
            "codebase_context": codebase_context_obj,  # 将上下文放入 Pipeline Context 返回
            "design": result.dict(),
            "meta_trace": tracer.meta_info,
        }

    def _invoke_llm(
        self,
        requirement_structured: Dict[str, Any],
        codebase_context: str,
        tracer: TraceCallbackHandler,
    ) -> Any:
        """调用 LLM 获取响应"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", TECH_ARCHITECT_SYSTEM_PROMPT),
                ("human", TECH_ARCHITECT_HUMAN_PROMPT),
            ]
        )

        _input = prompt.format_prompt(
            requirement_structured=requirement_structured,
            codebase_context=codebase_context,
            format_instructions=self.parser.get_format_instructions(),
        )

        response = self.llm.invoke(_input, config={"callbacks": [tracer]})
        tracer.print_trace_report()
        return response

    def _parse_response(self, response: Any, tracer: TraceCallbackHandler) -> Design:
        """解析 LLM 响应，失败时触发重试"""
        try:
            return self.parser.parse(response.content)
        except Exception as parse_e:
            print(f"[TechArchitect] 解析失败，触发 Retry 容错自愈... ({parse_e})")
            return self._retry_with_fix(response.content, parse_e, tracer)

    def _retry_with_fix(
        self, wrong_output: str, error_msg: str, tracer: TraceCallbackHandler
    ) -> Design:
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
        retry_response = self.llm.invoke(
            retry_input, config={"callbacks": [retry_tracer]}
        )
        retry_tracer.print_trace_report()
        tracer.meta_info.update({"retry_meta": retry_tracer.meta_info})

        return self.parser.parse(retry_response.content)
