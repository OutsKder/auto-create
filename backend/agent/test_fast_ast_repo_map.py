import os
import sys
from pathlib import Path

# Add backend/agent/rag to sys.path
agent_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(agent_dir))

from rag.context_manager import ContextManager
import time


def main():
    print("=" * 60)
    print("🚀 开始测试 FAST Repo-Map (AST原生提取)")
    print("=" * 60)

    testcode_path = os.path.abspath(os.path.join(agent_dir, "../../testcode"))

    cm = ContextManager(testcode_path)

    start_time = time.time()
    print("⏳ 正在一键扫描提取 AST 骨架...")

    # 直接调用底层的快速分析，替代缓慢的 opencode _call_opencode_plan
    repo_skeleton = cm._generate_repo_map()

    end_time = time.time()

    print("\n" + "=" * 60)
    print(f"✅ 生成完成！耗时: {(end_time - start_time) * 1000:.2f} ms")
    print("-" * 60)
    print(repo_skeleton)
    print("=" * 60)


if __name__ == "__main__":
    main()
