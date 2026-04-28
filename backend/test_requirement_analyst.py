import os
import sys
import json

# 测试日志采用紧凑模式，避免终端被逐字流式输出和超长上下文刷屏。
os.environ.setdefault("AGENT_TRACE_COMPACT", "1")

# 确保能导入 backend 下的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import RequirementAnalyst, TechArchitect
from backend.doubao_llm import llm as doubao_llm


def _clip(text: str, limit: int = 120) -> str:
    value = str(text or "").replace("\n", " ").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _print_requirement_summary(title: str, result: dict) -> None:
    structured = result.get("requirement_structured", {}) or {}
    print(f"\n{title}")
    print(f"- is_clear: {structured.get('is_clear')}")
    print(f"- goal: {_clip(structured.get('goal', ''))}")
    print(f"- features: {len(structured.get('features', []) or [])}")
    print(f"- constraints: {len(structured.get('constraints', []) or [])}")
    print(
        f"- acceptance_criteria: {len(structured.get('acceptance_criteria', []) or [])}"
    )


def _print_design_summary(title: str, result: dict) -> None:
    design = result.get("design", {}) or {}
    plan = design.get("file_change_plan", []) or []
    print(f"\n{title}")
    print(f"- architecture: {_clip(design.get('architecture', ''))}")
    print(f"- api_design: {_clip(design.get('api_design', ''))}")
    print(f"- file_change_plan: {len(plan)}")
    for item in plan[:5]:
        print(f"  - {item.get('change_type', 'Modify')}: {item.get('file_path', '')}")
    if len(plan) > 5:
        print(f"  - ... 其余 {len(plan) - 5} 项省略")
    print(f"- risk_analysis: {_clip(design.get('risk_analysis', ''))}")


