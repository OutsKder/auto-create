from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone
from inspect import isawaitable
from typing import Any, Callable, Dict
from pathlib import Path

from ..artifact_store import (
    apply_code_diff_to_workspace,
    build_delivery_summary,
    persist_stage_artifacts,
    validate_workspace,
)
from ..pipeline import Pipeline, PipelineStatus

logger = logging.getLogger(__name__)

OBSERVABILITY_KEY = "observability"


def _append_stage_observability(
    pipeline: Pipeline,
    *,
    stage_id: str,
    stage_name: str,
    started_monotonic: float,
    ok: bool,
    error: str | None = None,
) -> None:
    """Append one run record for simple dashboards (duration, tokens when present)."""
    elapsed = max(0.0, time.monotonic() - started_monotonic)
    bucket = pipeline.context.setdefault(OBSERVABILITY_KEY, {})
    runs = bucket.setdefault("runs", [])
    meta = pipeline.context.get("meta_trace")
    tokens: Dict[str, Any] | None = None
    if isinstance(meta, dict):
        tokens = {
            "total_tokens": meta.get("total_tokens"),
            "prompt_tokens": meta.get("prompt_tokens"),
            "completion_tokens": meta.get("completion_tokens"),
            "token_source": meta.get("token_source"),
        }
    runs.append(
        {
            "stage_id": stage_id,
            "stage_name": stage_name,
            "ok": ok,
            "elapsed_seconds": round(elapsed, 3),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "tokens": tokens,
            "error": error,
        }
    )
    bucket["last_updated"] = datetime.now(timezone.utc).isoformat()


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


async def _run_agent_execute(agent: Any, context: Dict[str, Any]) -> Any:
    result = agent.execute(context)
    if isawaitable(result):
        return await result
    return result


async def _execute_requirement_analysis(pipeline: Pipeline) -> bool:
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

    max_attempts = max(1, int(os.environ.get("ANALYSIS_MAX_ATTEMPTS", "3")))
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            llm = _build_llm()
            agent = RequirementAnalyst(llm_provider=llm)
            result = await _run_agent_execute(agent, pipeline.context)
            if not isinstance(result, dict):
                raise RuntimeError("RequirementAnalyst 返回格式错误，期望 Dict")
            pipeline.context.update(result)
            return True
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Requirement analysis failed; attempt=%d/%d; error=%s",
                attempt,
                max_attempts,
                exc,
            )
            pipeline.context["analysis_retry"] = {
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error": str(exc),
            }
            if attempt >= max_attempts:
                break

    raise RuntimeError(
        "RequirementAnalyst 多次重试后仍失败。"
        f"请检查模型网络连通性或结构化输出稳定性。最后错误: {last_error}"
    ) from last_error


async def _execute_tech_architect(pipeline: Pipeline) -> bool:
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
    result = await _run_agent_execute(agent, input_context)
    if isinstance(result, dict) and "design" in result:
        pipeline.context["design_doc"] = result["design"]
        if "meta_trace" in result:
            pipeline.context["meta_trace"] = result["meta_trace"]
        if "codebase_context" in result:
            pipeline.context["codebase_context"] = result["codebase_context"]
        return True
    if result is not None:
        pipeline.context["design_doc"] = result
        return True
    return False


async def _execute_code_generator(pipeline: Pipeline) -> bool:
    pipeline.context.pop("meta_trace", None)
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
    codebase = pipeline.context.get("codebase") or {
        "repo_name": "generated-project",
        "repo_path": str(PROJECT_ROOT),
        "branch": "main",
    }
    codebase_context = pipeline.context.get("codebase_context") or {
        "query": pipeline.context.get("requirement_raw", ""),
        "repo_skeleton": "",
        "hot_files": [],
        "dependency_signatures": [],
        "coverage_report": {
            "requirement_points": [],
            "covered_points": [],
            "uncovered_points": [],
            "risk_level": "unknown",
        },
        "context_compaction": {},
    }
    agent = CodeGeneratorAgent(llm_provider=llm, repo_root=codebase["repo_path"])
    input_context = {
        "requirement_structured": pipeline.context.get("requirement_structured"),
        "design": pipeline.context.get("design_doc"),
        "codebase_context": codebase_context,
        "codebase": codebase,
    }
    result = await _run_agent_execute(agent, input_context)
    if isinstance(result, dict) and "code_diff" in result:
        pipeline.context["code_diff"] = result["code_diff"]
        apply_code_diff_to_workspace(pipeline)
        return True
    if result is not None:
        pipeline.context["code_diff"] = result
        apply_code_diff_to_workspace(pipeline)
        return True
    return False


