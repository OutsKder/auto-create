"""
RAG (Retrieval-Augmented Generation) & Context Manager

负责将大体积的代码库压缩为豆包等 LLM 模型易于吞吐的高价值上下文。
实现三层过滤机制：
1. Repo-Map (代码骨架/地图)
2. Semantic Indexing & LSP (语义相关文件 + 依赖分析)
3. Hot-File (全量提供高优文件)
"""

import os
import json
import subprocess
import ast
from typing import List, Dict, Any, Optional


class ContextManager:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    def generate_codebase_context(self, requirement_structured: Dict[str, Any]) -> str:
        """
        基于需求和代码库生成结构化的上下文压缩对象 (Context Synthesis)
        """
        if not os.path.exists(self.workspace_root):
            return json.dumps(
                {
                    "repo_skeleton": "项目路目录暂不存在，请基于需求从零生成全新架构。",
                    "hot_files": [],
                    "dependency_signatures": [],
                },
                ensure_ascii=False,
            )

        # Step 1: 生态骨架 Repo-Map (直接使用无网络阻塞的原生 AST 高速映射引擎)
        # 放弃使用缓慢的 opencode @plan
        repo_skeleton = self._generate_repo_map()

        # Step 2: 关联性推理 (语义过滤)
        hot_file_paths = self._select_hot_files(requirement_structured, repo_skeleton)

        # Step 3: 读取完整内容及依赖
        hot_files = []
        # 简单读取全量代码，限制单文件最大大小防爆
        for fpath in hot_file_paths:
            full_path = os.path.join(self.workspace_root, fpath)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    # 粗略防大文件
                    if len(content) > 20000:
                        content = content[:20000] + "\n...[Content Truncated]..."

                    hot_files.append({"path": fpath, "content": content})
                except Exception:
                    pass

        # 依赖签名：模拟 LSP 分析
        dependency_signatures = self._extract_dependencies(hot_file_paths)

        context_obj = {
            "repo_skeleton": repo_skeleton,
            "hot_files": hot_files,
            "dependency_signatures": dependency_signatures,
        }

        # 输出给 LLM 使用的格式化 JSON 字符串
        return json.dumps(context_obj, ensure_ascii=False, indent=2)

    def _call_opencode_plan(self, requirement_goal: str) -> str:
        """
        通过 subprocess 执行 OpenCode CLI 获取官方的 Plan 与代码地图
        """
        print("[RAG] 正在尝试唤起 OpenCode (@plan 引擎)...")

        # 强制指定 provider 和模型，不写死在依赖中，使用本地环境的 opencode
        command = [
            "opencode",
            "run",
            f"@plan 为实现以下需求大概要改哪些文件，给出纯文本规划：{requirement_goal}",
            "--dangerously-skip-permissions",
        ]

        try:
            # 明确指定使用 agent 目录下的 opencode.json 配置
            env = os.environ.copy()
            agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            opencode_config_path = os.path.join(agent_dir, "opencode.json")
            if os.path.exists(opencode_config_path):
                env["OPENCODE_CONFIG"] = opencode_config_path

            # 增加 timeout 防止卡死，Windows 环境下 npm 全局包通常是 .cmd，需开启 shell=True 或者使用完整扩展名
            is_windows = os.name == "nt"
            result = subprocess.run(
                command,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
                shell=is_windows,
                env=env,
            )
            planning_text = result.stdout
            print("[RAG] OpenCode @plan 规划拉取成功！")
            return f"OpenCode Planner 扫描结果:\n{planning_text}"

        except FileNotFoundError:
            print(
                "[RAG] 未找到 OpenCode 环境变量，将回退使用本地检索 (Tree-sitter 降级)。"
            )
            return self._generate_repo_map()
        except subprocess.TimeoutExpired:
            print("[RAG] OpenCode 规划执行超时，将回退使用本地检索。")
            return self._generate_repo_map()
        except subprocess.CalledProcessError as e:
            print(f"[RAG] 唤起 OpenCode 发生异常: {e.stderr}")
            print("[RAG] 将回退使用本地检索。")
            return self._generate_repo_map()

    def _generate_repo_map(self) -> str:
        """
        Step 1: 生成项目全景图谱 (Repo-map)
        使用 Python built-in AST 解析 Python 文件，提取类名与函数签名，其他文件使用正则或只显示名称
        """
        import re

        structure = []

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

            for file in files:
                if not file.endswith(
                    (".py", ".js", ".ts", ".html", ".css", ".java", ".go")
                ):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_root)
                structure.append(f"- {rel_path}")

                try:
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

        return "代码库全景图谱 (Fast AST Repo-Map):\n" + "\n".join(structure)

    def _select_hot_files(
        self, requirement: Dict[str, Any], repo_map: str
    ) -> List[str]:
        """
        Step 2: 找到最热的文件(Hot-files)
        实际应该通过 向量数据库(RAG) + 豆包大模型预过滤 (Long-Context Ranking)。
        这里先用启发式简单匹配功能相关文件。
        """
        # 注意：此处你可以使用 self.llm 让豆包根据 requirement 帮我们从 repo_map 中挑选路径
        # 为了演示脱离副作用，暂时用简单的关键字匹配，可以接入 OpenCode 的 RAG API
        import random

        # 解析全部文件列表
        all_files = []
        for line in repo_map.split("\n"):
            if line.startswith("- "):
                all_files.append(line.split(" ")[1])

        # 简单启发式寻找 main, app, config
        hot_files = []
        for f in all_files:
            if "main" in f or "app" in f or "index" in f:
                hot_files.append(f)

        # 如果没有找到热门的，就随便取前 3 个防空
        if not hot_files and all_files:
            hot_files = all_files[:3]

        return hot_files[:5]  # 最多返回 5 个热点文件

    def _extract_dependencies(self, hot_files: List[str]) -> List[str]:
        """
        Step 3: 获取依赖文件签名
        实际应通过 LSP 或 AST 解析
        """
        return [
            f"{hot_file}: 存在隐式的 Import 类引入关联..." for hot_file in hot_files
        ]
