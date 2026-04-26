"""兼容入口：保留历史脚本路径，转发到 agent/tests。"""

try:
    from backend.agent.tests.test_requirement_analyst import test_requirement_analyst
except ImportError:
    from agent.tests.test_requirement_analyst import test_requirement_analyst


if __name__ == "__main__":
    test_requirement_analyst()
