import sys

with open('backend/coder_agent.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add read_file and list_dir missing tools
tools_code = """        return f"File {relative_path} written successfully."

    def run_command(self, command: str, timeout: int = 15) -> dict:
        \"\"\"在工作目录下执行命令\"\"\"
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
        full_path = os.path.join(self.workspace, relative_path)
        assert os.path.abspath(full_path).startswith(os.path.abspath(self.workspace))
        if not os.path.exists(full_path):
            return f"Error: File {relative_path} does not exist."
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def list_dir(self, relative_path: str = ".") -> str:
        full_path = os.path.join(self.workspace, relative_path)
        assert os.path.abspath(full_path).startswith(os.path.abspath(self.workspace))
        if not os.path.exists(full_path):
            return f"Error: Directory {relative_path} does not exist."
        return "\\n".join(os.listdir(full_path))"""
        
text = text.replace('        return f"File {relative_path} written successfully."\n\n    def run_command(self, command: str, timeout: int = 15) -> dict:', tools_code.split('def run_command')[0] + 'def run_command')

# 2. Update the system prompt
old_prompt = """1. `write_file_tool`: 创建/覆盖写入文件
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
        "command": "运行的命令，如果使用run_command_tool","""

new_prompt = """在编码过程中，你可以通过编写代码和执行小测试来逐步验证代码的正确性，根据结果调整代码。
1. `write_file_tool`: 创建/覆盖写入文件
2. `run_command_tool`: 运行测试命令（随时局部测试你写的代码运行是否正常）
3. `read_file_tool`: 读取沙箱中已存在的文件
4. `list_dir_tool`: 列出沙箱目录内容

需求：{req_data.get('title')}
背景：{req_data.get('background')}
架构信息参考：
{arch_context}

你必须：
通过返回以下 JSON 格式来使用工具（必须用 ```json 原样包裹，且只返回单个 JSON 块）：
```json
{{
    "action": "write_file_tool" 或 "run_command_tool" 或 "read_file_tool" 或 "list_dir_tool" 或 "finish",
    "action_input": {{
        "relative_path": "相对路径，如果使用write/read文件或list目录",
        "content": "写入的代码内容，如果使用write_file_tool",       
        "command": "运行的测试命令，如果使用run_command_tool","""

text = text.replace(old_prompt, new_prompt)

# 3. Update max loops
text = text.replace('max_loops = 5', 'max_loops = 50')

# 4. Add conditions for new tools
old_action_else = """        else:
            messages.append(HumanMessage(content=f"系统反馈: Unknown action '{action}'"))"""

new_action_else = """        elif action == "read_file_tool":
            filepath = action_input.get("relative_path", "")
            yield f'> 📖 **动作 [读文件]**：读取 `{filepath}`...\\n\\n'
            res = tools.read_file(filepath)
            messages.append(HumanMessage(content=f"系统反馈 (read_file):\\n{res}"))
            yield f'> ✅ **读取完成**\\n\\n'

        elif action == "list_dir_tool":
            dirpath = action_input.get("relative_path", ".")
            yield f'> 📂 **动作 [列出目录]**：`{dirpath}`\\n\\n'
            res = tools.list_dir(dirpath)
            messages.append(HumanMessage(content=f"系统反馈 (list_dir):\\n{res}"))
            yield f'> ✅ **列表完成**\\n\\n'
            
        else:
            messages.append(HumanMessage(content=f"系统反馈: Unknown action '{action}'"))"""

text = text.replace(old_action_else, new_action_else)

with open('backend/coder_agent_new.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated coder agent")

# -- Now test agent ---

with open('backend/test_agent.py', 'r', encoding='utf-8') as f:
    text_test = f.read()

old_test_prompt = """浣犳嫢鏈変袱涓兘力：
1. `write_file_tool`: 鍒涘缓/瑕嗙洊鍐欏叆娴嬭瘯鏂囦欢锛堜緥濡?test_main.py锛夋垨鑰呬慨澶嶄笟鍔′唬鐮併€?
2. `run_command_tool`: 杩愯娴嬭瘯鍛戒护锛堜緥濡?python test_main.py锛?"""
# Chinese garbled - I better use regex or simpler replace
