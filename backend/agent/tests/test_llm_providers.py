"""
LLM 多服务商架构测试

测试不同 Provider 的创建和调用
"""

import os

try:
    from backend.agent.llm import LLMFactory, LLMConfig
    from backend.agent.llm.providers import DoubaoProvider
except ImportError:
    from agent.llm import LLMFactory, LLMConfig
    from agent.llm.providers import DoubaoProvider


def test_factory_create():
    """测试工厂创建不同 Provider"""
    print("====== 测试 LLMFactory.create() ======\n")

    print("1. 创建 Doubao Provider...")
    doubao = LLMFactory.create("doubao")
    print(f"   ✅ 创建成功: {doubao}")
    print(f"   模型: {doubao.get_model_name()}")

    print("\n2. 创建 Qwen Provider...")
    qwen = LLMFactory.create("qwen")
    print(f"   ✅ 创建成功: {qwen}")
    print(f"   模型: {qwen.get_model_name()}")

    print("\n3. 创建 OpenAICompatible Provider...")
    openai = LLMFactory.create("openai")
    print(f"   ✅ 创建成功: {openai}")
    print(f"   模型: {openai.get_model_name()}")


def test_direct_provider():
    """测试直接创建 Provider"""
    print("\n\n====== 测试直接创建 Provider ======\n")

    print("1. 直接创建 DoubaoProvider...")
    doubao_config = LLMConfig(
        provider="doubao",
        model="doubao-pro-32k",
        api_key=os.getenv("DOUBAO_API_KEY"),
        temperature=0.7,
    )
    doubao = DoubaoProvider(config=doubao_config)
    print(f"   ✅ 创建成功: {doubao}")
    print(f"   配置: {doubao.get_config()}")


def test_provider_invoke():
    """测试 Provider 调用（需要真实 API Key）"""
    print("\n\n====== 测试 Provider 调用 ======\n")

    messages = [
        {"role": "system", "content": "你是一个专业的Python编程助手。"},
        {"role": "user", "content": "请用一句话介绍Python语言。"},
    ]

    print("1. 测试 Doubao Provider 调用...")
    try:
        doubao = DoubaoProvider()
        print(f"   Provider: {doubao}")

        response = doubao.invoke(messages)
        print("   ✅ 调用成功!")
        print(f"   模型: {response.get('model')}")
        print(f"   内容: {response.get('content', '')[:100]}...")
        print(f"   使用量: {response.get('usage')}")
    except Exception as e:
        print(f"   ❌ 调用失败: {e}")


def test_factory_with_config():
    """测试工厂 + 配置"""
    print("\n\n====== 测试工厂 + 配置 ======\n")

    print("1. 通过配置字典创建...")
    config_dict = {
        "provider": "doubao",
        "model": "doubao-pro-32k",
        "temperature": 0.8,
        "max_tokens": 2000,
    }
    llm = LLMFactory.create_from_config(config_dict)
    print(f"   ✅ 创建成功: {llm}")
    print(f"   模型: {llm.get_model_name()}")
    print(f"   温度: {llm.get_config().temperature}")


def test_list_providers():
    """测试列出所有 Provider"""
    print("\n\n====== 测试列出所有 Provider ======\n")
    providers = LLMFactory.list_providers()
    print(f"支持的 Provider 类型: {providers}")


if __name__ == "__main__":
    print("=" * 60)
    print("LLM 多服务商架构测试")
    print("=" * 60)

    try:
        test_factory_create()
        test_direct_provider()
        test_factory_with_config()
        test_list_providers()

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
