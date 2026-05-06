"""
通用 Prompt 模板，供所有 Agent 共享使用
"""

JSON_RETRY_SYSTEM_PROMPT = """你是一个严格的JSON纠错助手。请修复以下输出，使其完全符合给定的JSON Schema。不要输出任何多余内容，只需输出合法的JSON。"""

JSON_RETRY_HUMAN_PROMPT = """【原始预期格式】:
{format_instructions}

【错误的输出】:
{wrong_output}

【错误信息】:
{error_msg}

请直接输出修复后的JSON:"""

INPUT_TOO_SHORT_PROMPT = """您的输入过短或无具体意义，请详细描述您的核心业务需求。"""

TOKEN_LIMIT_EXCEEDED_PROMPT = """需求文档过长 (预估 {token_count} Tokens)，请将需求精简至 {max_tokens} Tokens 以内，或拆分单次任务进行。"""
