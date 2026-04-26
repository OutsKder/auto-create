from typing import Any, Dict

from .events import EventType
from .pipeline import Pipeline, PipelineStatus
from .checkpoint import Checkpoint

try:
    from agent.agents.requirement_analyst import RequirementAnalyst
except ImportError:
    from backend.agent.agents.requirement_analyst import RequirementAnalyst

try:
    # 复用已有的 ChatOpenAI 实例，保持与 test_requirement_analyst.py 一致的调用契约
    from backend.doubao_llm import llm as default_llm
except ImportError:
    from doubao_llm import llm as default_llm

# 初始化需求分析 Agent
requirement_agent = RequirementAnalyst(llm_provider=default_llm)

_AUTO_AGENT_STAGE_IDS = {"analysis"}

_PIPELINES: Dict[str, Pipeline] = {}


def create_pipeline(context: Dict[str, Any] = None) -> Pipeline:
    pipeline = Pipeline.create_default()
    if context:
        pipeline.context.update(context)
    _PIPELINES[pipeline.id] = pipeline
    return pipeline


def get_pipeline(pipeline_id: str) -> Pipeline:
    return _PIPELINES[pipeline_id]


def list_pipelines() -> list[Pipeline]:
    return list(_PIPELINES.values())


def get_checkpoint(checkpoint_id: str) -> Checkpoint:
    for pipeline in _PIPELINES.values():
        for checkpoint in pipeline.checkpoints:
            if checkpoint.id == checkpoint_id:
                return checkpoint
    raise KeyError(checkpoint_id)


def run_pipeline(pipeline_id: str) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)
    pipeline.start()
    # 自动执行已接入 agent 的阶段，直到遇到人工阶段
    _run_auto_agent_stages(pipeline)
    return pipeline


def run_agent_stages(pipeline_id: str) -> Pipeline:
    """仅执行当前及后续已接入 agent 的阶段，遇到未接入阶段即停。"""
    pipeline = get_pipeline(pipeline_id)

    if pipeline.status == PipelineStatus.FINISHED:
        return pipeline

    if pipeline.status == PipelineStatus.CREATED:
        pipeline.start()
    elif pipeline.status == PipelineStatus.WAITING_APPROVAL:
        checkpoint = pipeline.current_checkpoint()
        if checkpoint is None:
            raise ValueError("no active checkpoint")
        pipeline.approve(checkpoint.id)

    _run_auto_agent_stages(pipeline)
    return pipeline


def _run_auto_agent_stages(pipeline: Pipeline) -> None:
    """循环执行已接入 agent 的阶段，直到遇到未接入阶段或流程结束。"""
    safety_limit = max(len(pipeline.stages) * 2, 1)
    steps = 0

    while pipeline.status == PipelineStatus.RUNNING:
        stage = pipeline.current_stage()
        if stage is None:
            pipeline.status = PipelineStatus.FINISHED
            return
        if stage.id not in _AUTO_AGENT_STAGE_IDS:
            return

        steps += 1
        if steps > safety_limit:
            raise RuntimeError("auto agent stage execution exceeded safety limit")

        progressed = _execute_current_stage_agent(pipeline)
        if not progressed:
            return


def _execute_current_stage_agent(pipeline: Pipeline) -> bool:
    """执行当前阶段对应的Agent，将结果存入上下文"""
    current_stage = pipeline.current_stage()
    if not current_stage:
        return False

    if current_stage.id == "analysis":
        requirement_raw = (pipeline.context.get("requirement_raw") or "").strip()
        # 兼容旧调用方：缺失原始需求时不触发分析 Agent，保留在 analysis 阶段等待外部补充
        if not requirement_raw:
            return False

        # 需求分析阶段，调用需求分析 Agent
        result = requirement_agent.execute(pipeline.context)

        if not isinstance(result, dict):
            raise RuntimeError("RequirementAnalyst 返回格式错误，期望 Dict")

        # 将增量结果 merge 回全局上下文（包含 requirement_structured/meta_trace）
        pipeline.context.update(result)
        return True

    return False


