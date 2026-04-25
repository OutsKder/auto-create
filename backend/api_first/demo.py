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
    pipeline = create_pipeline()
    pprint({"event": "create_pipeline", "pipeline": pipeline})

    pipeline = run_pipeline(pipeline.id)
    pprint({"event": "run_pipeline", "pipeline_status": pipeline.status, "stage": pipeline.current_stage()})

    pipeline.stage_done()
    pprint({"event": "stage_done_analysis", "pipeline_status": pipeline.status, "stage": pipeline.current_stage()})

    pipeline.need_approval()
    checkpoint = pipeline.current_checkpoint()
    pprint({"event": "need_approval", "pipeline_status": pipeline.status, "stage": pipeline.current_stage(), "checkpoint": checkpoint})

    approved_pipeline = approve(pipeline.id, checkpoint.id)
    pprint({"event": "approve", "pipeline_status": approved_pipeline.status, "stage": approved_pipeline.current_stage(), "checkpoint": approved_pipeline.checkpoints[-1]})

    rejected_pipeline = create_pipeline()
    rejected_pipeline = run_pipeline(rejected_pipeline.id)
    rejected_pipeline.stage_done()
    rejected_pipeline.need_approval()
    rejected_checkpoint = rejected_pipeline.current_checkpoint()
    rejected_pipeline = reject(rejected_pipeline.id, rejected_checkpoint.id)
    pprint({"event": "reject", "pipeline_status": rejected_pipeline.status, "stage": rejected_pipeline.current_stage(), "checkpoint": rejected_pipeline.checkpoints[-1]})

    while approved_pipeline.status != PipelineStatus.FINISHED:
        approved_pipeline.stage_done()
    pprint({"event": "finish", "pipeline_status": approved_pipeline.status, "stage": approved_pipeline.current_stage()})
