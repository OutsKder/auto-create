from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict
from uuid import uuid4


class CheckpointStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class Checkpoint:
    id: str = field(default_factory=lambda: str(uuid4()))
    pipeline_id: str = ""
    stage_id: str = ""
    stage_name: str = ""
    status: CheckpointStatus = CheckpointStatus.PENDING
    note: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def approve(self, note: str = "") -> None:
        self.status = CheckpointStatus.APPROVED
        self.note = note

    def reject(self, note: str = "") -> None:
        self.status = CheckpointStatus.REJECTED
        self.note = note