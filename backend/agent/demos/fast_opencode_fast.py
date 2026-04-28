import os
import subprocess
from pathlib import Path

# Demo for quick OpenCode invocation moved from tests -> demos
agent_dir = Path(__file__).resolve().parent.parent


def test_fast_opencode():
    print("🚀 快速测试 OpenCode (不解析项目，只做基础问答) - demo")

    command = [
        "opencode",
        "run",
        "请输出一句：'你好，OpenCode调用成功！'，不要输出其他任何内容。",
        "--dangerously-skip-permissions",
    ]

    env = os.environ.copy()
    opencode_config_path = os.path.join(agent_dir, "opencode.json")

    if os.path.exists(opencode_config_path):
        env["OPENCODE_CONFIG"] = opencode_config_path
        print(f"✅ 已挂载环境配置: {opencode_config_path}")
    else:
        print(f"❌ 警告: 未找到配置 {opencode_config_path}")

    print("⏳ 等待大模型网络响应中...")

    try:
        is_windows = os.name == "nt"
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
            shell=is_windows,
            env=env,
        )
        print("\n" + "=" * 50)
        print("🎯 OpenCode 成功返回:")
        print("-" * 50)
        print(result.stdout.strip())
        print("=" * 50)

        if result.stderr.strip():
            print("\n⚠ 提示信息 (stderr):")
            print(result.stderr.strip())

    except subprocess.CalledProcessError as e:
        print("\n❌ 调用失败！")
        print("错误输出:", e.stderr)
    except subprocess.TimeoutExpired:
        print("\n❌ 请求超时，可能是网络问题或者大模型 API 响应过慢。")


if __name__ == "__main__":
    test_fast_opencode()
