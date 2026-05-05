from pprint import pprint
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    current_dir = Path(__file__).resolve().parent
    backend_dir = current_dir.parent
    sys.path.insert(0, str(backend_dir))
    from api_first.pipeline import PipelineStatus
    from api_first.service import create_pipeline, run_pipeline, approve, reject
else:
    from .pipeline import PipelineStatus
    from .service import create_pipeline, run_pipeline, approve, reject


if __name__ == "__main__":
    pipeline = create_pipeline(context={"requirement_raw": "演示 api-first 状态机与 agent 连接层的联动。"})
    pprint({"event": "create_pipeline", "pipeline": pipeline})

    while pipeline.status != PipelineStatus.FINISHED:
        if pipeline.status in (PipelineStatus.CREATED, PipelineStatus.RUNNING):
            pipeline = run_pipeline(pipeline.id)
            pprint({"event": "run_pipeline", "pipeline_status": pipeline.status, "stage": pipeline.current_stage()})
        elif pipeline.status == PipelineStatus.WAITING_APPROVAL:
            checkpoint = pipeline.current_checkpoint()
            pprint({"event": "need_approval", "pipeline_status": pipeline.status, "stage": pipeline.current_stage(), "checkpoint": checkpoint})
            pipeline = approve(pipeline.id, checkpoint.id)
            pprint({"event": "approve", "pipeline_status": pipeline.status, "stage": pipeline.current_stage(), "checkpoint": checkpoint})

    pprint({"event": "finish", "pipeline_status": pipeline.status, "stage": pipeline.current_stage()})
