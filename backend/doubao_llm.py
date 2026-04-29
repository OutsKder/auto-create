"""兼容入口：保持历史导入 backend.doubao_llm 可用。"""

try:
    from backend.agent.llm.legacy_doubao_client import (
        llm,
        chat_with_doubao,
        stream_chat_with_doubao,
    )
except ImportError:
    from agent.llm.legacy_doubao_client import (
        llm,
        chat_with_doubao,
        stream_chat_with_doubao,
    )


if __name__ == "__main__":
    print("正在测试普通调用豆包大模型 (LangChain版)...")
    answer = chat_with_doubao("你是什么模型seed1.6吗")
    print(f"回答：\n{answer}\n")
