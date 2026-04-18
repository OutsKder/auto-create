import os
import re
import json
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from coder_agent import FileSystemTools, API_KEY, BASE_URL, MODEL

async def stream_test_agent(req_id: str, req_data: dict, arch_context: str = ""):
    # 复用之前 coder_agent 建好的沙箱
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", f"target_project_{req_id}"))
    tools = FileSystemTools(workspace) # 如果目录没建好，它会静默创建空目录
    
    llm = ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.1, # QA needs low temp
    )
    
    sys_prompt = f"""你是一个高级资深自动化测试工程师 Agent (QA/SDET)。
你的任务是为已经生成的业务代码编写测试脚本，并运行测试来验证代码质量。
你的工作目录（沙箱）相对路径始终从当前文件夹开始，并且开发人员的代码已经存在于此。
你拥有两个能力：
1. `write_file_tool`: 创建/覆盖写入测试文件（例如 test_main.py）或者修复业务代码。
2. `run_command_tool`: 运行测试命令（例如 python test_main.py）

需求资料回顾：
需求：{req_data.get('title')}
背景：{req_data.get('background')}
目标：{req_data.get('goal')}
限制：{req_data.get('constraints')}

你必须：
通过返回以下 JSON 格式来使用工具（必须用 ```json 原样包裹，且只返回单个 JSON 块）：
```json
{{
    "action": "write_file_tool" 或 "run_command_tool" 或 "finish",
    "action_input": {{
        "relative_path": "相对路径，如果使用write_file_tool",
        "content": "写入的代码内容，如果使用write_file_tool",
        "command": "运行的测试命令，如果使用run_command_tool",
        "message": "最终交付的测试报告文本，如果是finish"
    }}
}}
```

**优先步骤：**
1. 先查看一下沙箱里有什么文件（可以使用命令 `ls` 或 `dir`，或直接凭直觉分析架构写测试）。
2. 写好测试文件。
3. 运行测试文件。
4. 如果测试没过，你有权限分析是业务代码错了还是测试代码错了，并再次使用 `write_file_tool` 去修改它们。
5. 最终必须通过测试。
"""
    
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content="请开始进行自动化测试用例编写与运行测试。如果不知道有哪些文件，可以先运行一次列出文件的命令。")
    ]
    
    yield '> 🎯 **Test Agent (QA 智能体) 启动**：接管环境空间 `' + workspace + '`\n\n'
    await asyncio.sleep(0.5)
    
    max_loops = 5
    for loop_idx in range(max_loops):
        yield f'> 🕵️ **QA 思考与探测中...** (第 {loop_idx + 1}/{max_loops} 轮)\n\n'
        
        # Invoke LLM
        response = await llm.ainvoke(messages)
        messages.append(response)
        
        text: str = response.content
        
        # Parse JSON
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if not json_match:
            try:
                data = json.loads(text)
            except:
                yield f'> ⚠️ **QA 误操作返回了非 JSON**：\n\n```text\n{text}\n```\n\n'
                messages.append(HumanMessage(content="你的回复格式错误，请只返回上述规定的 JSON。"))
                continue
        else:
            try:
                data = json.loads(json_match.group(1))
            except:
                messages.append(HumanMessage(content="JSON 格式解析失败。"))
                continue
        
        action = data.get("action")
        action_input = data.get("action_input", {})
        
        if action == "finish":
            yield f"### 🧪 自动化测试报告\n\n{action_input.get('message', '单元测试全部通过！')}\n\n"
            break
            
        elif action == "write_file_tool":
            filepath = action_input.get("relative_path")
            content = action_input.get("content")
            yield f'> 📝 **动作 [写测试用例/修Bug]**：正在写入 `{filepath}`...\n\n'
            try:
                res = tools.write_file(filepath, content)
                messages.append(HumanMessage(content=f"系统反馈 (write_file): {res}"))
                yield f'> ✅ **写入成功**\n\n'
            except Exception as e:
                messages.append(HumanMessage(content=f"系统反馈: Error -> {str(e)}"))
                yield f'> ❌ **写入失败**: {e}\n\n'
                
        elif action == "run_command_tool":
            cmd = action_input.get("command")
            yield f'> 🖥️ **动作 [执行测试命令]**：`{cmd}`\n\n'
            res = tools.run_command(cmd)
            
            if res["success"]:
                log = f"Success! STDOUT:\n{res['output']}"
                messages.append(HumanMessage(content=f"系统反馈 (run_command):\n{log}"))
                yield f'> ✅ **测试通过**：\n\n```text\n{res["output"]}\n```\n\n'
            else:
                log = f"Failed! STDOUT:\n{res['output']}\nSTDERR:\n{res['error']}"
                messages.append(HumanMessage(content=f"系统反馈 (run_command):\n{log}\n请分析并修复代码！"))
                yield f'> ❌ **测试报错**：捕获到异常日志，正在反馈给 QA 大脑寻找 Bug...\n\n```text\n{log}\n```\n\n'
        else:
            messages.append(HumanMessage(content=f"系统反馈: Unknown action '{action}'"))
    else:
        yield '> ⚠️ **警告**：测试智能体已达到最大重试次数（5次），由于一直未调通而在此中断。\n\n'