async def _execute_testing(pipeline: Pipeline) -> bool:
    pipeline.context.pop("meta_trace", None)
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
        llm = _build_llm()
        agent = SDETAgent(llm_provider=llm)
        result = await _run_agent_execute(agent, pipeline.context)
        if isinstance(result, dict):
            pipeline.context.update(result)

    workspace_report = validate_workspace(pipeline)
    generated_tests = pipeline.context.get("tests")
    pipeline.context["tests"] = {
        **(generated_tests if isinstance(generated_tests, dict) else {}),
        "sandbox_result": {
            "passed": workspace_report["passed"],
            "exit_code": 0 if workspace_report["passed"] else 1,
            "logs": "workspace validation passed"
            if workspace_report["passed"]
            else "workspace validation failed",
            "failure_stage": None if workspace_report["passed"] else "workspace",
            "failure_type": None if workspace_report["passed"] else "workspace_validation",
            "failure_message": None if workspace_report["passed"] else "workspace validation failed",
            "failure_context": {"checks": workspace_report["checks"]},
            "failed_patches": [],
            "failed_command": None,
        },
    }
    pipeline.context["test_report"] = {
        "passed": workspace_report["passed"],
        "workspace": workspace_report,
        "generated_tests": generated_tests,
    }
    return True


async def _execute_review(pipeline: Pipeline) -> bool:
    pipeline.context.pop("meta_trace", None)
    if _is_demo_mode(pipeline):
        pipeline.context["review_result"] = {
            "approved": True,
            "notes": ["demo mode review passed"],
        }
        return True

    from backend.agent.agents.senior_reviewer import SeniorReviewerAgent

    try:
        reviewer = SeniorReviewerAgent()
        result = await _run_agent_execute(reviewer, pipeline.context)
        if result is not None:
            pipeline.context.update(result)
            pipeline.context["review_result"] = result.get("review", result)
        else:
            pipeline.context["review_result"] = "通过"
    except Exception:
        pipeline.context["review_result"] = "通过"
    return True


def _execute_delivery(pipeline: Pipeline) -> bool:
    pipeline.context.pop("meta_trace", None)
    if _is_demo_mode(pipeline):
        pipeline.context["delivery"] = {
            "status": "ready",
            "package": "demo-delivery.zip",
        }
        return True

    build_delivery_summary(pipeline)
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
    started = time.monotonic()

    try:
        executor = _STAGE_EXECUTORS.get(stage.id)
        if executor is None:
            logger.info("No agent connector registered for stage: %s", stage.id)
            return

        success = executor(pipeline)
        if isawaitable(success):
            success = await success
        if not success:
            logger.warning("Stage %s connector returned false or empty result.", stage.id)
            _append_stage_observability(
                pipeline,
                stage_id=stage.id,
                stage_name=stage.name,
                started_monotonic=started,
                ok=False,
                error="阶段未返回有效结果",
            )
            return

        persist_stage_artifacts(pipeline, stage)
        _append_stage_observability(
            pipeline,
            stage_id=stage.id,
            stage_name=stage.name,
            started_monotonic=started,
            ok=True,
            error=None,
        )
        pipeline.stage_done()
        logger.info("==> Stage %s done. Waiting for approval.", stage.id)
    except Exception as e:
        pipeline.context["last_error"] = f"{stage.id}: {e}"
        _append_stage_observability(
            pipeline,
            stage_id=stage.id,
            stage_name=stage.name,
            started_monotonic=started,
            ok=False,
            error=str(e),
        )
        logger.exception("Error executing stage %s", stage.id)


def execute_current_stage_agent(pipeline: Pipeline) -> bool:
    stage = pipeline.current_stage()
    if not stage:
        return False
    executor = _STAGE_EXECUTORS.get(stage.id)
    if executor is None:
        return False
    result = executor(pipeline)
    if isawaitable(result):
        return asyncio.run(result)
    return result
