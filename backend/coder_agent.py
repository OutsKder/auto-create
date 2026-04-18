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

    def run_command(self, command: str, timeout: int = 300) -> dict:
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

    def read_file(self, relative_path: str) -> str:
        """读取文件内容"""
        full_path = os.path.join(self.workspace, relative_path)
        assert os.path.abspath(full_path).startswith(os.path.abspath(self.workspace))
        if not os.path.exists(full_path):
            return f"Error: File {relative_path} does not exist."
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def list_dir(self, relative_path: str = ".") -> str:
        """列出目录下的文件"""
        full_path = os.path.join(self.workspace, relative_path)
        assert os.path.abspath(full_path).startswith(os.path.abspath(self.workspace))
        if not os.path.exists(full_path):
            return f"Error: Directory {relative_path} does not exist."
        return "\n".join(os.listdir(full_path))

async def stream_coder_agent(req_id: str, req_data: dict, arch_context: str = ""):
    # 建立沙箱
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", f"target_project_{req_id}"))
    tools = FileSystemTools(workspace)

    llm = ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.1,
        max_tokens=800
    )

    sys_prompt = f"""你是一个高级资深全栈工程师 Agent (架构与全栈实现)。
你的任务是根据给定的需求和架构文档，进行代码编写。对于复杂项目，你必须先规划后执行。

【核心工作流与要求】
1. **任务拆解与环境准备**：
   - 如果是一个可能需要第三方依赖的项目（如 Python requests, pandas 或是 Node.js 工程），你应当优先使用 `write_file_tool` 创建配置（`requirements.txt` 或 `package.json`）。
   - 然后使用 `run_command_tool` 安装依赖（比如 `pip install -r requirements.txt`，沙箱自带网络与包管理权限）。
   - 开始写逻辑代码前，可以先用注释的方式写一个内部 Plan 作为指引。
2. **循序渐进地构建与测试**：
   - 编码过程中，你可以通过编写代码和执行测试（`run_command_tool`）来逐步验证代码的正确性，并根据结果调整代码。
   - 当遇到上下文模糊时，通过 `list_dir_tool` 和 `read_file_tool` 搞清楚现有的文件协议和入口逻辑，不要瞎猜。

你的工作目录（沙箱）相对路径始终从当前文件夹开始。你拥有四个能力：
1. `write_file_tool`: 创建/覆盖写入文件
2. `run_command_tool`: 运行系统命令（你可以用它来安装依赖包、局部执行代码测试验证）
3. `read_file_tool`: 读取沙箱中已存在的文件
4. `list_dir_tool`: 列出沙箱目录内容

需求资料：
标题：{req_data.get('title')}
背景：{req_data.get('background')}
架构信息参考：
{arch_context}

你必须：
通过返回以下 JSON 格式来使用工具（必须用 ```json 原样包裹，且只返回单个 JSON 块）：
```json
{{
    "action": "write_file_tool" 或 "run_command_tool" 或 "read_file_tool" 或 "list_dir_tool" 或 "finish",
    "action_input": {{
        "relative_path": "相对路径，如果使用需要路径的工具",
        "content": "写入的代码内容，如果使用write_file_tool",       
        "command": "运行的测试命令，如果使用run_command_tool",
        "message": "最终交付的文本，如果是finish"
    }}
}}
```

**每次只需返回一个 JSON，我会把执行结果返回给你。如果遇到报错或者不符合预期的结果，仔细分析日志，修改代码再测试，直到成功。**

**最后交付任务 (finish)：**
当确认代码开发完毕并在沙箱中成功运行后，你必须调用 `finish` 动作，并在 `message` 字段中根据你的执行过程输出一份《编码实现执行总结报告》（Markdown格式）。报告应详细包含：
1. 编码实现是否全部完成及总结
2. 主要实现的功能清单与边界处理
3. 实际生成并落盘的文件列表 (File Tree)
4. 沙箱执行与边写边测的自我验证情况概述
※ 注意：由于嵌套在 JSON 的 `message` 中，请确保换行使用标准的 `\\n` 转义。
"""

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content="请开始进行编码实现与边写边自测。")
    ]

    yield '> 🚀 **Coder Agent 启动**：环境隔离完毕，工作空间位于 `' + workspace + '`\n\n'
    await asyncio.sleep(0.5)

    import re

    def truncate(t: str, limit=500):
        if not t: return ""
        return t if len(t) < limit else t[:limit//2] + "\n...[内容过长已为您截断]...\n" + t[-limit//2:]

    max_loops = 50
    for loop_idx in range(max_loops):
        # 动态记忆压缩机制：将中间的历史总结为一段精简的记忆上下文
        if len(messages) > 6:
            yield f'> 🧹 **触发记忆压缩**：正在浓缩历史日志...\n\n'
            msgs_to_summarize = messages[2:-2]
            history_text = ""
            for m in msgs_to_summarize:
                # 只给模型少量的上下文
                c = m.content if len(m.content) < 800 else m.content[:800] + "...[截断]"
                history_text += c + "\n"
                
            summary_request = [
                SystemMessage(content="你是一个严谨的AI记忆压缩助手。请阅读以下Agent在沙箱中执行的操作记录，将其提炼为不超过300字的精华摘要。要求体现：做了什么动作、修改了哪些文件，当前还没解决的核心问题是什么。"),
                HumanMessage(content=f"【历史记录】\n{history_text}")
            ]
            
            summary_resp = await llm.ainvoke(summary_request)
            compressed_memory = f"【之前的操作摘要】\n{summary_resp.content}\n\n请继续完成任务。"
            
            # 使用开头的2条 + 摘要 + 最后的两轮对白 组合出最新的 messages 数组
            messages = [
                messages[0],
                messages[1],
                HumanMessage(content=compressed_memory),
                messages[-2],
                messages[-1]
            ]


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
                messages.append(HumanMessage(content="你的回复格式错误，请只返回规定的 JSON 块。"))
                continue
        else:
            try:
                data = json.loads(json_match.group(1))
            except:
                yield f'> ⚠️ **Agent 返回的 JSON 无法解析**：\n\n```text\n{text}\n```\n\n'
                messages.append(HumanMessage(content="JSON 格式解析失败。"))
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
                messages.append(HumanMessage(content=f"系统反馈: Error -> {str(e)}"))
                yield f'> ❌ **写入失败**: {e}\n\n'

        elif action == "run_command_tool":
            cmd = action_input.get("command")
            yield f'> 🖥️ **动作 [执行命令]**：`{cmd}`\n\n'
            res = tools.run_command(cmd)

            # 截断过长输出，防止 Token 撑爆
            pass

            safe_out = truncate(res['output'])
            safe_err = truncate(res['error'])

            if res["success"]:
                log = f"Success! STDOUT:\n{safe_out}"
                messages.append(HumanMessage(content=f"系统反馈 (run_command):\n{log}"))
                yield f'> ✅ **执行通过**：\n\n```text\n{safe_out}\n```\n\n'
            else:
                log = f"Failed! STDOUT:\n{safe_out}\nSTDERR:\n{safe_err}"
                messages.append(HumanMessage(content=f"系统反馈 (run_command):\n{log}\n请分析报错并使用 read_file_tool 查看堆栈中涉及的文件具体行号后，再尝试 write_file_tool 修复代码。不要盲目瞎猜问题。"))
                yield f'> ❌ **执行报错**：正在自愈修复...\n\n```text\n{log}\n```\n\n'
                
        elif action == "read_file_tool":
            filepath = action_input.get("relative_path", "")
            yield f'> 📖 **动作 [读文件]**：读取 `{filepath}`...\n\n'
            res = tools.read_file(filepath)
            safe_res = truncate(res, limit=800)
            messages.append(HumanMessage(content=f"系统反馈 (read_file):\n{safe_res}"))
            yield f'> ✅ **读取完成**\n\n'

        elif action == "list_dir_tool":
            dirpath = action_input.get("relative_path", ".")
            yield f'> 📂 **动作 [列出目录]**：`{dirpath}`\n\n'
            res = tools.list_dir(dirpath)
            messages.append(HumanMessage(content=f"系统反馈 (list_dir):\n{res}"))
            yield f'> ✅ **列表完成**\n\n'

        else:
            messages.append(HumanMessage(content=f"系统反馈: Unknown action '{action}'"))
            yield f'> ⚠️ **未知的动作**：`{action}`\n\n'

    else:
        yield '> ⚠️ **警告**：Coder Agent 已达到最大重试次数（50次），自动终止保护触发。\n\n'