def test_requirement_analyst():
    """测试需求分析 Agent"""
    print("====== 开始运行 Requirement Analyst 测试 ======\n")

    # 初始化 Agent (使用真实的豆包LLM)
    analyst = RequirementAnalyst(llm_provider=doubao_llm)

    # 测试场景 1: 正常需求分析
    print("=== 测试场景 1: 正常需求分析 ===\n")
    test_context = {
        "requirement_raw": """
        我需要做一个内部人员管理的后台，要包括员工列表、增加新员工、删除员工的功能。
        还要有一个统计面板，能看各个部门的人数占比饼图。
        要求页面加载要在2秒内完成，并且必须有权限控制，只有管理员能删人。
        另外，UI要偏梦感和科技感，类似飞书的风格。
        """
    }

    print(f"输入需求:\n{test_context['requirement_raw']}\n")
    print("正在调用 LLM 进行需求分析...")

    try:
        # 执行 Agent
        result = analyst.execute(test_context)

        _print_requirement_summary("\n====== 分析成功（摘要） ======", result)

        # 基本校验
        assert "requirement_structured" in result, "缺少 requirement_structured 字段"
        structured_data = result["requirement_structured"]
        assert "goal" in structured_data, "缺少 goal 字段"
        assert "features" in structured_data, "缺少 features 字段"
        assert "constraints" in structured_data, "缺少 constraints 字段"
        assert "acceptance_criteria" in structured_data, "缺少 acceptance_criteria 字段"
        assert "is_clear" in structured_data, "缺少 is_clear 字段"
        assert (
            "clarifying_questions" in structured_data
        ), "缺少 clarifying_questions 字段"

        print(f"\n需求是否清晰: {structured_data['is_clear']}")
        print(f"核心目标: {structured_data['goal']}")
        print(f"功能点数量: {len(structured_data['features'])}")
        print(f"约束条件数量: {len(structured_data['constraints'])}")
        print(f"验收标准数量: {len(structured_data['acceptance_criteria'])}")

        # 测试场景 2: 模糊需求测试
        print("\n\n=== 测试场景 2: 模糊需求测试 ===\n")
        fuzzy_context = {"requirement_raw": "我要做一个类似微信的软件，越快越好"}

        max_retries = 2
        for i in range(max_retries):
            print(f"\n--- 第 {i+1} 轮交互 ---")
            print(f"用户当前输入:\n{fuzzy_context['requirement_raw']}")
            fuzzy_result = analyst.execute(fuzzy_context)

            structured = fuzzy_result.get("requirement_structured", {})
            is_clear = structured.get("is_clear", False)

            print(f"\n>> Agent判断 is_clear: {is_clear}")
            if is_clear:
                print("✅ 需求终于清晰！进入下一环节，最终输出：")
                _print_requirement_summary("- 模糊需求澄清结果（摘要）", fuzzy_result)
                break

            questions = structured.get("clarifying_questions", [])
            print(
                f"⚠️ Agent以为需求不足以支撑开发，挂起流程并提出 {len(questions)} 个追问:"
            )
            for idx, q in enumerate(questions):
                print(f"  {idx+1}. {q}")

            if i < max_retries - 1:
                # 模拟用户根据问题进行补充
                print("\n[自动化模拟] -> 用户正在根据追问补充细节...")
                fuzzy_context[
                    "requirement_raw"
                ] += "\n[补充说明1]: 这是用于我们公司内部培训的交流工具，仅包含群聊和文件发送，不需要朋友圈和支付功能。开发要在1个月内上线，带有阅后即焚功能。"
            else:
                print("\n⚠️ 达到最大追问次数，跳出反问循环，最终输出需求分析：")
                _print_requirement_summary("- 最终需求分析（摘要）", fuzzy_result)

        # 测试场景 3: 极端短输入测试
        print("\n\n=== 测试场景 3: 极端短输入测试 ===\n")
        extreme_context = {"requirement_raw": "111"}
        extreme_result = analyst.execute(extreme_context)
        _print_requirement_summary("- 极端短输入结果（摘要）", extreme_result)

        # 验证极端输入处理
        extreme_structured = extreme_result.get("requirement_structured", {})
        assert not extreme_structured.get("is_clear"), "极端输入应该被标记为不清晰"
        assert (
            len(extreme_structured.get("clarifying_questions", [])) > 0
        ), "极端输入应该有澄清问题"

        # 测试场景 4: 空输入测试
        print("\n\n=== 测试场景 4: 空输入测试 ===\n")
        try:
            empty_context = {"requirement_raw": ""}
            empty_result = analyst.execute(empty_context)
            print("❌ 空输入应该抛出异常")
        except ValueError as e:
            print(f"✅ 空输入正确抛出异常: {e}")

        print("\n✅ 所有测试场景通过!")

    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback

        traceback.print_exc()


def test_full_flow():
    """测试完整流程：需求分析 -> 方案设计"""
    print("\n\n====== 开始运行完整流程测试 ======\n")

    # 初始化两个 Agent
    analyst = RequirementAnalyst(llm_provider=doubao_llm)
    architect = TechArchitect(llm_provider=doubao_llm)

    # 测试需求
    test_context = {
        "requirement_raw": "我需要为现有的计算器应用添加乘法和除法功能，并且要支持浮点数运算。"
    }

    print("=== 1. 需求分析阶段 ===")
    print(f"输入需求: {test_context['requirement_raw']}")

    # 执行需求分析
    analyst_result = analyst.execute(test_context)
    _print_requirement_summary("\n需求分析完成（摘要）", analyst_result)

    # 验证需求分析结果
    assert (
        "requirement_structured" in analyst_result
    ), "需求分析缺少 requirement_structured"
    requirement_structured = analyst_result["requirement_structured"]

    print("\n=== 2. 方案设计阶段 ===")
    # 构建方案设计的输入
    design_context = {"requirement_structured": requirement_structured}

    # 执行方案设计
    design_result = architect.execute(design_context)
    _print_design_summary("\n方案设计完成（摘要）", design_result)

    # 验证方案设计结果
    assert "design" in design_result, "方案设计缺少 design"
    design_data = design_result["design"]
    assert "architecture" in design_data, "方案设计缺少 architecture"
    assert "api_design" in design_data, "方案设计缺少 api_design"
    assert "file_change_plan" in design_data, "方案设计缺少 file_change_plan"
    assert "risk_analysis" in design_data, "方案设计缺少 risk_analysis"

    print("\n=== 3. 结果验证 ===")
    print(f"架构设计: {design_data['architecture'][:100]}...")
    print(f"API 设计: {design_data['api_design'][:100]}...")
    print(f"文件变更计划: {len(design_data['file_change_plan'])} 项")
    for item in design_data["file_change_plan"]:
        print(f"  - {item['change_type']}: {item['file_path']}")
    print(f"风险分析: {design_data['risk_analysis'][:100]}...")

    print("\n✅ 完整流程测试通过!")


