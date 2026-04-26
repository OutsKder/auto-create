from typing import Dict

from .events import EventType
from .pipeline import Pipeline, PipelineStatus
from .checkpoint import Checkpoint

_PIPELINES: Dict[str, Pipeline] = {}


def create_pipeline() -> Pipeline:
    pipeline = Pipeline.create_default()
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
    return pipeline


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

    if pipeline.status == PipelineStatus.CREATED:
        pipeline.start()
        return pipeline

    if pipeline.status == PipelineStatus.WAITING_APPROVAL:
        checkpoint = pipeline.current_checkpoint()
        if checkpoint is None:
            raise ValueError("no active checkpoint")
        pipeline.approve(checkpoint.id)
        return pipeline

    if pipeline.status == PipelineStatus.RUNNING:
        pipeline.stage_done()
        checkpoint = pipeline.current_checkpoint()
        if checkpoint is None:
            raise ValueError("no active checkpoint")
        pipeline.approve(checkpoint.id)
        return pipeline

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