def stage_done(pipeline_id: str) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)
    pipeline.stage_done()
    return pipeline


def need_approval(pipeline_id: str) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)
    pipeline.need_approval()
    return pipeline


def approve(pipeline_id: str, checkpoint_id: str | None = None) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)
    pipeline.approve(checkpoint_id=checkpoint_id)
    return pipeline


def reject(pipeline_id: str, checkpoint_id: str | None = None) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)
    pipeline.reject(checkpoint_id=checkpoint_id)
    return pipeline


def auto_advance_pipeline(pipeline_id: str) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)

    if pipeline.status == PipelineStatus.CREATED:
        pipeline.start()

    safety_limit = max(len(pipeline.stages) * 3, 1)
    steps = 0

    while pipeline.status != PipelineStatus.FINISHED:
        steps += 1
        if steps > safety_limit:
            raise RuntimeError("auto advance exceeded safety limit")

        if pipeline.status == PipelineStatus.RUNNING:
            _run_auto_agent_stages(pipeline)
            if pipeline.status != PipelineStatus.RUNNING:
                continue
            pipeline.stage_done()
            continue

        if pipeline.status == PipelineStatus.WAITING_APPROVAL:
            checkpoint = pipeline.current_checkpoint()
            if checkpoint is None:
                raise ValueError("no active checkpoint")
            pipeline.approve(checkpoint.id)
            continue

        break

    return pipeline


def advance_one_stage(pipeline_id: str) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)

    if pipeline.status == PipelineStatus.FINISHED:
        return pipeline

    original_index = pipeline.current_stage_index

    # 处理初始状态和待审核状态，先进入运行状态
    if pipeline.status == PipelineStatus.CREATED:
        pipeline.start()
    elif pipeline.status == PipelineStatus.WAITING_APPROVAL:
        checkpoint = pipeline.current_checkpoint()
        if checkpoint is None:
            raise ValueError("no active checkpoint")
        pipeline.approve(checkpoint.id)

    # ========= 绝对保证：每次只处理当前一个阶段，不管有没有Agent =========
    current_stage = pipeline.current_stage()
    if not current_stage:
        pipeline.status = PipelineStatus.FINISHED
        return pipeline

    # 1. 处理当前阶段逻辑：有Agent就执行，没有就直接跳过
    if current_stage.id in _AUTO_AGENT_STAGE_IDS:
        _execute_current_stage_agent(pipeline)
    
    # 2. 统一完成当前阶段的收尾流程（不管有没有Agent都走）
    current_stage.mark_done()
    # 生成审核节点并自动通过
    pipeline.checkpoint_for_current_stage()
    checkpoint = pipeline.current_checkpoint()
    pipeline.approve(checkpoint.id)
    
    # 3. 强制只推进一次，绝对不会加两次
    pipeline.current_stage_index = original_index + 1
    next_stage = pipeline.current_stage()
    if next_stage:
        next_stage.start()
        pipeline.status = PipelineStatus.RUNNING
    else:
        pipeline.status = PipelineStatus.FINISHED

    return pipeline


def emit_event(event_type: EventType, pipeline_id: str, checkpoint_id: str | None = None) -> Pipeline:
    if event_type == EventType.CREATE_PIPELINE:
        return create_pipeline()
    if event_type == EventType.RUN_PIPELINE:
        return run_pipeline(pipeline_id)
    if event_type == EventType.STAGE_DONE:
        return stage_done(pipeline_id)
    if event_type == EventType.NEED_APPROVAL:
        return need_approval(pipeline_id)
    if event_type == EventType.APPROVE:
        return approve(pipeline_id, checkpoint_id=checkpoint_id)
    if event_type == EventType.REJECT:
        return reject(pipeline_id, checkpoint_id=checkpoint_id)
    raise ValueError(f"unsupported event: {event_type}")
