from enum import Enum


class EventType(str, Enum):
    CREATE_PIPELINE = "create_pipeline"
    RUN_PIPELINE = "run_pipeline"
    STAGE_DONE = "stage_done"
    NEED_APPROVAL = "need_approval"
    APPROVE = "approve"
    REJECT = "reject"
