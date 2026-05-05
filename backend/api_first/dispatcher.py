import logging

from .connectors.agent_connectors import dispatch_stage as dispatch_connector_stage
from .pipeline import Pipeline

logger = logging.getLogger(__name__)

async def dispatch_stage(pipeline: Pipeline):
    """兼容层：交给 connectors/agent_connectors.py 完成真正的 agent 分发。"""
    await dispatch_connector_stage(pipeline)
