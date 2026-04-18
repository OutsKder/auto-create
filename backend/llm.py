import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# 使用标准的 OpenAI 客户端，这里可以配置为 DeepSeek/Ali/OpenAI
# 我们默认采用兼容的配置方案
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

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
    
    # 真实的大模型流式请求
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "你是【织界引擎】系统的 AI 智能体节点，在你的环节产出严谨、高质量的专业内容。不要废话，直接输出结果。"},
            {"role": "user", "content": prompt}
        ],
        stream=True,
    )
    
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
