import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 初始化给定的 Qwen 语言模型后端
llm_model = ChatOpenAI(
    model="Qwen2.5-Coder-32B-Instruct-GPTQ-Int4/",
    base_url="http://47.123.4.240:11499/v1/",
    api_key="key",  # 根据要求直接硬编码
    streaming=True
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
        "analysis": f"你是需求分析专家。请分析以下需求，提取核心目标、用户痛点、潜在风险，并列出3个澄清问题和验证标准。请用清晰的Markdown回复。\n{base_info}",
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

