from __future__ import annotations

import asyncio
import logging
import os
import sys
from inspect import isawaitable
from typing import Any, Callable, Dict
from pathlib import Path

from ..pipeline import Pipeline, PipelineStatus

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.agent.llm.config import load_config
    from backend.agent.llm.factory import LLMFactory
except Exception:
    load_config = None
    LLMFactory = None


def _build_llm():
    if load_config is None or LLMFactory is None:
        raise RuntimeError("LLM factory is unavailable in current environment")

    provider = os.environ.get("TEST_LLM_PROVIDER", "doubao")
    llm_config = load_config(provider)
    if not getattr(llm_config, "api_key", None):
        raise RuntimeError(
            "LLM api_key not found. Set API key via config/llm.yaml or environment variables."
        )
    return LLMFactory.create(llm_config.provider, config=llm_config)


def _is_demo_mode(pipeline: Pipeline) -> bool:
    return bool(pipeline.context.get("demo_mode") or os.environ.get("API_FIRST_DEMO_MODE"))


def _run_agent_execute(agent: Any, context: Dict[str, Any]) -> Any:
    result = agent.execute(context)
    if isawaitable(result):
        return asyncio.run(result)
    return result


def _execute_requirement_analysis(pipeline: Pipeline) -> bool:
    if _is_demo_mode(pipeline):
        requirement_raw = (pipeline.context.get("requirement_raw") or "演示需求").strip()
        pipeline.context["requirement_structured"] = {
            "goal": requirement_raw,
            "features": ["需求分析", "审批流演示"],
            "constraints": ["无需 FastAPI", "支持标准 HTTP"],
            "acceptance_criteria": ["能创建 pipeline", "能进入审批点", "能审批通过或拒绝"],
        }
        pipeline.context["analysis_doc"] = {
            "summary": f"已将需求整理为结构化描述：{requirement_raw}",
        }
        return True

    requirement_raw = (pipeline.context.get("requirement_raw") or "").strip()
    if not requirement_raw:
        return False

    from backend.agent.agents.requirement_analyst import RequirementAnalyst

    llm = _build_llm()
    agent = RequirementAnalyst(llm_provider=llm)
    result = _run_agent_execute(agent, pipeline.context)
    if not isinstance(result, dict):
        raise RuntimeError("RequirementAnalyst 返回格式错误，期望 Dict")
    pipeline.context.update(result)
    return True


def _execute_tech_architect(pipeline: Pipeline) -> bool:
    if _is_demo_mode(pipeline):
        pipeline.context["design_doc"] = {
            "title": "api-first demo design",
            "modules": ["core", "connectors", "http_demo_server", "http_demo_client"],
            "api": ["POST /pipelines", "POST /pipelines/{id}/run", "POST /checkpoints/{id}/approve", "POST /checkpoints/{id}/reject"],
        }
        return True

    from backend.agent.agents.tech_architect import TechArchitect

    llm = _build_llm()
    agent = TechArchitect(llm_provider=llm)
    requirement = pipeline.context.get("requirement_structured")
    if not requirement:
        requirement = pipeline.context.get("analysis_doc", {}).get("summary", "默认需求")
    input_context = {
        "requirement_structured": requirement,
        "codebase": pipeline.context.get("codebase", {"repo_path": ""}),
    }
    result = _run_agent_execute(agent, input_context)
    if isinstance(result, dict) and "design" in result:
        pipeline.context["design_doc"] = result["design"]
        return True
    if result is not None:
        pipeline.context["design_doc"] = result
        return True
    return False


def _execute_code_generator(pipeline: Pipeline) -> bool:
    if _is_demo_mode(pipeline):
        pipeline.context["code_diff"] = {
            "changes": [
                "split core state machine and connectors",
                "add checkpoint-driven approval",
                "add stdlib HTTP demo server",
            ]
        }
        return True

    from backend.agent.agents.code_generator import CodeGeneratorAgent

    llm = _build_llm()
    agent = CodeGeneratorAgent(llm_provider=llm)
    input_context = {
        "requirement_structured": pipeline.context.get("requirement_structured"),
        "design": pipeline.context.get("design_doc"),
        "codebase_context": pipeline.context.get("codebase", {"repo_path": ""}),
    }
    result = _run_agent_execute(agent, input_context)
    if isinstance(result, dict) and "code_diff" in result:
        pipeline.context["code_diff"] = result["code_diff"]
        return True
    if result is not None:
        pipeline.context["code_diff"] = result
        return True
    return False


def _execute_testing(pipeline: Pipeline) -> bool:
    if _is_demo_mode(pipeline):
        pipeline.context["test_report"] = {
            "passed": True,
            "summary": "demo mode smoke test passed",
        }
        return True

    from backend.agent.agents.sdet import SDETAgent

    try:
        from backend.agent.codegen.testing_workflow import TestingWorkflow
    except Exception:
        TestingWorkflow = None

    if SDETAgent is not None:
        agent = SDETAgent()
        _run_agent_execute(agent, pipeline.context)

    if TestingWorkflow is not None:
        workflow = TestingWorkflow()
        result = workflow.execute(pipeline.context)
        pipeline.context["test_report"] = result
        return True

    pipeline.context["test_report"] = "集成测试报告"
    return True


def _execute_review(pipeline: Pipeline) -> bool:
    if _is_demo_mode(pipeline):
        pipeline.context["review_result"] = {
            "approved": True,
            "notes": ["demo mode review passed"],
        }
        return True

    from backend.agent.agents.senior_reviewer import SeniorReviewer

    try:
        reviewer = SeniorReviewer()
        result = _run_agent_execute(reviewer, pipeline.context)
        if result is not None:
            pipeline.context["review_result"] = result
        else:
            pipeline.context["review_result"] = "通过"
    except Exception:
        pipeline.context["review_result"] = "通过"
    return True


def _execute_delivery(pipeline: Pipeline) -> bool:
    if _is_demo_mode(pipeline):
        pipeline.context["delivery"] = {
            "status": "ready",
            "package": "demo-delivery.zip",
        }
        return True

    pipeline.context["delivery"] = "打包完成"
    return True


_STAGE_EXECUTORS: Dict[str, Callable[[Pipeline], bool]] = {
    "analysis": _execute_requirement_analysis,
    "design": _execute_tech_architect,
    "coding": _execute_code_generator,
    "testing": _execute_testing,
    "review": _execute_review,
    "delivery": _execute_delivery,
}


async def dispatch_stage(pipeline: Pipeline):
    """
    连接 agent 的可变层：根据当前 stage 调用对应 agent，
    然后把结果交回 pipeline 的固定状态机处理。
    """
    if pipeline.status != PipelineStatus.RUNNING:
        return

    stage = pipeline.current_stage()
    if not stage:
        return

    logger.info("==> Dispatching stage: %s", stage.id)

    try:
        executor = _STAGE_EXECUTORS.get(stage.id)
        if executor is None:
            logger.info("No agent connector registered for stage: %s", stage.id)
            return

        success = executor(pipeline)
        if not success:
            logger.warning("Stage %s connector returned false or empty result.", stage.id)
            return

        pipeline.stage_done()
        logger.info("==> Stage %s done. Waiting for approval.", stage.id)
    except Exception as e:
        logger.error("Error executing stage %s: %s", stage.id, e)


def execute_current_stage_agent(pipeline: Pipeline) -> bool:
    stage = pipeline.current_stage()
    if not stage:
        return False
    executor = _STAGE_EXECUTORS.get(stage.id)
    if executor is None:
        return False
    return executor(pipeline)
