import unittest
from unittest.mock import patch

from api_first.events import EventType
from api_first.pipeline import PipelineStatus
from api_first.service import create_pipeline, emit_event, run_pipeline
import api_first.service as pipeline_service


FAKE_ANALYSIS_RESULT = {
    "requirement_structured": {
        "is_clear": True,
        "clarifying_questions": [],
        "goal": "员工管理",
        "features": ["员工列表"],
        "constraints": ["2秒内加载"],
        "acceptance_criteria": ["可新增和删除员工"],
    },
    "meta_trace": {"mock": True},
}


class PipelineLifecycleTests(unittest.TestCase):
    def test_default_pipeline_has_six_stages_with_contract(self):
        pipeline = create_pipeline()

        self.assertEqual(6, len(pipeline.stages))
        self.assertEqual(
            ["analysis", "design", "coding", "testing", "review", "delivery"],
            [stage.id for stage in pipeline.stages],
        )
        self.assertIn("input", pipeline.stages[0].meta)
        self.assertIn("output", pipeline.stages[0].meta)
        self.assertIn("acceptance", pipeline.stages[0].meta)

    def test_happy_path_can_finish_all_stages(self):
        pipeline = create_pipeline(context={"requirement_raw": "做一个简单的任务管理系统"})
        with patch.object(pipeline_service, "requirement_agent") as mock_agent:
            mock_agent.execute.return_value = FAKE_ANALYSIS_RESULT
            
            while pipeline.status != PipelineStatus.FINISHED:
                if pipeline.status == PipelineStatus.WAITING_APPROVAL:
                    checkpoint = pipeline.current_checkpoint()
                    pipeline.approve(checkpoint.id)
                elif pipeline.status == PipelineStatus.RUNNING or pipeline.status == PipelineStatus.CREATED:
                    run_pipeline(pipeline.id)
                else:
                    break

        self.assertEqual(PipelineStatus.FINISHED, pipeline.status)
        self.assertEqual("delivery", pipeline.current_stage().id)
        self.assertEqual("DONE", pipeline.current_stage().status.value)

    def test_need_approval_and_approve_moves_to_next_stage(self):
        pipeline = create_pipeline(context={"requirement_raw": "做一个简单的任务管理系统"})
        with patch.object(pipeline_service, "requirement_agent") as mock_agent:
            mock_agent.execute.return_value = FAKE_ANALYSIS_RESULT
            run_pipeline(pipeline.id)
    
        self.assertEqual(PipelineStatus.WAITING_APPROVAL, pipeline.status)
        self.assertEqual("analysis", pipeline.current_stage().id)
        self.assertIsNotNone(pipeline.current_checkpoint())
    
        checkpoint = pipeline.current_checkpoint()
        emit_event(EventType.APPROVE, pipeline.id, checkpoint_id=checkpoint.id)
    
        self.assertEqual(PipelineStatus.RUNNING, pipeline.status)
        self.assertEqual("design", pipeline.current_stage().id)

    def test_reject_resets_current_stage(self):
        pipeline = create_pipeline(context={"requirement_raw": "做一个简单的任务管理系统"})
        with patch.object(pipeline_service, "requirement_agent") as mock_agent:
            mock_agent.execute.return_value = FAKE_ANALYSIS_RESULT
            run_pipeline(pipeline.id)

        checkpoint = pipeline.current_checkpoint()
        emit_event(EventType.REJECT, pipeline.id, checkpoint_id=checkpoint.id)

        self.assertEqual(PipelineStatus.RUNNING, pipeline.status)
        self.assertEqual("analysis", pipeline.current_stage().id)
        self.assertEqual("PENDING", pipeline.current_stage().status.value)

    def test_run_pipeline_executes_requirement_analysis_when_context_ready(self):
        pipeline = create_pipeline(context={"requirement_raw": "做一个员工管理后台"})
        with patch.object(pipeline_service, "requirement_agent") as mock_agent:
            mock_agent.execute.return_value = FAKE_ANALYSIS_RESULT
            run_pipeline(pipeline.id)

            self.assertEqual("analysis", pipeline.current_stage().id)
            self.assertEqual(PipelineStatus.WAITING_APPROVAL, pipeline.status)


if __name__ == "__main__":
    unittest.main()
