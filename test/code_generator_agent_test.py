import os
import sys
import json

# Ensure repo root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.agent.llm.config import load_config
from backend.agent.llm.factory import LLMFactory
from backend.agent.codegen.code_generator import CodeGeneratorAgent


def main():
    input_path = os.path.join(
        os.path.dirname(__file__), "code_generator_agent_input.json"
    )
    output_path = os.path.join(
        os.path.dirname(__file__), "code_generator_agent_output.json"
    )

    with open(input_path, "r", encoding="utf-8") as f:
        context = json.load(f)

    provider = os.environ.get("TEST_LLM_PROVIDER", "doubao")
    print(f"Using LLM provider: {provider}")

    llm_config = load_config(provider)
    if not getattr(llm_config, "api_key", None):
        raise RuntimeError(
            "LLM api_key not found. Set API key via config/llm.yaml or environment variables."
        )

    llm = LLMFactory.create(llm_config.provider, config=llm_config)
    repo_root = context.get("codebase", {}).get("repo_path")
    if not repo_root:
        raise RuntimeError("codebase.repo_path is required for CodeGeneratorAgent")

    agent = CodeGeneratorAgent(llm_provider=llm, repo_root=repo_root)

    print("Invoking CodeGeneratorAgent agent...")
    result = agent.execute(context)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Output written to {output_path}")


if __name__ == "__main__":
    main()
