from typing import Any, Dict

from .connectors.agent_connectors import execute_current_stage_agent
from .events import EventType
from .pipeline import Pipeline, PipelineStatus
from .checkpoint import Checkpoint

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


import asyncio

def run_pipeline(pipeline_id: str) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)
    if pipeline.status == PipelineStatus.CREATED:
        pipeline.start()
    
    # 兼容老测试：同步运行 dispatcher
    from .dispatcher import dispatch_stage
    asyncio.run(dispatch_stage(pipeline))
    return pipeline

def run_agent_stages(pipeline_id: str) -> Pipeline:
    """仅执行当前及后续已接入 agent 的阶段，遇到未接入阶段即停。"""
    pipeline = get_pipeline(pipeline_id)

    if pipeline.status == PipelineStatus.FINISHED:
        return pipeline

    if pipeline.status == PipelineStatus.CREATED:
        pipeline.start()
    elif pipeline.status == PipelineStatus.WAITING_APPROVAL:
        # 禁止自动 approve，等待用户通过API调用审批
        return pipeline

    from .dispatcher import dispatch_stage
    asyncio.run(dispatch_stage(pipeline))
    return pipeline


import time


def _run_auto_agent_stages(pipeline: Pipeline) -> None:
    """
    此方法已被废弃，将在异步重构后移除。
    新的调度统一收口在 api_first/dispatcher.py 中。
    """
    pass


def _execute_current_stage_agent(pipeline: Pipeline) -> bool:
    """执行当前阶段对应的Agent，将结果存入上下文。"""
    return execute_current_stage_agent(pipeline)


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


def reject(
    pipeline_id: str, checkpoint_id: str | None = None, note: str = ""
) -> Pipeline:
    pipeline = get_pipeline(pipeline_id)
    pipeline.reject(checkpoint_id=checkpoint_id, note=note)
    return pipeline


def auto_advance_pipeline(pipeline_id: str) -> Pipeline:
    # 已废弃，建议使用审批驱动流程
    pipeline = get_pipeline(pipeline_id)

    from .dispatcher import dispatch_stage
    import asyncio

    if pipeline.status == PipelineStatus.CREATED:
        pipeline.start()

    safety_limit = max(len(pipeline.stages) * 3, 1)
    steps = 0

    while pipeline.status != PipelineStatus.FINISHED:
        steps += 1
        if steps > safety_limit:
            raise RuntimeError("auto advance exceeded safety limit")

        if pipeline.status == PipelineStatus.RUNNING:
            asyncio.run(dispatch_stage(pipeline))
            if pipeline.status != PipelineStatus.RUNNING:
                # dispatcher 会把状态改成 WAITING_APPROVAL
                continue
            # 防止死循环跳出
            break

        if pipeline.status == PipelineStatus.WAITING_APPROVAL:
            # 自动审批，为了演示全自动
            approve(pipeline.id)
            continue

        break

    return pipeline


def advance_one_stage(pipeline_id: str) -> Pipeline:
    """内部调试工具：仅用于调试，不对外暴露API。自动推进一个阶段并自动审批。"""
    pipeline = get_pipeline(pipeline_id)

    if pipeline.status == PipelineStatus.FINISHED:
        return pipeline

    # 处理初始状态，先启动
    if pipeline.status == PipelineStatus.CREATED:
        pipeline.start()
    elif pipeline.status == PipelineStatus.WAITING_APPROVAL:
        # 调试模式：自动审批当前checkpoint
        checkpoint = pipeline.current_checkpoint()
        if checkpoint is None:
            raise ValueError("no active checkpoint")
        pipeline.approve(checkpoint.id)

    current_stage = pipeline.current_stage()
    if not current_stage:
        pipeline.status = PipelineStatus.FINISHED
        return pipeline

    # 处理当前阶段逻辑：交给连接器层执行对应 Agent
    _execute_current_stage_agent(pipeline)

    # 完成当前阶段
    current_stage.mark_done()
    pipeline.checkpoint_for_current_stage()

    # 调试模式：自动审批并推进到下一个阶段
    checkpoint = pipeline.current_checkpoint()
    pipeline.approve(checkpoint.id)

    return pipeline


def emit_event(
    event_type: EventType, pipeline_id: str, checkpoint_id: str | None = None
) -> Pipeline:
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
