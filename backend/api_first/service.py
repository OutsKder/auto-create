from typing import Dict

from .events import EventType
from .pipeline import Pipeline

_PIPELINES: Dict[str, Pipeline] = {}


def create_pipeline() -> Pipeline:
    pipeline = Pipeline.create_default()
    _PIPELINES[pipeline.id] = pipeline
    return pipeline


def run_pipeline(pipeline_id: str) -> Pipeline:
    pipeline = _PIPELINES[pipeline_id]
    pipeline.start()
    return pipeline


def approve(pipeline_id: str, checkpoint_id: str | None = None) -> Pipeline:
    pipeline = _PIPELINES[pipeline_id]
    pipeline.approve(checkpoint_id=checkpoint_id)
    return pipeline


def reject(pipeline_id: str, checkpoint_id: str | None = None) -> Pipeline:
    pipeline = _PIPELINES[pipeline_id]
    pipeline.reject(checkpoint_id=checkpoint_id)
    return pipeline


def emit_event(event_type: EventType, pipeline_id: str) -> Pipeline:
    if event_type == EventType.CREATE_PIPELINE:
        return create_pipeline()
    if event_type == EventType.RUN_PIPELINE:
        return run_pipeline(pipeline_id)
    if event_type == EventType.APPROVE:
        return approve(pipeline_id)
    if event_type == EventType.REJECT:
        return reject(pipeline_id)
    raise ValueError(f"unsupported event: {event_type}")
