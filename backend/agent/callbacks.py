import time
import sys
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult


class TraceCallbackHandler(BaseCallbackHandler):
    """
    可观测性链路追踪回调处理器

    功能：
    1. 实现流式打字机效果输出
    2. 记录完整的 Prompt 和响应结果
    3. 记录 Tokens 消耗
    4. 记录整个生成过程的耗时
    """

    def __init__(self):
        self.start_time = 0.0
        self.end_time = 0.0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.prompts = []
        self.completion = ""
        self.meta_info = {}

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        """记录模型执行开始及 Prompt 详情"""
        self.start_time = time.time()
        self.prompts = [[m.content for m in msg_list] for msg_list in messages]
        print("\n[AI思考中] 正在逐字输出...")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """接收新生成的 token 实现流式输出"""
        sys.stdout.write(token)
        sys.stdout.flush()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """模型执行结束记录生成结果与 Token 开销"""
        self.end_time = time.time()
        print("\n\n")

        if len(response.generations) > 0 and len(response.generations[0]) > 0:
            self.completion = response.generations[0][0].text

        token_usage = {}

        llm_output = response.llm_output or {}
        if "token_usage" in llm_output:
            token_usage = llm_output["token_usage"]
        else:
            if len(response.generations) > 0 and len(response.generations[0]) > 0:
                gen = response.generations[0][0]
                if hasattr(gen, "message") and hasattr(
                    gen.message, "response_metadata"
                ):
                    meta = gen.message.response_metadata
                    if isinstance(meta, dict) and "token_usage" in meta:
                        token_usage = meta["token_usage"]

        if token_usage:
            self.total_tokens = token_usage.get("total_tokens", 0)
            self.prompt_tokens = token_usage.get("prompt_tokens", 0)
            self.completion_tokens = token_usage.get("completion_tokens", 0)
        else:
            self.prompt_tokens = int(len(str(self.prompts)) * 1.5)
            self.completion_tokens = int(len(str(self.completion)) * 1.5)
            self.total_tokens = self.prompt_tokens + self.completion_tokens

        elapsed_time = self.end_time - self.start_time

        self.meta_info = {
            "elapsed_seconds": round(elapsed_time, 2),
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "prompts_snapshot": self.prompts,
            "completion_snapshot": self.completion,
        }

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """发生错误时候的钩子"""
        self.end_time = time.time()
        print(f"\n[Trace] 模型调用发生异常：{error}")

    def print_trace_report(self) -> None:
        """控制台打印溯源分析报告"""
        if not self.meta_info:
            # 计算默认值
            elapsed_seconds = round(self.end_time - self.start_time, 2) if self.end_time > 0 else 0
            if not self.total_tokens:
                # 估算 tokens
                self.prompt_tokens = int(len(str(self.prompts)) * 1.5) if self.prompts else 0
                self.completion_tokens = int(len(str(self.completion)) * 1.5) if self.completion else 0
                self.total_tokens = self.prompt_tokens + self.completion_tokens
        else:
            elapsed_seconds = self.meta_info.get('elapsed_seconds', 0)

        print(f"====== 📊 Agent Trace 观测链路报告 ======")
        print(f"⏱️  耗时: {elapsed_seconds}秒")
        print(
            f"🪙  Tokens 消耗: 提示词 {self.prompt_tokens} + 补全 {self.completion_tokens} = 总计 {self.total_tokens}"
        )
        print(f"📝  请求Prompt预览: {str(self.prompts)[:200] if self.prompts else '[]'}...")
        print("=" * 41)
