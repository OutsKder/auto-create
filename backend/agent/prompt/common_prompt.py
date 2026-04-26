# 各个 Agent 通用的基础回复及重试纠错 Prompt

# 当 JSON 输出结构解析失败时的系统 Prompt
JSON_RETRY_SYSTEM_PROMPT = """你是一个严格的JSON纠错助手。请修复以下输出，使其完全符合给定的JSON Schema。不要输出任何多余内容，只需输出合法的JSON。"""

# 当 JSON 输出结构解析失败时的用户纠正 Prompt
JSON_RETRY_HUMAN_PROMPT = """【原始预期格式】:
{format_instructions}

【错误的输出】:
{wrong_output}

【错误信息】:
{error_msg}

请直接输出修复后的JSON:"""
