import unittest

from api_first.events import EventType
from api_first.pipeline import PipelineStatus
from api_first.service import create_pipeline, emit_event, run_pipeline


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
        pipeline = create_pipeline()
        run_pipeline(pipeline.id)

        while pipeline.status != PipelineStatus.FINISHED:
            pipeline.stage_done()
            checkpoint = pipeline.current_checkpoint()
            pipeline.approve(checkpoint.id)

        self.assertEqual(PipelineStatus.FINISHED, pipeline.status)
        self.assertEqual("delivery", pipeline.current_stage().id)
        self.assertEqual("DONE", pipeline.current_stage().status.value)

    def test_need_approval_and_approve_moves_to_next_stage(self):
        pipeline = create_pipeline()
        run_pipeline(pipeline.id)
        pipeline.stage_done()  # analysis -> design

        emit_event(EventType.NEED_APPROVAL, pipeline.id)
        self.assertEqual(PipelineStatus.WAITING_APPROVAL, pipeline.status)
        self.assertIsNotNone(pipeline.current_checkpoint())

        checkpoint = pipeline.current_checkpoint()
        emit_event(EventType.APPROVE, pipeline.id, checkpoint_id=checkpoint.id)

        self.assertEqual(PipelineStatus.RUNNING, pipeline.status)
        self.assertEqual("coding", pipeline.current_stage().id)

    def test_reject_resets_current_stage(self):
        pipeline = create_pipeline()
        run_pipeline(pipeline.id)
        pipeline.stage_done()  # analysis -> design
        emit_event(EventType.NEED_APPROVAL, pipeline.id)
        checkpoint = pipeline.current_checkpoint()

        emit_event(EventType.REJECT, pipeline.id, checkpoint_id=checkpoint.id)

        self.assertEqual(PipelineStatus.RUNNING, pipeline.status)
        self.assertEqual("design", pipeline.current_stage().id)
        self.assertEqual("PENDING", pipeline.current_stage().status.value)


if __name__ == "__main__":
    unittest.main()
