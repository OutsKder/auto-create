# -*- coding: utf-8 -*-
import codecs

CODE_TO_FIND = """if len(messages) > 8:
            messages = [messages[0], messages[1]] + messages[-6:]"""

CODE_TO_REPLACE = """# History Compression & Truncation combo
        current_len = sum(len(str(m.content)) for m in messages)
        
        # If the context is over ~3000 chars, perform summarization memory
        if len(messages) > 6 and current_len > 3000:
            history_to_compress = "\\n".join([f"{'User' if 'HumanMessage' in str(type(m)) else 'AI'}: {str(m.content)[:500]}" for m in messages[2:-4]])
            compress_prompt = f"请把以下先前的操作日志和AI行为压缩为最多300字的简明摘要（包含已尝试的动作、报错原因、现在的关键线索）：\\n\\n{history_to_compress}"
            
            yield '> 🗜️ **触发长期记忆提炼**：历史上下文过长，正在后台进行压缩，释放Token...\\n\\n'
            
            try:
                summary_res = await llm.ainvoke([SystemMessage(content="你是专门压缩AI操作日志以便释放Token空间的助手。"), HumanMessage(content=compress_prompt)])
                summary_msg = HumanMessage(content=f"【之前操作的历史摘要】：\\n{summary_res.content}")
                
                # Keep System(0), initial instruction(1), summary, and the latest 4 messages
                messages = [messages[0], messages[1], summary_msg] + messages[-4:]
            except Exception as compress_err:
                # If summarization fails, fallback to hard truncation
                messages = [messages[0], messages[1]] + messages[-6:]
                yield f'> ⚠️ **记忆提炼异常**：{str(compress_err)}。已直接截断最早记录...\\n\\n'
        
        # Fail-safe hard limit
        elif len(messages) > 8:
            messages = [messages[0], messages[1]] + messages[-6:]"""

def process_file(file_path):
    with codecs.open(file_path, 'r', 'utf-8') as f:
        content = f.read()

    content = content.replace(CODE_TO_FIND, CODE_TO_REPLACE)
    
    if "def run_command(self, command: str, timeout: int = 15) -> dict:" in content:
        content = content.replace("timeout: int = 15", "timeout: int = 300")

    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.write(content)

process_file('backend/coder_agent.py')
process_file('backend/test_agent.py')

print("Memory compression and timeout limits successfully applied.")
