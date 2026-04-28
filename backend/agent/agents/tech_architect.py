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

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import os
import glob
import time
import re

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
        step2_start = time.perf_counter()
        codebase_context_obj = tool.extract_context(context=context, query=query)
        step2_elapsed = time.perf_counter() - step2_start
        print(
            f"[TechArchitect] Context Tool 完成，耗时 {step2_elapsed:.2f}s，hot_files={len(codebase_context_obj.get('hot_files', []))}"
        )

        # 覆盖率门禁：若 Step2 回补后仍有未覆盖需求点，则阻断进入代码生成阶段。
        coverage_report = codebase_context_obj.get("coverage_report", {})
        uncovered_points = coverage_report.get("uncovered_points", [])
        if uncovered_points:
            raise RuntimeError(
                "Step2 覆盖率门禁未通过，仍存在未覆盖需求点："
                + "；".join(uncovered_points[:5])
            )

        # 将对象转为字符串喂给大模型
        import json

        llm_context = self._compact_context_for_llm(
            codebase_context_obj, requirement_structured
        )
        codebase_context_str = json.dumps(llm_context, ensure_ascii=False, indent=2)

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

    def _compact_context_for_llm(
        self, codebase_context: Dict[str, Any], requirement_structured: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compress context payload before sending to LLM while preserving key signals.

        Notes:
        - Keep retrieval quality unchanged: this only affects LLM prompt payload size.
        - Use adaptive budget by requirement complexity.
        - Use logic snippets (not only file head) to reduce noise while keeping relevant blocks.
        """
        hot_files = codebase_context.get("hot_files", []) or []
        compact_hot_files: List[Dict[str, Any]] = []

        complexity = self._estimate_requirement_complexity(requirement_structured)
        total_chars_budget, skeleton_budget, sig_budget, max_files = (
            self._adaptive_budgets(complexity)
        )
        consumed = 0
        query_terms = self._extract_query_terms(requirement_structured)

        for idx, hf in enumerate(hot_files[:max_files]):
            path = hf.get("path", "")
            content = hf.get("content", "") or ""
            if not path or not content:
                continue

            if consumed >= total_chars_budget:
                break

            file_budget = min(
                self._file_char_budget_by_rank(idx, complexity),
                total_chars_budget - consumed,
            )
            snippet, snippet_meta = self._extract_logic_snippet(
                content=content,
                path=path,
                file_budget=file_budget,
                query_terms=query_terms,
                evidence=hf.get("evidence", []) or [],
            )
            consumed += len(snippet)

            compact_hot_files.append(
                {
                    "path": path,
                    "score": hf.get("score", 0.0),
                    "evidence": (hf.get("evidence", []) or [])[:6],
                    "content": snippet,
                    "content_truncated": len(content) > len(snippet),
                    "original_chars": len(content),
                    "snippet_meta": snippet_meta,
                }
            )

        dependency_signatures = (
            codebase_context.get("dependency_signatures", []) or []
        )[:sig_budget]

        compact = {
            "query": codebase_context.get("query", ""),
            "repo_skeleton": (codebase_context.get("repo_skeleton", "") or "")[
                :skeleton_budget
            ],
            "hot_files": compact_hot_files,
            "dependency_signatures": dependency_signatures,
            "coverage_report": codebase_context.get("coverage_report", {}),
            "context_compaction": {
                "complexity": complexity,
                "original_hot_files": len(hot_files),
                "sent_hot_files": len(compact_hot_files),
                "content_chars_budget": total_chars_budget,
                "content_chars_used": consumed,
                "mode": "adaptive_logic_snippet",
            },
        }

        print(
            "[TechArchitect] LLM上下文压缩: "
            f"hot_files {len(hot_files)}->{len(compact_hot_files)}, "
            f"chars={consumed}/{total_chars_budget}, complexity={complexity}"
        )
        return compact

    def _estimate_requirement_complexity(
        self, requirement_structured: Dict[str, Any]
    ) -> int:
        goal = str(requirement_structured.get("goal", "") or "")
        features = requirement_structured.get("features", []) or []
        constraints = requirement_structured.get("constraints", []) or []
        ac = requirement_structured.get("acceptance_criteria", []) or []

        text_len = len(goal) + sum(len(str(x)) for x in features + constraints + ac)
        score = 0
        score += min(4, len(features) // 3)
        score += min(3, len(constraints) // 3)
        score += min(3, len(ac) // 3)
        if text_len > 1200:
            score += 2
        elif text_len > 700:
            score += 1
        return max(1, min(10, score))

    def _adaptive_budgets(self, complexity: int) -> Tuple[int, int, int, int]:
        # Return: total_chars_budget, repo_skeleton_budget, signature_budget, max_hot_files
        if complexity <= 3:
            return 42000, 8000, 80, 10
        if complexity <= 6:
            return 62000, 12000, 120, 14
        if complexity <= 8:
            return 85000, 18000, 180, 18
        return 110000, 24000, 240, 24

    def _file_char_budget_by_rank(self, index: int, complexity: int) -> int:
        if complexity <= 3:
            if index < 3:
                return 5000
            if index < 8:
                return 2500
            return 1400

        if complexity <= 6:
            if index < 3:
                return 7000
            if index < 8:
                return 3500
            return 1800

        if index < 4:
            return 9000
        if index < 10:
            return 4200
        return 2200

    def _extract_query_terms(self, requirement_structured: Dict[str, Any]) -> List[str]:
        raw = [str(requirement_structured.get("goal", "") or "")]
        raw.extend(str(x) for x in (requirement_structured.get("features", []) or []))
        raw.extend(
            str(x) for x in (requirement_structured.get("constraints", []) or [])
        )
        raw.extend(
            str(x)
            for x in (requirement_structured.get("acceptance_criteria", []) or [])
        )
        text = "\n".join(raw).lower()
        tokens = [
            t.strip()
            for t in re.split(r"[^a-zA-Z0-9_\u4e00-\u9fff]+", text)
            if len(t.strip()) >= 2
        ]
        seen = set()
        out: List[str] = []
        for token in tokens:
            if token not in seen:
                out.append(token)
                seen.add(token)
            if len(out) >= 40:
                break
        return out

    def _extract_logic_snippet(
        self,
        content: str,
        path: str,
        file_budget: int,
        query_terms: List[str],
        evidence: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        if len(content) <= file_budget:
            return content, {"strategy": "full", "segments": 1}

        lines = content.splitlines()
        if not lines:
            return content[:file_budget], {"strategy": "head", "segments": 1}

        evidence_terms: List[str] = []
        for e in evidence:
            part = str(e).split(":", 1)
            if len(part) == 2 and part[1].strip():
                evidence_terms.append(part[1].strip().lower())

        terms = [t for t in query_terms + evidence_terms if t]
        terms = terms[:60]

        matched_idx: List[int] = []
        for i, line in enumerate(lines):
            l = line.lower()
            if any(term in l for term in terms):
                matched_idx.append(i)

        ext = os.path.splitext(path)[1].lower()
        window_before = 6 if ext in {".py", ".js", ".ts", ".jsx", ".tsx"} else 4
        window_after = 32 if ext in {".py", ".js", ".ts", ".jsx", ".tsx"} else 16

        segments: List[Tuple[int, int]] = []
        for idx in matched_idx[:30]:
            start = max(0, idx - window_before)
            end = min(len(lines), idx + window_after)
            segments.append((start, end))

        if not segments:
            # Fallback: keep head+tail to preserve entry/setup and terminal logic.
            head_len = max(300, int(file_budget * 0.7))
            tail_len = max(200, file_budget - head_len)
            head = content[:head_len]
            tail = content[-tail_len:] if tail_len < len(content) else ""
            merged = head + "\n\n# ... SNIP ...\n\n" + tail if tail else head
            return merged[:file_budget], {"strategy": "head_tail", "segments": 2}

        merged_segments: List[Tuple[int, int]] = []
        for start, end in sorted(segments):
            if not merged_segments or start > merged_segments[-1][1] + 2:
                merged_segments.append((start, end))
            else:
                last_s, last_e = merged_segments[-1]
                merged_segments[-1] = (last_s, max(last_e, end))

        out_parts: List[str] = []
        used = 0
        for idx, (start, end) in enumerate(merged_segments):
            block = "\n".join(lines[start:end]).strip()
            if not block:
                continue
            prefix = "\n\n# ... SNIP ...\n\n" if idx > 0 else ""
            candidate = prefix + block
            if used + len(candidate) > file_budget:
                remain = file_budget - used
                if remain > 200:
                    out_parts.append(candidate[:remain])
                    used += len(out_parts[-1])
                break
            out_parts.append(candidate)
            used += len(candidate)

        if not out_parts:
            fallback = content[:file_budget]
            return fallback, {"strategy": "head_fallback", "segments": 1}

        snippet = "".join(out_parts)
        return snippet, {
            "strategy": "logic_snippet",
            "segments": len(out_parts),
            "matched_lines": len(matched_idx),
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
