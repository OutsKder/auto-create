with open('backend/workflow.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 强制禁用 mock 路径
text = text.replace('        for keyword, paths in self.mocks.get("golden_paths", {}).items():', '        for keyword, paths in {}.items(): # Disabled bypass')

with open('backend/workflow.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Mock disabled.")