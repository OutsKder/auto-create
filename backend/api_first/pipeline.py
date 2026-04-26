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
        stage_specs = [
            {
                "id": "analysis",
                "name": "需求分析",
                "input": "自然语言需求描述",
                "output": "结构化需求文档（含验收标准）",
                "acceptance": [
                    "需求范围和边界明确",
                    "歧义项被标记并给出澄清建议",
                    "每条核心需求可追踪到验收标准",
                ],
            },
            {
                "id": "design",
                "name": "方案设计",
                "input": "结构化需求 + 代码库上下文",
                "output": "技术方案（含文件变更清单、API 设计）",
                "acceptance": [
                    "明确影响模块和风险",
                    "接口变更向后兼容策略清晰",
                    "变更文件清单可执行",
                ],
            },
            {
                "id": "coding",
                "name": "代码生成",
                "input": "技术方案 + 代码库",
                "output": "代码变更集（Diff）",
                "acceptance": [
                    "实现与技术方案一致",
                    "核心路径可运行",
                    "不引入无关重构",
                ],
            },
            {
                "id": "testing",
                "name": "测试生成",
                "input": "代码变更集 + 需求",
                "output": "测试代码 + 执行结果",
                "acceptance": [
                    "覆盖新增/修改的关键路径",
                    "至少包含单元测试与集成测试建议",
                    "失败用例给出可复现信息",
                ],
            },
            {
                "id": "review",
                "name": "代码评审",
                "input": "代码变更集 + 方案 + 测试结果",
                "output": "评审报告（含问题列表和修复建议）",
                "acceptance": [
                    "正确性/安全性/规范性均有结论",
                    "高优先级问题有定位和建议",
                    "评审结论可用于发布决策",
                ],
            },
            {
                "id": "delivery",
                "name": "交付集成",
                "input": "评审通过的变更集",
                "output": "可合并代码变更 + 变更摘要",
                "acceptance": [
                    "变更可合并",
                    "交付物与需求一一对应",
                    "发布说明完整",
                ],
            },
        ]

        return cls(
            stages=[
                Stage(
                    id=spec["id"],
                    name=spec["name"],
                    meta={
                        "input": spec["input"],
                        "output": spec["output"],
                        "acceptance": spec["acceptance"],
                    },
                )
                for spec in stage_specs
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
        self.checkpoint_for_current_stage()
        self.status = PipelineStatus.WAITING_APPROVAL
        return stage

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
