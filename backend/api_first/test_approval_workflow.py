import unittest
from unittest.mock import patch
from copy import deepcopy
import sys
import os

# 添加上级目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_first.pipeline import Pipeline, PipelineStatus, StageStatus
from api_first.service import create_pipeline, run_pipeline, approve, reject, stage_done
from api_first.checkpoint import CheckpointStatus


class TestApprovalDrivenWorkflow(unittest.TestCase):
    """测试基于Checkpoint的审批驱动流程"""

    def setUp(self):
        # 创建测试流水线
        self.pipeline = create_pipeline(context={
            "requirement_raw": "做一个简单的员工管理系统",
            "custom_field": "初始值"
        })
        self.original_context = deepcopy(self.pipeline.context)

    def test_stage_completion_goes_to_waiting_approval(self):
        """测试：阶段执行完成后，必须进入WAITING_APPROVAL状态，不会自动推进"""
        # 直接启动阶段，模拟执行完成
        self.pipeline.start()
        current_stage = self.pipeline.current_stage()
        self.assertEqual(current_stage.id, "analysis")
        self.assertEqual(current_stage.status, StageStatus.RUNNING)
        
        # 模拟执行agent，修改上下文
        self.pipeline.context.update({
            "requirement_structured": {"goal": "员工管理"},
            "custom_field": "修改后的值"
        })

        # 标记阶段完成
        stage_done(self.pipeline.id)

        # 验证状态：进入等待审批，没有自动推进
        self.assertEqual(self.pipeline.status, PipelineStatus.WAITING_APPROVAL)
        self.assertEqual(self.pipeline.current_stage_index, 0)  # 仍然在analysis阶段索引
        self.assertEqual(self.pipeline.current_stage().id, "analysis")
        self.assertEqual(self.pipeline.current_stage().status, StageStatus.DONE)

        # 验证Checkpoint已创建
        checkpoint = self.pipeline.current_checkpoint()
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint.status, CheckpointStatus.PENDING)
        self.assertEqual(checkpoint.stage_index, 0)
        self.assertEqual(checkpoint.stage_id, "analysis")
        # 验证上下文快照已保存
        self.assertIn("requirement_structured", checkpoint.context_snapshot)
        self.assertEqual(checkpoint.context_snapshot["custom_field"], "修改后的值")

    def test_approve_advances_to_next_stage(self):
        """测试：approve后正确推进到下一个阶段并启动"""
        # 先执行第一个阶段并完成，进入审批状态
        self.pipeline.start()
        self.pipeline.context.update({"requirement_structured": {}})
        stage_done(self.pipeline.id)
        checkpoint = self.pipeline.current_checkpoint()

        # 执行approve
        approve(self.pipeline.id, checkpoint_id=checkpoint.id)

        # 验证：已推进到下一个阶段
        self.assertEqual(self.pipeline.status, PipelineStatus.RUNNING)
        self.assertEqual(self.pipeline.current_stage_index, 1)  # 已推进到design阶段
        self.assertEqual(self.pipeline.current_stage().id, "design")
        self.assertEqual(self.pipeline.current_stage().status, StageStatus.RUNNING)
        # 验证checkpoint状态
        self.assertEqual(checkpoint.status, CheckpointStatus.APPROVED)
        # 验证当前没有待审批的checkpoint
        self.assertIsNone(self.pipeline.current_checkpoint())

    def test_reject_resets_stage_and_restore_context(self):
        """测试：reject后重置当前阶段，恢复上下文快照，可以重新执行"""
        # 先执行第一个阶段并完成，进入审批状态
        self.pipeline.start()
        self.pipeline.context.update({
            "requirement_structured": {"goal": "员工管理"},
            "custom_field": "修改后的值"
        })
        stage_done(self.pipeline.id)
        checkpoint = self.pipeline.current_checkpoint()
        context_before_reject = deepcopy(self.pipeline.context)

        # 修改上下文，测试回滚效果
        self.pipeline.context["temp_change"] = "临时修改"
        self.assertIn("temp_change", self.pipeline.context)

        # 执行reject
        reject(self.pipeline.id, checkpoint_id=checkpoint.id, note="需求分析不完整，需要补充细节")

        # 验证：reject后仍然在当前阶段，阶段被重置
        self.assertEqual(self.pipeline.status, PipelineStatus.RUNNING)
        self.assertEqual(self.pipeline.current_stage_index, 0)  # 仍然在analysis阶段
        self.assertEqual(self.pipeline.current_stage().id, "analysis")
        self.assertEqual(self.pipeline.current_stage().status, StageStatus.PENDING)  # 已重置为待执行

        # 验证上下文已恢复到checkpoint保存的快照
        self.assertEqual(self.pipeline.context, context_before_reject)
        self.assertNotIn("temp_change", self.pipeline.context)  # 临时修改已被回滚

        # 验证checkpoint状态
        self.assertEqual(checkpoint.status, CheckpointStatus.REJECTED)
        self.assertEqual(checkpoint.note, "需求分析不完整，需要补充细节")
        # 验证当前没有待审批的checkpoint
        self.assertIsNone(self.pipeline.current_checkpoint())

        # 可以重新执行当前阶段
        # 启动阶段
        self.pipeline.current_stage().start()
        self.assertEqual(self.pipeline.current_stage().status, StageStatus.RUNNING)
        
        with patch("api_first.service.requirement_agent") as mock_agent:
            mock_agent.execute.return_value = {
                "requirement_structured": {"goal": "员工管理", "features": ["员工列表"]},
                "custom_field": "修改后的值_重新执行"
            }
            # 重新执行需求分析阶段
            from api_first.service import _execute_current_stage_agent
            _execute_current_stage_agent(self.pipeline)

        self.assertEqual(self.pipeline.context["custom_field"], "修改后的值_重新执行")

    def test_no_auto_advance_after_approval(self):
        """测试：没有自动审批逻辑，必须手动调用approve才能推进"""
        # 执行第一个阶段
        self.pipeline.start()
        self.pipeline.context.update({"requirement_structured": {}})
        stage_done(self.pipeline.id)

        # 等待审批状态，不会自动推进
        self.assertEqual(self.pipeline.status, PipelineStatus.WAITING_APPROVAL)
        self.assertEqual(self.pipeline.current_stage_index, 0)

        # 即使再次调用run_pipeline/run_agent_stages也不会自动推进
        from api_first.service import run_agent_stages
        run_agent_stages(self.pipeline.id)

        self.assertEqual(self.pipeline.status, PipelineStatus.WAITING_APPROVAL)
        self.assertEqual(self.pipeline.current_stage_index, 0)

        # 手动approve后才会推进
        checkpoint = self.pipeline.current_checkpoint()
        approve(self.pipeline.id, checkpoint.id)
        self.assertEqual(self.pipeline.current_stage_index, 1)

    def test_full_approval_workflow(self):
        """测试完整的审批驱动流程：执行→审批→执行→审批直到完成"""
        mock_results = [
            {"requirement_structured": {"goal": "员工管理"}},  # analysis阶段结果
            {"tech_design": {"modules": ["user"]}},  # design阶段结果
            {"code_diff": "xxx"},  # coding阶段结果
            {"test_cases": []},  # testing阶段结果
            {"review_report": {"approved": True}},  # review阶段结果
            {"delivery_package": "v1.0.0"},  # delivery阶段结果
        ]

        # 直接启动第一个阶段
        self.pipeline.start()
        self.pipeline.context.update(mock_results[0])

        # 遍历所有阶段
        for i in range(6):
            current_stage_id = self.pipeline.current_stage().id
            print(f"处理阶段: {i+1}/6 - {current_stage_id}")

            # 1. 完成当前阶段
            stage_done(self.pipeline.id)
            self.assertEqual(self.pipeline.status, PipelineStatus.WAITING_APPROVAL)

            # 如果是最后一个阶段，approve后会结束
            if i == 5:
                checkpoint = self.pipeline.current_checkpoint()
                approve(self.pipeline.id, checkpoint.id)
                self.assertEqual(self.pipeline.status, PipelineStatus.FINISHED)
                break

            # 2. 审批通过
            checkpoint = self.pipeline.current_checkpoint()
            self.assertEqual(checkpoint.stage_index, i)
            approve(self.pipeline.id, checkpoint.id)

            # 3. 已推进到下一个阶段
            self.assertEqual(self.pipeline.current_stage_index, i + 1)
            self.assertEqual(self.pipeline.status, PipelineStatus.RUNNING)

        print("完整审批流程测试通过！")
        self.assertEqual(self.pipeline.status, PipelineStatus.FINISHED)
        self.assertEqual(len(self.pipeline.checkpoints), 6)  # 每个阶段一个checkpoint


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
