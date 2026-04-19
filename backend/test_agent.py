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
        max_tokens=8192
    )

    sys_prompt = f"""你是一个高级资深自动化测试工程师 Agent (QA/SDET)。
你的任务是为已经生成的业务代码编写测试脚本，并运行测试来验证代码质量。对于复杂项目，你可能需要自己梳理测试环境和架构。

【白盒测试与强力诊断】
1. **测试前环境检测**：
   - 优先使用 `list_dir_tool` 查看当前存在什么文件（如 `.py`、`package.json`）。
   - 如果开发遗漏了三方库，你有权限使用 `run_command_tool` 先行安装依赖包（如 `pip install pytest`）。
2. **源码级阅读 (White-box testing)**：
   - 如果不确切知道某个类名、模块如何引入，一定要使用 `read_file_tool` 打开源码阅读，绝不靠瞎猜写用例。
3. **精准报错自愈逻辑**：
   - 测试运行（`run_command_tool`）失败时，注意提取控制台打印出的报错堆栈。
   - 不要只依靠异常栈直接覆盖写入源文件。如有必要，通过 `read_file_tool` 查看报错涉及到的实际业务代码行逻辑，确认是逻辑错误还是你的测试写的不对。

你的工作目录（沙箱）相对路径始终从当前文件夹开始。你拥有五个能力：
1. `write_file_tool`: 创建/覆盖写入测试文件（或强行修复业务代码）。
2. `run_command_tool`: 运行依赖安装和测试脚本。
3. `read_file_tool`: 读取沙箱中的文件以进行代码诊断。
4. `list_dir_tool`: 探测沙箱目录的内容结构。
5. `semantic_search_tool`: (RAG查询) 对整个项目库进行语义检索，用于快速了解特定功能的代码细节，免去全文读取的负担。

需求资料回顾：
需求：{req_data.get('title')}
背景：{req_data.get('background')}
目标：{req_data.get('goal')}
限制：{req_data.get('constraints')}

你必须：
通过返回以下 JSON 格式来使用工具（必须用 ```json 原样包裹，且只返回单个 JSON 块）：
```json
{{
    "action": "write_file_tool" 或 "run_command_tool" 或 "read_file_tool" 或 "list_dir_tool" 或 "semantic_search_tool" 或 "finish",
    "action_input": {{
        "relative_path": "相对路径，如果使用需要路径的工具",
        "content": "写入的代码内容，如果使用write_file_tool",       
        "command": "运行的测试命令，如果使用run_command_tool",
        "query": "你想检索的功能细节或代码，如果使用semantic_search_tool",
        "test_passed": true 或 false, // 只有在finish时填写，表示最后到底是成功还是失败打回
        "message": "最终交付的测试报告文本，如果是finish"
    }}
}}
```

**优先步骤：**
1. 先查看一下沙箱里有什么文件（使用 `list_dir_tool`）。
2. 使用 `semantic_search_tool` 进行精确的代码或文档检索。
3. 若还需要整体脉络，可使用 `read_file_tool` 阅读。
4. 编写并运行测试文件。
5. 如果不通过，再次使用检索和代码读写能力修复！

**最后交付任务 (finish)：**
当测试全部通过，或者即使尝试修复仍旧存在难以解决的问题而不得不终止时，你必须调用 `finish` 动作，并在 `message` 字段中根据你的执行过程输出一份《自动化测试总结报告》（Markdown格式）。
如果测试一直失败，请在 test_passed 字段标记 false，以此来作为后期“打回改写”的凭证。
报告应详细包含：
1. 测试范围与方案概述（测试了哪些功能，设计了哪些边界/异常路径断言）。
2. 测试过程与结果分析（执行了什么命令，最初有没有报错？报错是否并如何被修复了？）。
3. 最终通过情况（是否有未通过的遗留问题？通过率等统计数据）。
4. 业务代码返修建议（若有未解Bug或代码缺陷，记录给打回修改的建议）。
※ 注意：由于嵌套在 JSON 的 `message` 中，请确保换行使用标准的 `\\n` 转义。
"""

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content="请开始进行自动化测试用例编写与运行测试。如果不清楚有哪些文件，请先采取列出目录及读取文件的动作。")
    ]

    yield '> 🎯 **Test Agent (QA 智能体) 启动**：接管环境空间 `' + workspace + '`\n\n'
    await asyncio.sleep(0.5)
    
    import re
    def truncate(t: str, limit=50000):
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
                messages.append(HumanMessage(content="你的回复格式错误，请只返回规定的 JSON 块。"))
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
            test_passed = action_input.get("test_passed", True)
            status_emoji = "✅全部通过" if test_passed else "❌测试不通过，已记录备案"
            yield f"### 📊 自动化测试报告 ({status_emoji})\n\n{action_input.get('message', '')}\n\n"
            # NOTE: 后期这里可以在 workflow 中获取这个信息来决定是否打回
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

            # 截断过长输出，防止 Token 撑爆
            def truncate(t: str, limit=50000):
                if not t: return ""
                return t if len(t) < limit else t[:limit//2] + "\n...[日志过长已截断]...\n" + t[-limit//2:]

            safe_out = truncate(res['output'])
            safe_err = truncate(res['error'])

            if res["success"]:
                log = f"Success! STDOUT:\n{safe_out}"
                messages.append(HumanMessage(content=f"系统反馈 (run_command):\n{log}"))
                yield f'> ✅ **测试通过**：\n\n```text\n{safe_out}\n```\n\n'
            else:
                log = f"Failed! STDOUT:\n{safe_out}\nSTDERR:\n{safe_err}"
                messages.append(HumanMessage(content=f"系统反馈 (run_command):\n{log}\n测试包含断言失败或其它报错，请利用 read_file_tool 读取报错提及的具体文件进行诊断，必要时使用 write_file_tool 修复原业务代码！"))
                yield f'> ❌ **测试报错**：捕获到异常日志，正在反馈给 QA 大脑寻找 Bug...\n\n```text\n{log}\n```\n\n'

        elif action == "read_file_tool":
            filepath = action_input.get("relative_path", "")
            yield f'> 📖 **动作 [读文件]**：读取 `{filepath}`...\n\n'
            res = tools.read_file(filepath)
            safe_res = truncate(res, limit=100000)
            messages.append(HumanMessage(content=f"系统反馈 (read_file):\n{safe_res}"))
            yield f'> ✅ **读取完成**\n\n'

        elif action == "list_dir_tool":
            dirpath = action_input.get("relative_path", ".")
            yield f'> 📂 **动作 [列出目录]**：`{dirpath}`\n\n'
            res = tools.list_dir(dirpath)
            messages.append(HumanMessage(content=f"系统反馈 (list_dir):\n{res}"))
            yield f'> ✅ **列表完成**\n\n'

        elif action == "semantic_search_tool":
            query = action_input.get("query", "")
            yield f'> 🔍 **动作 [RAG代码检索]**：`{query}`...\n\n'
            res = tools.semantic_search(query)
            messages.append(HumanMessage(content=f"系统反馈 (semantic_search):\n{res}"))
            yield f'> ✅ **RAG检索完成**，为你提供最精确的代码碎片！\n\n'

        else:
            messages.append(HumanMessage(content=f"系统反馈: Unknown action '{action}'"))
            yield f'> ⚠️ **未知的动作**：`{action}`\n\n'

    else:
        yield '> ⚠️ **警告**：测试智能体已达到最大重试次数（50次），由于一直未调通而在此中断。\n\n'