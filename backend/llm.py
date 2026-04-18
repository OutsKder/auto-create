import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 初始化给定的 Qwen 语言模型后端
llm_model = ChatOpenAI(
    model="Qwen2.5-Coder-32B-Instruct-GPTQ-Int4/",
    base_url="http://47.123.4.240:11499/v1/",
    api_key="key",  # 根据要求直接硬编码
    streaming=True,
    max_tokens=2048
)

async def get_stage_prompt(stage_id: str, req_data: dict) -> str:
    """生成每个节点的专属 Prompt"""
    base_info = f"""
【需求来源信息】
标题：{req_data.get('title')}
背景：{req_data.get('background', '未提供')}
目标：{req_data.get('goal', '未提供')}
限制：{req_data.get('constraints', '未提供')}
"""
    prompts = {
        "analysis": f"""你是一位拥有十多年顶级互联网经验的【资深产品总监（Product Director）】。你需要对以下粗略的原始需求进行深度、极具结构化的拆解分析。请基于第一性原理，不要浮于表面，深挖用户真实痛点并评估长期业务价值。由于这是初步需求，你需要像剥洋葱一样把它展开。

【原始需求信息】
标题：{req_data.get('title')}
背景：{req_data.get('background', '未提供')}
目标：{req_data.get('goal', '未提供')}
限制条件：{req_data.get('constraints', '未提供')}

【产出要求】
请严格按照以下5个维度的专业结构输出（使用严谨优美的Markdown排版，使用加粗、列表和分隔线，方便阅读）：

### 一、 商业价值与产品愿景 (Vision & Value)
- **真伪需求研判**：用户表面需求背后的核心痛点到底是什么？是否存在更好的替代方案？
- **业务核心收益**：落地后的关键价值（如：降本增效指标、用户体验提升点、合规风险规避）。
- **北极星指标 (North Star Metric)**：如何通过量化指标来衡量该功能上线后的成功与否？

### 二、 用户画像与核心场景 (Personas & Scenarios)
- **利益相关者**：列出系统中所有受影响的角色（例如：普通员工、审批人、系统管理员等）及其核心诉求。
- **典型用户故事 (User Story)**：使用“作为 [角色]，我希望 [功能]，以便于 [价值]”的敏捷格式，列出前 3 个最具代表性的核心场景。

### 三、 MVP 核心功能拆解边界 (Scope & Features)
- **核心功能必做 (Must-haves)**：在现有约束条件下，MVP阶段绝对不能砍掉的核心功能模块。
- **伪需求与延期池 (Won't-haves)**：哪些功能看起来美好，但这期绝对不该做？请明确指出以防项目蔓延（Scope Creep）。
- **非功能性需求**：针对当前场景的安全性、性能、离线运行能力等特殊考量。

### 四、 潜在风险与可行性预警 (Risks & Feasibility)
- **业务运营卡点**：推广或落地过程中最可能遭遇的人为或流程阻力。
- **技术预警**：基于常识评估在当前限制条件下的最大技术难点（如弱网同步、隐私安全、多端适配等）。

### 五、 最优先级澄清清单 (Top Clarification Questions)
为防止后续方案跑偏，列出对业务方发起的 3-5 个“灵魂审问”（务必尖锐、直白，切中核心矛盾与未定义清楚的边界）。
""",
        "solution": f"你是资深架构师。根据以下需求，输出一份技术方案草稿，包含：模块拆解、API设计思路、数据库核心表或实体设计，以及技术难点。\n{base_info}",
        "coding": f"你是高级研发工程师。根据以下需求给出一个简单的代码骨架实现思路或者目录结构，以Markdown格式直接输出。\n{base_info}",
        "testing": f"你是QA专家。给出端到端的测试策略和最重要的5个边界用例。\n{base_info}",
        "review": f"你是项目技术Owner。结合上述需求要求，给出上线评审的Checklist，包含安全、性能、监控等方面。\n{base_info}"
    }
    return prompts.get(stage_id, f"请分析处理以下需求：\n{base_info}")

async def stream_llm_response(stage_id: str, req_data: dict):
    """
    真正地去请求大模型，并将流式响应逐个 yield 出去
    """
    prompt = await get_stage_prompt(stage_id, req_data)
    
    # 动态人设
    personas = {
        "analysis": "你是一位出色的【需求分析专家】。请用客观、专业的口吻输出内容，不要说客套话。",
        "solution": "你是一位顶级的【首席架构师（Architect）】。你的思考深入且注重系统架构的扩展性。",
        "coding": "你是一位拥有10年经验的【高级全栈开发工程师（Senior Developer）】。你的代码干净整洁，骨架清晰。",
        "testing": "你是一丝不苟的【资深 QA 工程师】。你善于发现边界条件和极端错误情况。",
        "review": "你是一位严厉但负责的【项目技术 Owner】。你负责把控最后的发版质量生命线。"
    }
    system_prompt = personas.get(stage_id, "你是【织界引擎】系统的高级 AI 智能体节点，不要废话，直接输出结果。")
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt)
    ]
    
    # 使用 Langchain 的 astream 真实发往 Qwen 模型
    async for chunk in llm_model.astream(messages):
        if chunk.content:
            yield chunk.content

