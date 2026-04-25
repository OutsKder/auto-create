import os

files = ['backend/coder_agent.py', 'backend/test_agent.py']

for file in files:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            text = f.read()

        text = text.replace('max_tokens=2048', 'max_tokens=8192')
        text = text.replace('limit=5000', 'limit=50000')   
        text = text.replace('limit=8000', 'limit=100000')   
        text = text.replace('current_len > 15000', 'current_len > 200000')

        with open(file, 'w', encoding='utf-8') as f:
            f.write(text)
