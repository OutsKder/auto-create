import os
import subprocess
import json
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

API_KEY = os.getenv("OPENAI_API_KEY", "key")
BASE_URL = os.getenv("OPENAI_BASE_URL", "http://47.123.4.240:11499/v1/")
MODEL = "Qwen2.5-Coder-32B-Instruct-GPTQ-Int4/"

class FileSystemTools:
    def __init__(self, workspace_path: str):
        self.workspace = workspace_path
        os.makedirs(self.workspace, exist_ok=True)

    def write_file(self, relative_path: str, content: str) -> str:
        """模型调用的专门写文件的函数"""
        full_path = os.path.join(self.workspace, relative_path)
        # 安全断言，防止逃逸计算
        assert os.path.abspath(full_path).startswith(os.path.abspath(self.workspace))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File {relative_path} written successfully."

    def run_command(self, command: str, timeout: int = 15) -> dict:
        """在工作目录下执行命令"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=self.workspace, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

async def stream_coder_agent(req_id: str, req_data: dict, arch_context: str = ""):
    # 建立沙箱
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", f"target_project_{req_id}"))
    tools = FileSystemTools(workspace)
    
    # 我们采用 Langchain Tools 机制
    from langchain_core.tools import tool
    
    llm = ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.1,
    )
    
    sys_prompt = f"""你是一个高级资深全栈工程师 Agent。
你的任务是根据给定的需求和架构文档，进行代码编写。
你的工作目录（沙箱）相对路径始终从当前文件夹开始。你拥有两个能力：
1. `write_file_tool`: 创建/覆盖写入文件
2. `run_command_tool`: 运行测试命令

需求：{req_data.get('title')}
背景：{req_data.get('background')}
架构信息参考：
{arch_context}

你必须：
通过返回以下 JSON 格式来使用工具（必须用 ```json 原样包裹，且只返回单个 JSON 块）：
```json
{{
    "action": "write_file_tool" 或 "run_command_tool" 或 "finish",
    "action_input": {{
        "relative_path": "相对路径，如果使用write_file_tool",
        "content": "写入的代码内容，如果使用write_file_tool",
        "command": "运行的命令，如果使用run_command_tool",
        "message": "最终交付的文本，如果是finish"
    }}
}}
```

**示例1：写入文件**
```json
{{
    "action": "write_file_tool",
    "action_input": {{
        "relative_path": "app.py",
        "content": "print('hello')"
    }}
}}
```

**示例2：运行命令**
```json
{{
    "action": "run_command_tool",
    "action_input": {{
        "command": "python app.py"
    }}
}}
```

**每次只需返回一个 JSON，我会把执行结果返回给你。如果遇到报错，仔细分析错误日志，再次触发 write_file_tool 修改文件。**

**最后交付任务 (finish)：**
当确认代码开发完毕并在沙箱中成功运行后，你必须调用 `finish` 动作，并在 `message` 字段中根据你的执行过程输出一份《编码实现执行总结报告》（Markdown格式）。报告应详细包含：
1. 编码实现是否全部完成及总结
2. 主要实现的功能清单与边界处理
3. 实际生成并落盘的文件列表 (File Tree)
4. 沙箱执行与自测的情况概述
※ 注意：由于嵌套在 JSON 的 `message` 中，请确保换行使用标准的 `\\n` 转义。
"""
    
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content="请开始进行编码实现与测试。")
    ]
    
    yield '> 🚀 **Coder Agent 启动**：环境隔离完毕，工作空间位于 `' + workspace + '`\n\n'
    await asyncio.sleep(0.5)
    
    import re

    max_loops = 5
    for loop_idx in range(max_loops):
        yield f'> 🧠 **Agent 思考中...** (第 {loop_idx + 1}/{max_loops} 轮)\n\n'
        
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
                yield f'> ⚠️ **Agent 意外返回了非 JSON 格式**：\n\n```text\n{text}\n```\n\n'
                messages.append(HumanMessage(content="你的回复格式错误，请只返回上述规定的 JSON，不要返回其他废话文字。"))
                continue
        else:
            try:
                data = json.loads(json_match.group(1))
            except:
                yield f'> ⚠️ **Agent 返回的 JSON 无法解析**：\n\n```text\n{text}\n```\n\n'
                messages.append(HumanMessage(content="JSON 格式解析失败，请检查语法并重新输出。"))
                continue
        
        action = data.get("action")
        action_input = data.get("action_input", {})
        
        if action == "finish":
            yield f"### ✅ 最终汇报\n\n{action_input.get('message', '执行完成')}\n\n"
            break
            
        elif action == "write_file_tool":
            filepath = action_input.get("relative_path")
            content = action_input.get("content")
            yield f'> 📝 **动作 [写文件]**：正在向 `{filepath}` 写入代码...\n\n'
            try:
                res = tools.write_file(filepath, content)
                messages.append(HumanMessage(content=f"系统反馈 (write_file): {res}"))
                yield f'> ✅ **写入成功**\n\n'
            except Exception as e:
                messages.append(HumanMessage(content=f"系统反馈 (write_file): Error -> {str(e)}"))
                yield f'> ❌ **写入失败**: {e}\n\n'
                
        elif action == "run_command_tool":
            cmd = action_input.get("command")
            yield f'> 🖥️ **动作 [执行命令]**：`{cmd}`\n\n'
            res = tools.run_command(cmd)
            
            if res["success"]:
                log = f"Success! STDOUT:\n{res['output']}"
                messages.append(HumanMessage(content=f"系统反馈 (run_command):\n{log}"))
                yield f'> ✅ **执行通过**：\n\n```text\n{res["output"]}\n```\n\n'
            else:
                log = f"Failed! STDOUT:\n{res['output']}\nSTDERR:\n{res['error']}"
                messages.append(HumanMessage(content=f"系统反馈 (run_command):\n{log}\n请分析报错并修复代码！"))
                yield f'> ❌ **执行报错**：捕获到异常日志，正在反馈给大脑进行自愈修复...\n\n```text\n{log}\n```\n\n'
        else:
            messages.append(HumanMessage(content=f"系统反馈: Unknown action '{action}'"))
            yield f'> ⚠️ **未知的动作**：`{action}`\n\n'

    else:
        yield '> ⚠️ **警告**：Coder Agent 已达到最大重试次数（5次），自动终止保护触发。\n\n'
