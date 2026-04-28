import os
import sys
from pathlib import Path

# Compatibility demo moved from tests -> demos
agent_dir = Path(__file__).resolve().parent.parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from backend.agent.rag.context_manager import ContextManager
import time


def main():
    print("=" * 60)
    print("🚀 开始测试 FAST Repo-Map (AST原生提取) - demo")
    print("=" * 60)

    testcode_path = os.path.abspath(os.path.join(agent_dir, "..", "testcode"))

    cm = ContextManager(testcode_path)

    start_time = time.time()
    print("⏳ 正在一键扫描提取 AST 骨架...")

    # 使用 adapter 暴露的接口
    repo_skeleton = cm.generate_codebase_context({})

    end_time = time.time()

    print("\n" + "=" * 60)
    print(f"✅ 生成完成！耗时: {(end_time - start_time) * 1000:.2f} ms")
    print("-" * 60)
    print(repo_skeleton[:400])
    print("=" * 60)


if __name__ == "__main__":
    main()
