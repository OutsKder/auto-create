from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    WAITING_APPROVAL = "WAITING_APPROVAL"


@dataclass
class Stage:
    id: str
    name: str
    status: StageStatus = StageStatus.PENDING
    meta: Dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        self.status = StageStatus.RUNNING

    def mark_done(self) -> None:
        self.status = StageStatus.DONE

    def need_approval(self) -> None:
        self.status = StageStatus.WAITING_APPROVAL

    def reset(self) -> None:
        self.status = StageStatus.PENDING
