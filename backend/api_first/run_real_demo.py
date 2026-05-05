import os
import sys

# 关键：把 auto-create 也要加到 sys.path 中，因为代码很多地方使用了 from backend.agent... 绝对引入
auto_create_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(auto_create_dir)

# 确保能包引入现在的相对路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from api_first.pipeline import PipelineStatus
from api_first.service import create_pipeline, run_pipeline, approve, get_pipeline

def run_real_e2e_demo():
    print("=" * 60)
    print("1. 创建 Pipeline")
    # 模拟一个实际需求: 修改 Python 代码逻辑而不是 HTML
    req = """给 `testcode` 项目的 main.py 增加异常捕获以避免崩溃，并加上完整的英文日志注释。
如果里面没有日志模块，请引入 python logging 模块代替 print。"""
    
    # 构建上下文：带上真实的 codebase 信息指向 testcode 目录
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "testcode"))
    
    pipeline = create_pipeline(context={
        "requirement_raw": req,
        "codebase": {
            "repo_path": repo_path
        }
    })
    
    print(f"Pipeline ID: {pipeline.id}")
    print(f"初态: {pipeline.status.value}, Stage: {pipeline.current_stage().name if pipeline.current_stage() else 'None'}")
    
    step = 1
    while pipeline.status != PipelineStatus.FINISHED:
        print("\n" + "-" * 40)
        
        if pipeline.status in (PipelineStatus.CREATED, PipelineStatus.RUNNING):
            stage_name = pipeline.current_stage().name
            print(f"步骤 {step}: 执行阶段 => [{stage_name}]")
            # 调用真实 Agent 的异步调度过程
            run_pipeline(pipeline.id)
            print(f"    --> 执行后状态: {pipeline.status.value}")
            
        elif pipeline.status == PipelineStatus.WAITING_APPROVAL:
            checkpoint = pipeline.current_checkpoint()
            stage_name = pipeline.current_stage().name
            print(f"步骤 {step}: 审批阶段 => [{stage_name}] checkpoint={checkpoint.id}")
            
            if stage_name == "需求分析":
                 print(f"    [产物窥探] 结构化需求: {pipeline.context.get('requirement_structured')}")
            elif stage_name == "方案设计":
                print(f"    [产物窥探] 架构设计: {str(pipeline.context.get('design_doc'))[:200]}...")
            elif stage_name == "代码生成":
                diff = pipeline.context.get('diff_bundle')
                print(f"    [产物窥探] 代码 Diff 生成文件数: {len(diff.get('changes', [])) if isinstance(diff, dict) else diff}")
            
            # 模拟人工选择“同意”
            approve(pipeline.id, checkpoint.id)
            print(f"    --> 审批通过，向后流转...当前状态: {pipeline.status.value}")
            
        step += 1
        
    print("\n" + "=" * 60)
    print("🎉 Pipeline 执行结束！最终状态：FINISHED")

if __name__ == "__main__":
    run_real_e2e_demo()
