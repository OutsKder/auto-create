import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

DOUBAO_API_KEY = os.environ.get(
    "DOUBAO_API_KEY", "ark-ed75ee35-931d-4978-bdd8-4f0a9fa4e230-5f52b"
)
DOUBAO_ENDPOINT = os.environ.get("DOUBAO_ENDPOINT", "ep-20260423223020-fxwrn")

# 使用 LangChain 的 ChatOpenAI 包装器，指向火山引擎兼容接口
llm = ChatOpenAI(
    model=DOUBAO_ENDPOINT,
    api_key=DOUBAO_API_KEY,
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    temperature=0.7,
    streaming=True,
)


def chat_with_doubao(
    prompt: str, system_prompt: str = "你是一个强大的人工智能助手。"
) -> str:
    """使用 LangChain 调用豆包大模型。"""
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"请求失败: {str(e)}"


def stream_chat_with_doubao(
    prompt: str, system_prompt: str = "你是一个强大的人工智能助手。"
):
    """使用 LangChain 流式调用豆包大模型。"""
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
    try:
        for chunk in llm.stream(messages):
            yield chunk.content
    except Exception as e:
        yield f"\n[请求失败: {str(e)}]"
