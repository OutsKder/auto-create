# Coder Agent (编码智能体) 整体规划与实现方案

## 1. 核心设计理念 (Core Concepts)
对于真正的编码，大模型往往无法一次性写对（必定会有拼写错误、包找不到、端口冲突等）。因此，Coder Agent 的核心不是“一次写出完美代码”，而是**“像人类程序员一样工作”**，并具备**实时侦听和闭环自修复**的能力：
1. **沙箱式文件系统 (Workspace I/O)**：拥有在物理硬盘（如 `target_project/<req_id>`）读写文件的能力。
2. **终端执行能力 (Terminal Execution)**：拥有拉起子进程执行 `python`、`npm` 脚本的能力。
3. **实时侦听与自修复 (Self-Healing / Auto-Debug)**：捕获执行的终端输出（stdout）和报错信息（stderr）。一旦发生错误，Agent 会自动将错误日志发回给大模型：“你写的代码报了这个错，请修复代码”，直到运行成功或达到最大重试次数。
4. **过程透明化 (Observability)**：前端除了看最终代码，还要能像看直播一样实时看到 Agent 的思考过程与动作：“正在创建文件...”、“正在运行编译...”、“报错了，正在分析原因...”。

## 2. 整体业务架构分层
Coder Agent 独立于纯文本生成的 `chat_llm`模块，分为四个核心层：

* **接入层 (SSE Handler)**：复用现有的 FastAPI SSE 接口，针对编码阶段，增加结构化事件格式（不仅推送内容，还推送“动作状态”和“执行结果”）。
* **编排层 (Agent Loop)**：基于 `LangChain` 的 Tool Calling（函数调用）机制，或通过手写的 `asyncio` 控制流，管理最大 N 次的 `执行 -> 侦听报错 -> 修复代码` 重试逻辑。
* **工具层 (Toolkits)**：
    * `WriteFileTool`: 将代码片段按指定路径写入。
    * `ExecuteCommandTool`: 拉起子任务执行 Bash/CMD 命令，并收集超时/成功/报错的完整日志。
    * `ReadFileTool`: 回头读取项目已有文件进行上下文确认。
* **物理层 (Sandbox)**：限定工作目录在 `auto-create/target_project/{requirement_id}/` 下，防止危险命令越界。

## 3. 实时侦听与闭环自动修复机制 (核心工作流)
为了实现“实时侦听与测试报错修改”，Agent 内部运行一个 ReAct (Reasoning + Acting) 闭环：
1. **Agent 思考**：决定生成何种代码。
2. **Agent 动作**：调用 `WriteFileTool` 落盘代码；调用 `ExecuteCommandTool` 运行测试代码。
3. **环境反馈 (Observation)**：脚本执行后，系统捕获终端实际输出。
4. **自动评判与修正**：如果返回码不为 0 (执行失败) 或 stderr 中存在明显报错，将报错栈直接作为下一轮 `user` 提示词追加进上下文，强迫 LLM 分析错误并发出新的 `WriteFileTool` 指令修改文件，循环往复。

## 4. 前后端接口设计 (Interface Design)
后端的 SSE 数据流进行升级，传输 JSON，供前端动态渲染动作帧：

```json
// 类型1：动作状态（前端可展示为 Timeline 或终端 Loading 状态）
{"type": "action", "status": "running", "message": "正在创建目录 /target_project/demo-123", "data": null}
{"type": "action", "status": "running", "message": "正在写入文件 main.py...", "data": null}
{"type": "action", "status": "testing", "message": "正在执行测试 🏃 python main.py...", "data": null}
{"type": "action", "status": "error", "message": "运行出错，捕获到日志，正在呼叫大模型分析...", "data": "ModuleNotFoundError: No module named 'fastapi'"}

// 类型2：生成结果汇报（前端可展示在 Markdown 或代码阅读器中）
{"type": "code_chunk", "message": "", "data": "```python\nimport os\n..."}

// 类型3：完成状态
{"type": "done", "status": "success", "message": "编码与测试全部通过！", "data": null}
```

## 5. 后端核心模块实现规划 (Python 伪代码)

### 5.1 Tools（工具定义）
```python
import os
import subprocess

class FileSystemTools:
    def __init__(self, workspace_path: str):
        self.workspace = workspace_path
        os.makedirs(self.workspace, exist_ok=True)

    def write_file(self, relative_path: str, content: str) -> str:
        # 写文件逻辑...
        pass

    def run_command(self, command: str, timeout: int = 15) -> dict:
        """在工作目录下执行命令，用于实时侦听执行结果"""
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
```

### 5.2 Agent 侦听控制流
```python
import json

async def run_coder_agent_stream(req_id: str, arch_context: dict):
    # 初始化工具与上下文...
    
    max_loops = 5
    for i in range(max_loops):
        # 1. 调用 LLM (支持 Tool Calling)
        response = await llm.ainvoke(messages) 
        
        # ... 处理纯文本回答逻辑
        
        # 2. 拦截并执行 Tool
        for tool_call in response.tool_calls:
            if tool_call.name == "write_file":
                # 写入文件...
                
            elif tool_call.name == "run_command":
                yield json.dumps({"type": "action", "message": f"🖥️ 执行测试: {tool_call.args['command']}"})
                exec_result = tools.run_command(tool_call.args['command'])
                
                # 3. 核心：闭环侦听报错并送回 LLM
                if not exec_result["success"]:
                    yield json.dumps({"type": "action", "message": "❌ 运行报错，正在尝试修复..."})
                    result = f"Command failed!\nSTDOUT:\n{exec_result['output']}\nSTDERR:\n{exec_result['error']}\nPlease fix the code."
                else:
                    yield json.dumps({"type": "action", "message": "✅ 测试通过！"})
                    result = f"Success!\nSTDOUT:\n{exec_result['output']}"
            
            # 把环境的反馈追加到消息里，下一轮 LLM 就能收到报错并针对性修正
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
            
    else:
        yield json.dumps({"type": "error", "message": "超过最大自愈次数，自动挂起。"})
```

## 6. 接下来的实施步骤
1. **第一步（工具层）**：在 `backend` 创建 `coder_agent.py`，实现物理层安全的 `write_file` 和 `run_command` 工具并附带真实子进程调用。
2. **第二步（控制层）**：编写带 Tool Calling 的循环函数，确立“代码写入->自动终端测试->提取报错重试”的死循环（最多N次）机制。
3. **第三步（前后端通讯层）**：调整 `workflow.py` 路由，并修改前端 `app.js` 来解析带状态和命令行的 JSON 流，形成控制台风格的 UI 反馈。
