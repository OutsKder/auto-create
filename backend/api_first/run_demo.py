import os
import sys
from pprint import pprint

# 确保能包引入
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from api_first.pipeline import PipelineStatus
from api_first.service import create_pipeline, run_pipeline, approve, get_pipeline

def run_e2e_demo():
    print("=" * 60)
    print("1. 创建 Pipeline")
    pipeline = create_pipeline(context={"requirement_raw": "实现一个基础的用户登录注册页面，需要包含账号密码输入框和提交按钮。"})
    print(f"Pipeline ID: {pipeline.id}")
    print(f"初态: {pipeline.status.value}, Stage: {pipeline.current_stage().name if pipeline.current_stage() else 'None'}")
    
    # 我们用一个循环持续触发跑到结束
    step = 1
    while pipeline.status != PipelineStatus.FINISHED:
        print("\n" + "-" * 40)
        
        # 1. 处于 CREATED / RUNNING 时，我们要去 run 让它推进
        if pipeline.status in (PipelineStatus.CREATED, PipelineStatus.RUNNING):
            stage_name = pipeline.current_stage().name
            print(f"步骤 {step}: 执行阶段 => [{stage_name}]")
            # 这会调用 dispatcher 分发去跑具体的 Agent，完成后自动进入 WAITING_APPROVAL
            run_pipeline(pipeline.id)
            print(f"    --> 执行后状态: {pipeline.status.value}")
            
        # 2. 处于等待人类审批状态时
        elif pipeline.status == PipelineStatus.WAITING_APPROVAL:
            checkpoint = pipeline.current_checkpoint()
            stage_name = pipeline.current_stage().name
            print(f"步骤 {step}: 审批阶段 => [{stage_name}] checkpoint={checkpoint.id}")
            
            # 在这里打印一下阶段执行完之后塞进 context 的产物体会一下
            if stage_name == "需求分析":
                doc = pipeline.context.get("requirement_structured", "没有结构化数据")
                print(f"    [产物窥探] 分析结果摘要: {pipeline.context.get('analysis_doc')}")
            elif stage_name == "方案设计":
                print(f"    [产物窥探] 架构设计: {pipeline.context.get('design_doc')}")
            elif stage_name == "代码生成":
                print(f"    [产物窥探] 代码 Diff: {pipeline.context.get('diff_bundle')}")
            elif stage_name == "测试生成":
                print(f"    [产物窥探] 测试报告: {pipeline.context.get('test_report')}")
                
            # 模拟人工点击“同意”按钮
            approve(pipeline.id, checkpoint.id)
            print(f"    --> 审批通过，向后流转...当前状态: {pipeline.status.value}")
            
        step += 1
        
    print("\n" + "=" * 60)
    print("🎉 Pipeline 执行结束！最终状态：FINISHED")

if __name__ == "__main__":
    run_e2e_demo()
