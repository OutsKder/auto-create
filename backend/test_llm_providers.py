"""兼容入口：保留历史脚本路径，转发到 agent/tests。"""

try:
    from backend.agent.tests.test_llm_providers import (
        test_factory_create,
        test_direct_provider,
        test_factory_with_config,
        test_list_providers,
        test_provider_invoke,
    )
except ImportError:
    from agent.tests.test_llm_providers import (
        test_factory_create,
        test_direct_provider,
        test_factory_with_config,
        test_list_providers,
        test_provider_invoke,
    )

import os


if __name__ == "__main__":
    print("=" * 60)
    print("LLM 多服务商架构测试")
    print("=" * 60)

    try:
        test_factory_create()
        test_direct_provider()
        test_factory_with_config()
        test_list_providers()

        # 只有在有真实 API Key 时才测试调用
        if os.getenv("DOUBAO_API_KEY"):
            test_provider_invoke()
        else:
            print("\n\n⚠️  未设置 DOUBAO_API_KEY 环境变量，跳过真实调用测试")

        print("\n\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
