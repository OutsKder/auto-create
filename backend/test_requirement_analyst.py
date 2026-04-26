import os
import sys
import json

# 确保能导入 backend 下的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import RequirementAnalyst
from backend.doubao_llm import llm as doubao_llm


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

        print("\n====== 分析成功，输出如下 ======\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))

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
                print(json.dumps(fuzzy_result, ensure_ascii=False, indent=2))
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
                print(json.dumps(fuzzy_result, ensure_ascii=False, indent=2))

        # 测试场景 3: 极端短输入测试
        print("\n\n=== 测试场景 3: 极端短输入测试 ===\n")
        extreme_context = {"requirement_raw": "111"}
        extreme_result = analyst.execute(extreme_context)
        print(json.dumps(extreme_result, ensure_ascii=False, indent=2))

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


if __name__ == "__main__":
    test_requirement_analyst()