def test_frontend_full_flow():
    """测试前端代码库完整流程：需求分析 -> 方案设计"""
    print("\n\n====== 开始运行前端代码库完整流程测试 ======\n")

    analyst = RequirementAnalyst(llm_provider=doubao_llm)
    architect = TechArchitect(llm_provider=doubao_llm)

    frontend_repo = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
        )
    )

    test_context = {
        "requirement_raw": "给前端登录界面换一个浅蓝色的背景，并且把登录按钮改成圆角的，要求代码改动尽可能小。",
        "codebase": {"repo_path": frontend_repo},
    }

    print("=== 1. 需求分析阶段（前端） ===")
    print(f"输入需求: {test_context['requirement_raw']}")

    analyst_result = analyst.execute(
        {"requirement_raw": test_context["requirement_raw"]}
    )
    _print_requirement_summary("\n需求分析完成（摘要）", analyst_result)

    assert (
        "requirement_structured" in analyst_result
    ), "前端需求分析缺少 requirement_structured"
    requirement_structured = analyst_result["requirement_structured"]

    print("\n=== 2. 方案设计阶段（前端） ===")
    design_context = {
        "requirement_structured": requirement_structured,
        "codebase": {"repo_path": frontend_repo},
    }

    design_result = architect.execute(design_context)
    _print_design_summary("\n前端方案设计完成（摘要）", design_result)

    assert "design" in design_result, "前端方案设计缺少 design"
    design_data = design_result["design"]
    assert "architecture" in design_data, "前端方案设计缺少 architecture"
    assert "api_design" in design_data, "前端方案设计缺少 api_design"
    assert "file_change_plan" in design_data, "前端方案设计缺少 file_change_plan"
    assert "risk_analysis" in design_data, "前端方案设计缺少 risk_analysis"

    codebase_context = design_result.get("codebase_context", {})
    hot_files = codebase_context.get("hot_files", [])
    retrieved_paths = [item.get("path", "") for item in hot_files]

    print("\n=== 3. 结果验证（前端） ===")
    print(f"架构设计: {design_data['architecture'][:100]}...")
    print(f"API 设计: {design_data['api_design'][:100]}...")
    print(f"文件变更计划: {len(design_data['file_change_plan'])} 项")
    for item in design_data["file_change_plan"]:
        print(f"  - {item['change_type']}: {item['file_path']}")
    print(f"召回文件数量: {len(hot_files)}")
    print(f"前端命中文件: {', '.join(retrieved_paths[:6])}")
    if len(retrieved_paths) > 6:
        print(f"- ... 其余 {len(retrieved_paths) - 6} 个文件省略")
    print(f"风险分析: {design_data['risk_analysis'][:100]}...")

    assert len(hot_files) > 0, "前端检索没有召回任何文件"
    assert any(
        path.endswith("index.html") for path in retrieved_paths
    ), "前端检索应命中 index.html"
    assert any(
        path.endswith("app.js") for path in retrieved_paths
    ), "前端检索应命中 app.js"
    assert any(
        "login" in path for path in retrieved_paths
    ), "前端检索应命中 login 目录文件"

    print("\n✅ 前端代码库完整流程测试通过!")


if __name__ == "__main__":
    # test_requirement_analyst()
    # test_full_flow()
    test_frontend_full_flow()
