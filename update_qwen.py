import os

files = ['backend/coder_agent.py', 'backend/test_agent.py']

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Base configs
    text = text.replace('os.getenv("OPENAI_API_KEY", "key")', 'os.getenv("DASHSCOPE_API_KEY")')
    text = text.replace('os.getenv("OPENAI_BASE_URL", "http://47.123.4.240:11499/v1/")', '"https://dashscope.aliyuncs.com/compatible-mode/v1"')
    text = text.replace('"Qwen2.5-Coder-32B-Instruct-GPTQ-Int4/"', '"qwen3.5-122b-a10b"')
    text = text.replace('"Qwen2.5-Coder-32B-Instruct-GPTQ-Int4"', '"qwen3.5-122b-a10b"')

    # Relax token limits
    text = text.replace('max_tokens=800', 'max_tokens=2048')  # Increase max tokens a bit
    text = text.replace('limit=500', 'limit=5000')   
    text = text.replace('limit=800', 'limit=8000')   
    text = text.replace('current_len > 1500', 'current_len > 15000')

    with open(file, 'w', encoding='utf-8') as f:
        f.write(text)
