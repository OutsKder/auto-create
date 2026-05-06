from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4
from copy import deepcopy


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
    stage_index: int = 0
    status: CheckpointStatus = CheckpointStatus.PENDING
    note: Optional[str] = None
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def approve(self, note: str = "") -> None:
        self.status = CheckpointStatus.APPROVED
        self.note = note

    def reject(self, note: str = "") -> None:
        self.status = CheckpointStatus.REJECTED
        self.note = note