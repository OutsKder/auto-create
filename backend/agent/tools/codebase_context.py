import os
import ast
import re
from typing import List, Dict, Any


class CodebaseContextTool:
    """
    提供结构化的代码库上下文提取工具。
    输入目标代码库地址，返回格式化的 codebase_context 字典。
    """

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    def extract_context(self, query: str = "") -> Dict[str, Any]:
        """
        提取结构化的代码库上下文。
        目前只实现了 Step 1 (毫秒级 AST Repo-Map 骨架提取)。
        """
        if not os.path.exists(self.workspace_root):
            return {
                "query": query,
                "repo_skeleton": "项目目录暂不存在，请基于需求从零开始设计架构。",
                "hot_files": [],
                "dependency_signatures": [],
            }

        return {
            "query": query,
            "repo_skeleton": self._generate_repo_map(),
            "hot_files": [],  # Step 2: 待实现的热点文件全量代码
            "dependency_signatures": [],  # Step 3: 待实现的依赖签名提取
        }

    def _generate_repo_map(self) -> str:
        """
        Step 1: 生成项目全景图谱 (Repo-map)
        使用 Python built-in AST 解析 Python 文件，提取类名与函数签名，其他文件使用正则或只显示名称
        """
        structure = []

        # 遍历工作目录下的所有文件和文件夹
        for root, dirs, files in os.walk(self.workspace_root):
            # 过滤不需要的目录
            dirs[:] = [
                d
                for d in dirs
                if d
                not in [
                    ".git",
                    "__pycache__",
                    "node_modules",
                    "venv",
                    "env",
                    ".opencode",
                ]
            ]

            # 处理每个文件
            for file in files:
                # 只处理支持的代码文件类型
                if not file.endswith(
                    (".py", ".js", ".ts", ".html", ".css", ".java", ".go")
                ):
                    continue

                # 构建文件的完整路径和相对路径
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_root)
                structure.append(f"- {rel_path}")

                try:
                    # 读取文件内容
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # 针对 Python 使用 AST 精确解析
                    if file.endswith(".py"):
                        tree = ast.parse(content)
                        for node in tree.body:
                            if isinstance(
                                node, (ast.FunctionDef, ast.AsyncFunctionDef)
                            ):
                                args = [a.arg for a in node.args.args]
                                structure.append(
                                    f"  - def {node.name}({', '.join(args)})"
                                )
                            elif isinstance(node, ast.ClassDef):
                                structure.append(f"  - class {node.name}:")
                                for class_node in node.body:
                                    if isinstance(
                                        class_node,
                                        (ast.FunctionDef, ast.AsyncFunctionDef),
                                    ):
                                        args = [a.arg for a in class_node.args.args]
                                        if args and args[0] == "self":
                                            args = args[1:]  # 隐藏掉 self 让签名更干净
                                        structure.append(
                                            f"    - def {class_node.name}({', '.join(args)})"
                                        )

                    # 针对 JS/TS 进行轻量正则提取
                    elif file.endswith((".js", ".ts")):
                        # 查找 class
                        classes = re.findall(r"class\s+([a-zA-Z0-9_]+)", content)
                        for c in classes:
                            structure.append(f"  - class {c}:")
                        # 查找 function
                        funcs = re.findall(
                            r"(?:function\s+|const\s+|let\s+|var\s+)([a-zA-Z0-9_]+)\s*(?:=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>|\([^)]*\)\s*\{)",
                            content,
                        )
                        for func in funcs:
                            structure.append(f"  - function {func}()")

                except Exception:
                    # 遇到语法错误/编码错误直接跳过内部提取
                    pass

        # 返回格式化的代码库全景图谱
        return "代码库全景图谱 (Fast AST Repo-Map):\n" + "\n".join(structure)
