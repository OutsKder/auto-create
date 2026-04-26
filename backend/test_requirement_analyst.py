import os
import sys

# 确保能导入 backend 下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doubao_llm import llm
from agent.requirement_analyst import RequirementAnalyst
import json


def test_requirement_analyst():
    print("====== 开始运行 Requirement Analyst 测试 ======\n")

    # 初始化 Agent
    analyst = RequirementAnalyst(llm_provider=llm)

    # 构建模拟 Context
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

        print("\n\n====== 分析成功，输出如下 ======\n")
        print(json.dumps(result, ensure_ascii=False, indent=4))

        # 基本校验
        assert "requirement_structured" in result
        structured_data = result["requirement_structured"]
        assert "goal" in structured_data
        assert "features" in structured_data
        assert "constraints" in structured_data
        assert "acceptance_criteria" in structured_data
        # 验证新的交互属性
        assert "is_clear" in structured_data
        assert "clarifying_questions" in structured_data
        print(f"需求是否清晰: {structured_data['is_clear']}")

        # 增加一个模糊需求的测试(最多反问1次)
        print("\n\n====== 测试拦截模糊需求 (最多反问1次机制) ======\n")
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
                print(json.dumps(fuzzy_result, ensure_ascii=False, indent=4))
                break

            questions = structured.get("clarifying_questions", [])
            print(
                f"⚠️ Agent以为需求不足以支撑开发，挂起流程并提出 {len(questions)} 个致命追问:"
            )
            for idx, q in enumerate(questions):
                print(f"  {idx+1}. {q}")

            if i < max_retries - 1:
                # 模拟用户根据问题进行补充
                print("\n[自动化模拟] -> 用户正在根据追问补充细节...")
                if i == 0:
                    fuzzy_context[
                        "requirement_raw"
                    ] += "\n[补充说明1]: 这是用于我们公司内部培训的交流工具，仅包含群聊和文件发送，不需要朋友圈和支付功能。开发要在1个月内上线，带有阅后即焚功能。"
            else:
                print("\n⚠️ 达到最大追问次数(1次)，跳出反问循环，最终输出需求分析：")
                print(json.dumps(fuzzy_result, ensure_ascii=False, indent=4))

        # 验证对抗极端短字符输入
        print("\n\n====== 测试拦截极端输入 ======\n")
        extreme_context = {"requirement_raw": "111"}
        extreme_result = analyst.execute(extreme_context)
        print(json.dumps(extreme_result, ensure_ascii=False, indent=4))

        print("\n✅ 测试全部通过!")

    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")


if __name__ == "__main__":
    test_requirement_analyst()
