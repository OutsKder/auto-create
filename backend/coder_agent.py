import os
import subprocess
import json
import asyncio
import shutil
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage, HumanMessage

API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"        
MODEL = "qwen3.5-27b"

class FileSystemTools:
    def __init__(self, workspace_path: str):
        self.workspace = workspace_path
        os.makedirs(self.workspace, exist_ok=True)

    def semantic_search(self, query: str, top_k: int = 5) -> str:
        """对整个目录空间的代码和文件进行语义搜索"""
        docs = []
        for root, _, files in os.walk(self.workspace):
            for file in files:
                if file.startswith('.') or 'venv' in root or file.endswith(('.pyc', '.png', '.jpg')): continue
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        rel_path = os.path.relpath(full_path, self.workspace)
                        # 简单的文本分块，切分为每段 1500 字符
                        chunks = [content[i:i+1500] for i in range(0, len(content), 1500)]
                        for idx, chunk in enumerate(chunks):
                            docs.append({"content": f"File [{rel_path}] Chunk {idx}:\n{chunk}", "metadata": {"source": rel_path}})
                except Exception:
                    pass
        
        if not docs:
            return "No readable files found in workspace for semantic search."
            
        embeddings = OpenAIEmbeddings(
            api_key=API_KEY,
            base_url=BASE_URL,
            model="qwen3-vl-embedding"
        )
        texts = [d["content"] for d in docs]
        metadatas = [d["metadata"] for d in docs]
        
        try:
            vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
            results = vectorstore.similarity_search(query, k=top_k)
            return "\n\n---\n\n".join([res.page_content for res in results])
        except Exception as e:
            return f"Error in semantic search: {str(e)}"

    def write_file(self, relative_path: str, content: str) -> str:
        """模型调用的专门写文件的函数"""
        full_path = os.path.join(self.workspace, relative_path)
        # 安全断言，防止逃逸计算
        assert os.path.abspath(full_path).startswith(os.path.abspath(self.workspace))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File {relative_path} written successfully."

    def replace_in_file(self, relative_path: str, old_str: str, new_str: str) -> str:
        """替换文件中的某一段文本，极大地节省token。传入需要替换的原字符串和新字符串。"""
        full_path = os.path.join(self.workspace, relative_path)
        assert os.path.abspath(full_path).startswith(os.path.abspath(self.workspace))
        if not os.path.exists(full_path):
            return f"Error: File {relative_path} does not exist."
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if old_str not in content:
            return "Error: Exact old_str not found in the file. Watch out for exact whitespace matching."
        content = content.replace(old_str, new_str)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File {relative_path} modified successfully with string replacement."

    def run_command(self, command: str, timeout: int = 15) -> dict:
        """在工作目录下执行短暂命令。限制了最长只能运行 15 秒防止一直卡住。"""
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
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "template_project"))
    
    # 每次都从模板项目复制一份骨架到沙箱中
    if not os.path.exists(workspace):
        if os.path.exists(template_dir):
            shutil.copytree(template_dir, workspace)
        else:
            os.makedirs(workspace, exist_ok=True)

    tools = FileSystemTools(workspace)

    llm = ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.1,
        max_tokens=8192
    )

    # 提取之前人类打回或留下的审核意见（支持接着直接写）
    feedback_note = ""
    stage_data = req_data.get("stages", {}).get("coding", {})
    if stage_data.get("human_note"):
        feedback_note = f"\n\n🚨 【重要！来自人类的最新打回/修改意见】\n{stage_data.get('human_note')}\n\n当前沙箱已经保存了你上一次写的代码，请基于上面的意见，使用搜索工具定位代码中的问题并直接往下修改功能（不要重新初始化脚手架）！"

    sys_prompt = f"""你是一个高级资深全栈工程师 Agent (架构与全栈实现)。
你的任务是根据给定的需求和架构文档，进行代码微调和二次开发。{feedback_note}

【核心工作流与要求 - 极大减少Token消耗策略】
1. **现有框架已准备就绪**：
   - 你的沙箱当前已一套预先写好极简前后的 **Template Project** 骨架！里面包含 `backend/main.py`（FastAPI完整逻辑）、`frontend/index.html`与`app.js`（已有列表渲染、交互逻辑）。如果是打回重做，它还包含你刚才修改过的进度！
   - **绝对不要从头开始写项目！绝对不要重新输出整个文件！**
   - 优先通过只改动几行代码来完成业务需求，极致复用现在的代码。
2. **任务执行策略**：
   - 先通过 `list_dir_tool` 并阅读 `README.md` 来掌握当前工程结构。
   - 不要大段地读取源文件，通过 `semantic_search_tool` 直接定位需要增加字段或路由的地方。
   - 直接用 `write_file_tool` 去补充修改必要的地方。如果是追加，可以直接覆盖或者用替换思维改写小部分。
3. **边改边测**：
   - 如果需要测试代码有没有语法错误，可以用 `run_command_tool` 运行（例如 `python -m py_compile backend/main.py`）。
   - ⚠️ **绝对禁止执行 `uvicorn main:app` 或 `npm run dev` 等会永远阻塞的持久化服务端命令！！这会导致整个流水线死锁卡住！** 只需要改完代码确保没有语法错误即可交付。

你的工作目录（沙箱）相对路径始终从当前文件夹开始。你拥有六个能力：
1. `write_file_tool`: 创建/覆盖整个文件 (消耗海量Token，仅创建新文件用！)
2. `replace_in_file_tool`: 局部替换文件特定段落(传递old_str和new_str)，精准高效省Token！
3. `run_command_tool`: 运行系统命令（你可以用它来安装依赖包、局部执行代码测试验证）
4. `read_file_tool`: 读取沙箱中已存在的文件
5. `list_dir_tool`: 列出沙箱目录内容
6. `semantic_search_tool`: (RAG查询) 对沙箱代码库与文档进行自然语言/语义检索，免去了全文读取的负担。推荐频繁使用！

需求资料：
标题：{req_data.get('title')}
背景：{req_data.get('background')}
架构信息参考：
{arch_context}

你必须：
通过返回以下 JSON 格式来使用工具（必须用 ```json 原样包裹，且只返回单个 JSON 块）：
```json
{{
    "action": "write_file_tool" 或 "replace_in_file_tool" 或 "run_command_tool" 或 "read_file_tool" 或 "list_dir_tool" 或 "semantic_search_tool" 或 "finish",
    "action_input": {{
        "relative_path": "相对路径，如果涉及到文件相关的操作",
        "content": "写入的代码内容，仅使用write_file_tool时",
        "old_str": "需要被替换的旧字符串内容(必须精确匹配连同空白)，仅使用replace_in_file_tool时",
        "new_str": "替换后的新代码段，仅使用replace_in_file_tool时",
        "command": "运行的测试命令，如果使用run_command_tool",
        "query": "你想检索的代码逻辑或自然语言描述，如果使用semantic_search_tool",
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
        HumanMessage(content="请开始进行编码实现。如果是打回任务，请先阅读最新打回意见，用 semantic_search_tool 找到问题并直接修复，边改边测。")
    ]

    yield '> 🚀 **Coder Agent 启动**：环境隔离完毕，工作空间位于 `' + workspace + '`\n\n'
    await asyncio.sleep(0.5)

    import re

    def truncate(t: str, limit=50000):
        if not t: return ""
        return t if len(t) < limit else t[:limit//2] + "\n...[内容过长已为您截断]...\n" + t[-limit//2:]

    max_loops = 20
    for loop_idx in range(max_loops):
        # 动态记忆压缩机制：将中间的历史总结为一段精简的记忆上下文
        if len(messages) > 15:
            yield f'> 🧹 **触发记忆压缩**：正在浓缩历史日志...\n\n'
            msgs_to_summarize = messages[2:-4]
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

            # 使用开头的2条 + 摘要 + 最后的四轮对白 组合出最新的 messages 数组
            messages = [
                messages[0],
                messages[1],
                HumanMessage(content=compressed_memory),
                messages[-4],
                messages[-3],
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
            yield f'> 📝 **动作 [写文件]**：正在向 `{filepath}` 写入全文...\n\n'
            try:
                res = tools.write_file(filepath, content)
                messages.append(HumanMessage(content=f"系统反馈 (write_file): {res}"))
                yield f'> ✅ **写入成功**\n\n'
            except Exception as e:
                messages.append(HumanMessage(content=f"系统反馈: Error -> {str(e)}"))
                yield f'> ❌ **写入失败**: {e}\n\n'

        elif action == "replace_in_file_tool":
            filepath = action_input.get("relative_path")
            old_str = action_input.get("old_str")
            new_str = action_input.get("new_str")
            yield f'> ✂️ **动作 [局部替换]**：正在修改 `{filepath}` ...\n\n'
            try:
                res = tools.replace_in_file(filepath, old_str, new_str)
                messages.append(HumanMessage(content=f"系统反馈 (replace_in_file): {res}"))
                yield f'> ✅ **替换结果**: {res}\n\n'
            except Exception as e:
                messages.append(HumanMessage(content=f"系统反馈: Error -> {str(e)}"))
                yield f'> ❌ **替换失败**: {e}\n\n'

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
            # 限制读取内容，以免浪费 Token。鼓励它用 semantic_search
            if len(res) > 8000:
                res = res[:8000] + "\n\n...[文件过长，截断了后续部分。请勿反复尝试直接读取整个大文件，必须改用 semantic_search_tool 进行精准检索！]..."
            
            messages.append(HumanMessage(content=f"系统反馈 (read_file):\n{res}"))

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
            yield f'> ✅ **RAG检索完成**，为你提供最精确的代码切片碎片！\n\n'

        else:
            messages.append(HumanMessage(content=f"系统反馈: Unknown action '{action}'"))
            yield f'> ⚠️ **未知的动作**：`{action}`\n\n'

    else:
        yield '> ⚠️ **警告**：Coder Agent 已达到最大重试次数（50次），自动终止保护触发。\n\n'