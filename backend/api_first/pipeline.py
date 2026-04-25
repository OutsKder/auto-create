from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from .checkpoint import Checkpoint, CheckpointStatus
from .stage import Stage, StageStatus


class PipelineStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    FINISHED = "FINISHED"


@dataclass
class Pipeline:
    id: str = field(default_factory=lambda: str(uuid4()))
    status: PipelineStatus = PipelineStatus.CREATED
    stages: List[Stage] = field(default_factory=list)
    checkpoints: List[Checkpoint] = field(default_factory=list)
    current_stage_index: int = 0
    current_checkpoint_id: Optional[str] = None

    @classmethod
    def create_default(cls) -> "Pipeline":
        return cls(
            stages=[
                Stage(id="analysis", name="需求分析"),
                Stage(id="design", name="方案设计"),
                Stage(id="coding", name="写代码"),
                Stage(id="testing", name="测试"),
            ]
        )

    def current_stage(self) -> Optional[Stage]:
        if 0 <= self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return None

    def next_stage(self) -> Optional[Stage]:
        next_index = self.current_stage_index + 1
        if 0 <= next_index < len(self.stages):
            return self.stages[next_index]
        return None

    def current_checkpoint(self) -> Optional[Checkpoint]:
        if self.current_checkpoint_id is None:
            return None
        for checkpoint in self.checkpoints:
            if checkpoint.id == self.current_checkpoint_id:
                return checkpoint
        return None

    def checkpoint_for_current_stage(self) -> Checkpoint:
        stage = self.current_stage()
        if stage is None:
            raise ValueError("no active stage")

        checkpoint = Checkpoint(
            pipeline_id=self.id,
            stage_id=stage.id,
            stage_name=stage.name,
        )
        self.checkpoints.append(checkpoint)
        self.current_checkpoint_id = checkpoint.id
        return checkpoint

    def start(self) -> Stage:
        if not self.stages:
            raise ValueError("pipeline has no stages")
        self.status = PipelineStatus.RUNNING
        stage = self.current_stage()
        stage.start()
        return stage

    def stage_done(self) -> Optional[Stage]:
        stage = self.current_stage()
        if stage is None:
            return None
        stage.mark_done()
        next_stage = self.next_stage()
        if next_stage is None:
            self.status = PipelineStatus.FINISHED
            return None
        self.current_stage_index += 1
        next_stage = self.current_stage()
        next_stage.start()
        return next_stage

    def need_approval(self) -> Stage:
        stage = self.current_stage()
        if stage is None:
            raise ValueError("no active stage")
        stage.need_approval()
        self.status = PipelineStatus.WAITING_APPROVAL
        self.checkpoint_for_current_stage()
        return stage

    def approve(self, checkpoint_id: Optional[str] = None) -> Optional[Stage]:
        checkpoint = self._resolve_checkpoint(checkpoint_id)
        checkpoint.approve()
        stage = self.current_stage()
        if stage is None:
            return None
        stage.mark_done()
        self.current_checkpoint_id = None
        next_stage = self.next_stage()
        if next_stage is None:
            self.status = PipelineStatus.FINISHED
            return None
        self.current_stage_index += 1
        self.status = PipelineStatus.RUNNING
        next_stage = self.current_stage()
        next_stage.start()
        return next_stage

    def reject(self, checkpoint_id: Optional[str] = None) -> Stage:
        checkpoint = self._resolve_checkpoint(checkpoint_id)
        checkpoint.reject()
        stage = self.current_stage()
        if stage is None:
            raise ValueError("no active stage")
        stage.reset()
        self.status = PipelineStatus.RUNNING
        self.current_checkpoint_id = None
        return stage

    def _resolve_checkpoint(self, checkpoint_id: Optional[str] = None) -> Checkpoint:
        target_id = checkpoint_id or self.current_checkpoint_id
        if target_id is None:
            raise ValueError("no active checkpoint")
        for checkpoint in self.checkpoints:
            if checkpoint.id == target_id:
                return checkpoint
        raise ValueError(f"checkpoint not found: {target_id}")
