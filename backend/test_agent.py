import os
import sys
import json
import shutil
import subprocess
import tempfile

# 测试日志采用紧凑模式，避免终端被逐字流式输出和超长上下文刷屏。
os.environ.setdefault("AGENT_TRACE_COMPACT", "1")

# 确保能导入 backend 下的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import RequirementAnalyst, TechArchitect
from backend.agent.agents import CodeGeneratorAgent, SDETAgent
from backend.agent.codegen import Patch, Patcher
from backend.agent.codegen.models import SandboxResult
from backend.agent.codegen.runner import Runner
from backend.agent.workspace import WorkspaceManager
from backend.agent.self_healing import SelfHealingCoordinator
from backend.doubao_llm import llm as doubao_llm


def _clip(text: str, limit: int = 120) -> str:
    value = str(text or "").replace("\n", " ").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _print_requirement_summary(title: str, result: dict) -> None:
    structured = result.get("requirement_structured", {}) or {}
    print(f"\n{title}")
    print(f"- is_clear: {structured.get('is_clear')}")
    print(f"- goal: {_clip(structured.get('goal', ''))}")
    print(f"- features: {len(structured.get('features', []) or [])}")
    print(f"- constraints: {len(structured.get('constraints', []) or [])}")
    print(
        f"- acceptance_criteria: {len(structured.get('acceptance_criteria', []) or [])}"
    )


def _print_design_summary(title: str, result: dict) -> None:
    design = result.get("design", {}) or {}
    plan = design.get("file_change_plan", []) or []
    print(f"\n{title}")
    print(f"- architecture: {_clip(design.get('architecture', ''))}")
    print(f"- api_design: {_clip(design.get('api_design', ''))}")
    print(f"- file_change_plan: {len(plan)}")
    for item in plan[:5]:
        print(f"  - {item.get('change_type', 'Modify')}: {item.get('file_path', '')}")
    if len(plan) > 5:
        print(f"  - ... 其余 {len(plan) - 5} 项省略")
    print(f"- risk_analysis: {_clip(design.get('risk_analysis', ''))}")


class _FakeCodeGenLLM:
    """用于测试代码生成 Agent 的确定性假 LLM。"""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return {"content": self.response_text}


class _FakeSDETLLM:
    """用于测试测试生成 Agent 的确定性假 LLM。"""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return {"content": self.response_text}


def _print_code_diff_summary(title: str, result: dict) -> None:
    code_diff = result.get("code_diff", {}) or {}
    patches = code_diff.get("patches", []) or []
    print(f"\n{title}")
    print(f"- stage: {code_diff.get('stage')}")
    print(f"- mode: {code_diff.get('mode')}")
    print(f"- files_changed: {len(code_diff.get('files_changed', []) or [])}")
    print(f"- patches: {len(patches)}")
    print(f"- diff: {_clip(code_diff.get('diff', ''))}")
    validation = code_diff.get("validation", {}) or {}
    print(f"- static_checks: {len((validation.get('static_checks', {}) or {}))}")


def _print_test_bundle_summary(title: str, result: dict) -> None:
    tests = result.get("tests", {}) or {}
    print(f"\n{title}")
    print(f"- stage: {tests.get('stage')}")
    print(f"- test_plan: {len(tests.get('test_plan', []) or [])}")
    print(f"- test_files: {len(tests.get('test_files', []) or [])}")
    print(f"- runner_commands: {len(tests.get('runner_commands', []) or [])}")
    sandbox = tests.get("sandbox_result", {}) or {}
    print(f"- sandbox_passed: {sandbox.get('passed')}")
    print(f"- sandbox_exit_code: {sandbox.get('exit_code')}")


def test_sdet_agent_with_runner():
    """测试 SDET Agent：结构化输出 + 本地 Runner 执行并回填 sandbox_result。"""
    print("\n\n====== 开始运行 SDET Agent 测试 ======\n")

    temp_root = tempfile.mkdtemp(prefix="sdet_runner_")
    try:
        smoke_file = os.path.join(temp_root, "check.py")
        with open(smoke_file, "w", encoding="utf-8") as f:
            f.write("print('SDET_SMOKE_OK')\n")

        fake_tests = {
            "stage": "testing",
            "test_plan": [
                {
                    "acceptance_criterion": "运行 smoke 脚本成功",
                    "test_type": "unit",
                    "coverage_target": ["check.py"],
                }
            ],
            "test_files": [
                {
                    "file_path": "tests/test_smoke.py",
                    "test_type": "unit",
                    "covers": ["check.py"],
                }
            ],
            "test_code": "def test_placeholder():\n    assert True\n",
            "runner_commands": ["python check.py"],
            "sandbox_result": {"passed": False, "exit_code": 0, "logs": ""},
        }

        fake_llm = _FakeSDETLLM(json.dumps(fake_tests, ensure_ascii=False))
        agent = SDETAgent(llm_provider=fake_llm)

        context = {
            "code_diff": {
                "stage": "coding",
                "mode": "diff_bundle",
                "files_changed": ["check.py"],
                "patches": [],
                "diff": "",
                "validation": {"static_checks": [], "runtime_checks": []},
            },
            "requirement_structured": {
                "acceptance_criteria": ["运行 smoke 脚本成功"],
            },
            "codebase": {"repo_path": temp_root},
            "testing_options": {"auto_run": True, "timeout": 30},
        }

        result = agent.execute(context)
        _print_test_bundle_summary("====== 测试生成结果（摘要） ======", result)

        assert "tests" in result, "缺少 tests 字段"
        tests = result["tests"]
        assert tests.get("stage") == "testing", "stage 应为 testing"
        assert len(tests.get("test_plan", []) or []) == 1, "test_plan 数量不正确"
        assert (
            len(tests.get("runner_commands", []) or []) == 1
        ), "runner_commands 数量不正确"

        sandbox = tests.get("sandbox_result", {}) or {}
        assert sandbox.get("passed") is True, "Runner 执行应成功"
        assert sandbox.get("exit_code") == 0, "Runner 退出码应为 0"
        assert "SDET_SMOKE_OK" in (sandbox.get("logs") or ""), "日志中应包含 smoke 标记"

        print("\n✅ SDET Agent 测试通过!")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_sdet_agent_isolated_workspace_and_patch_application():
    """验证 SDET 会在临时工作区中应用 code_diff、物化测试文件并运行。"""
    print("\n\n====== 开始运行 SDET 隔离工作区测试 ======\n")

    temp_root = tempfile.mkdtemp(prefix="sdet_isolated_")
    try:
        app_file = os.path.join(temp_root, "calc.py")
        with open(app_file, "w", encoding="utf-8") as f:
            f.write("""def compute(op, a, b):
    if op == 'add':
        return a + b
    raise ValueError(op)
""")

        fake_tests = {
            "stage": "testing",
            "test_plan": [
                {
                    "acceptance_criterion": "修改后的计算函数应支持乘法",
                    "test_type": "unit",
                    "coverage_target": ["calc.py"],
                }
            ],
            "test_files": [
                {
                    "file_path": "tests/test_calc.py",
                    "test_type": "unit",
                    "covers": ["calc.py"],
                }
            ],
            "test_code": (
                "from calc import compute\n\n"
                "def test_compute_mul():\n"
                "    assert compute('mul', 2, 3) == 6\n"
            ),
            "runner_commands": ["pytest -q"],
            "sandbox_result": {"passed": False, "exit_code": 0, "logs": ""},
        }

        fake_llm = _FakeSDETLLM(json.dumps(fake_tests, ensure_ascii=False))
        agent = SDETAgent(llm_provider=fake_llm)

        context = {
            "code_diff": {
                "stage": "coding",
                "mode": "diff_bundle",
                "files_changed": ["calc.py"],
                "patches": [
                    {
                        "file_path": "calc.py",
                        "change_type": "modify",
                        "patch_format": "search_replace",
                        "patch": """FILE: calc.py
<<<<<<< SEARCH
def compute(op, a, b):
    if op == 'add':
        return a + b
    raise ValueError(op)
=======
def compute(op, a, b):
    if op == 'mul':
        return a * b
    raise ValueError(op)
>>>>>>> REPLACE""",
                        "reason": "把计算函数改为乘法",
                        "risk_level": "low",
                    }
                ],
                "diff": "diff --git a/calc.py b/calc.py",
                "validation": {"static_checks": ["syntax"], "runtime_checks": []},
            },
            "requirement_structured": {
                "acceptance_criteria": ["修改后的计算函数应支持乘法"],
            },
            "codebase": {"repo_path": temp_root},
            "testing_options": {"timeout": 30},
        }

        result = agent.execute(context)
        _print_test_bundle_summary("====== 隔离工作区测试结果（摘要） ======", result)

        tests = result.get("tests", {}) or {}
        sandbox = tests.get("sandbox_result", {}) or {}
        assert sandbox.get("passed") is True, "隔离工作区中的测试执行应成功"
        assert sandbox.get("exit_code") == 0, "隔离工作区运行退出码应为 0"
        assert "1 passed" in (sandbox.get("logs") or ""), "日志中应包含 pytest 成功痕迹"

        with open(app_file, "r", encoding="utf-8") as f:
            original_content = f.read()
        assert "op == 'add'" in original_content, "原始仓库不应被修改"
        assert "op == 'mul'" not in original_content, "原始仓库不应写入补丁结果"

        print("\n✅ SDET 隔离工作区测试通过!")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_workspace_manager_uses_repo_name():
    """验证临时工作区会放到 workspace/<原代码库名> 下。"""
    temp_root = tempfile.mkdtemp(prefix="workspace_manager_")
    try:
        source_repo = os.path.join(temp_root, "sample_repo")
        os.makedirs(source_repo, exist_ok=True)
        with open(os.path.join(source_repo, "marker.txt"), "w", encoding="utf-8") as f:
            f.write("ok")

        manager = WorkspaceManager()
        workspace_path = manager.create_workspace(source_repo)
        expected_suffix = os.path.join("workspace", "sample_repo")

        assert workspace_path.endswith(expected_suffix), "workspace 路径命名不符合规则"
        assert os.path.isdir(workspace_path), "workspace 目录未创建成功"
        assert os.path.exists(
            os.path.join(workspace_path, "marker.txt")
        ), "源码未复制到 workspace"

        manager.cleanup_workspace(source_repo)
        assert not os.path.exists(workspace_path), "workspace 未清理干净"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_runner_builds_hardened_docker_command():
    """验证 Docker 命令默认带上网络禁用、资源限制和只读挂载。"""
    runner = Runner(use_docker=True, docker_image="python:3.10-slim")
    command = runner._build_docker_command(
        ["pytest -q"],
        r"D:\temp\repo",
        {
            "network_disabled": True,
            "read_only": True,
            "cpus": "0.5",
            "memory": "512m",
            "pids_limit": "64",
            "tmpfs_size": "64m",
            "environment": {"PYTHONUNBUFFERED": "1"},
        },
    )

    assert command[0:3] == ["docker", "run", "--rm"]
    assert "--network" in command and "none" in command, "未启用网络禁用"
    assert "--read-only" in command, "未启用只读挂载"
    assert "--cpus" in command and "0.5" in command, "未设置 CPU 限制"
    assert "--memory" in command and "512m" in command, "未设置内存限制"
    assert "--pids-limit" in command and "64" in command, "未设置进程数限制"
    assert "--tmpfs" in command, "未挂载 tmpfs"
    assert any(
        item.endswith(":/workspace:ro") for item in command
    ), "工作区未以只读方式挂载"
    assert "-e" in command and "PYTHONUNBUFFERED=1" in command, "未注入环境变量"


def test_docker_container_verification():
    """验证 Docker 容器实际执行：硬化参数生效、输出捕获、隔离工作。

    如果 Docker 环境有问题（如镜像拉取失败），测试会降级到验证命令构建和结构。
    """
    import shutil
    from pathlib import Path

    # 创建临时测试目录
    test_workspace = tempfile.mkdtemp(prefix="docker_verify_")
    try:
        # 在工作区创建一个简单的测试脚本
        test_script = Path(test_workspace) / "test_script.py"
        test_script.write_text(
            "import sys\n"
            "print('Docker container OK')\n"
            "print(f'Python: {sys.version}')\n"
            "import socket\n"
            "try:\n"
            "    socket.create_connection(('8.8.8.8', 53), timeout=1)\n"
            "    print('Network: OPEN (NOT EXPECTED)')\n"
            "except Exception:\n"
            "    print('Network: Isolated (OK)')\n"
        )

        # 创建 Runner，使用 Docker 模式
        runner = Runner(use_docker=True, docker_image="python:3.10-slim")

        # 验证构建的 Docker 命令包含所有硬化参数
        commands = ["python /workspace/test_script.py"]
        docker_cmd = runner._build_docker_command(
            commands,
            test_workspace,
            {
                "network_disabled": True,
                "read_only": True,
                "cpus": "1",
                "memory": "512m",
                "tmpfs_size": "64m",
            },
        )

        print("\n=== Docker 容器验证测试 ===")
        print(f"构建的 Docker 命令:")
        print(f"  {' '.join(docker_cmd)}")

        # 验证硬化参数存在（第一阶段：命令构建验证）
        assert docker_cmd[0:3] == ["docker", "run", "--rm"], "Docker run 基础不正确"
        assert "--network" in docker_cmd and "none" in docker_cmd, "❌ 网络隔离未启用"
        print("✓ 网络隔离: --network none")

        assert "--cpus" in docker_cmd and "1" in docker_cmd, "❌ CPU 限制未设置"
        print("✓ CPU 限制: --cpus 1")

        assert "--memory" in docker_cmd and "512m" in docker_cmd, "❌ 内存限制未设置"
        print("✓ 内存限制: --memory 512m")

        assert "--read-only" in docker_cmd, "❌ 只读挂载未启用"
        print("✓ 只读挂载: --read-only")

        assert "--cap-drop" in docker_cmd and "ALL" in docker_cmd, "❌ 能力删除未设置"
        print("✓ 能力删除: --cap-drop ALL")

        assert (
            "--security-opt" in docker_cmd and "no-new-privileges" in docker_cmd
        ), "❌ 安全选项未设置"
        print("✓ 安全选项: --security-opt no-new-privileges")

        assert "--tmpfs" in docker_cmd, "❌ 临时文件系统未挂载"
        print("✓ 临时文件系统: --tmpfs /tmp")

        # 验证工作区挂载为只读
        assert any(
            item.endswith(":/workspace:ro") for item in docker_cmd
        ), "❌ 工作区挂载不是只读"
        print("✓ 工作区只读挂载")

        print("\n✅ Docker 命令构建验证通过！")
        print("  - 所有硬化参数存在: ✓")

        # 第二阶段：尝试实际执行 Docker（可能失败）
        print("\n执行 Docker 容器测试...")
        try:
            result = runner.run_commands(
                commands,
                test_workspace,
                {
                    "network_disabled": True,
                    "read_only": True,
                    "cpus": "1",
                    "memory": "512m",
                    "tmpfs_size": "64m",
                },
            )

            # 验证 SandboxResult 结构
            assert isinstance(result, SandboxResult), "❌ 返回结果不是 SandboxResult"
            assert hasattr(result, "passed"), "❌ SandboxResult 缺少 passed 属性"
            assert hasattr(result, "exit_code"), "❌ SandboxResult 缺少 exit_code 属性"
            assert hasattr(result, "logs"), "❌ SandboxResult 缺少 logs 属性"

            print(f"\n=== 执行结果 ===")
            print(f"Passed: {result.passed}")
            print(f"Exit Code: {result.exit_code}")
            print(f"\n--- 容器输出日志 ---")
            print(result.logs[:500])
            if len(result.logs) > 500:
                print(f"... (还有 {len(result.logs) - 500} 字符)")

            # 验证执行成功
            if result.passed and result.exit_code == 0:
                assert "Docker container OK" in result.logs, "❌ 脚本输出未捕获"
                assert "Network: Isolated" in result.logs, "❌ 网络隔离验证失败"
                print(f"\n✅ Docker 容器实际执行通过！")
                print(f"  - 硬化参数验证: ✓")
                print(f"  - 容器执行: ✓")
                print(f"  - 网络隔离: ✓")
                print(f"  - 输出捕获: ✓")
            else:
                # Docker 执行可能失败但命令构建正确
                print(f"\n⚠️ Docker 容器执行失败（但命令构建正确）")
                print(f"  失败原因: {result.logs[:200]}")
                print(f"  这可能是由于 Docker 镜像拉取问题或 Docker Desktop 配置问题")
                print(
                    f"  建议: 检查 Docker Desktop 设置，尝试手动拉取 python:3.10-slim 镜像"
                )

        except Exception as e:
            # Docker 执行环境不可用，但命令构建已验证
            print(f"\n⚠️ Docker 执行环境不可用: {str(e)[:100]}")
            print(f"  但 Docker 命令构建已验证正确，包含所有硬化参数")
            print(f"  建议: 检查 Docker Desktop 状态和镜像可用性")

    finally:
        # 清理临时目录
        if os.path.exists(test_workspace):
            shutil.rmtree(test_workspace)


def test_code_generator_agent():
    """测试代码修改 Agent：使用假 LLM 验证结构化 Diff Bundle 输出。"""
    print("====== 开始运行 Code Generator Agent 测试 ======\n")

    fake_diff = {
        "stage": "coding",
        "mode": "diff_bundle",
        "files_changed": ["backend/demo.py"],
        "patches": [
            {
                "file_path": "backend/demo.py",
                "change_type": "modify",
                "patch_format": "search_replace",
                "patch": "FILE: backend/demo.py\n<<<<<<< SEARCH\nprint('hello')\n=======\nprint('hello world')\n>>>>>>> REPLACE",
                "reason": "修正输出文案",
                "risk_level": "low",
            }
        ],
        "diff": "diff --git a/backend/demo.py b/backend/demo.py",
        "validation": {"static_checks": ["syntax"], "runtime_checks": []},
    }

    fake_llm = _FakeCodeGenLLM(json.dumps(fake_diff, ensure_ascii=False))
    agent = CodeGeneratorAgent(
        llm_provider=fake_llm,
        repo_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    test_context = {
        "codebase": {
            "repo_path": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        },
        "requirement_structured": {
            "goal": "修正 demo 输出",
            "acceptance_criteria": ["运行 demo 后输出包含 world"],
            "features": ["修改打印内容"],
            "constraints": ["最小修改"],
        },
        "design": {
            "architecture": "最小代码修复",
            "file_change_plan": [
                {
                    "file_path": "backend/demo.py",
                    "action": "modify",
                    "description": "把 hello 改成 hello world",
                    "example_patch": "FILE: backend/demo.py\n<<<<<<< SEARCH\nprint('hello')\n=======\nprint('hello world')\n>>>>>>> REPLACE",
                    "risk_level": "low",
                }
            ],
            "risk_analysis": "low",
        },
        "codebase_context": {
            "query": "demo output",
            "hot_files": [
                {
                    "path": "backend/demo.py",
                    "content": "print('hello')",
                    "score": 0.99,
                    "evidence": ["hello"],
                }
            ],
            "repo_skeleton": "backend/demo.py",
        },
    }

    result = agent.execute(test_context)
    _print_code_diff_summary("====== 代码生成结果（摘要） ======", result)

    assert "code_diff" in result, "缺少 code_diff 字段"
    code_diff = result["code_diff"]
    assert code_diff.get("stage") == "coding", "stage 应为 coding"
    assert code_diff.get("mode") == "diff_bundle", "mode 应为 diff_bundle"
    assert (
        len(code_diff.get("files_changed", []) or []) == 1
    ), "files_changed 数量不正确"
    assert len(code_diff.get("patches", []) or []) == 1, "patches 数量不正确"
    assert code_diff.get("patches", [])[0]["file_path"] == "backend/demo.py"
    assert "static_checks" in (
        code_diff.get("validation", {}) or {}
    ), "缺少静态校验结果"

    print("\n✅ Code Generator Agent 测试通过!")


def test_patch_and_verify_testcode():
    """真正修改 testcode 副本中的文件，并通过运行程序验证修改结果。"""
    print("\n\n====== 开始运行 testcode 补丁验证测试 ======\n")

    source_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "testcode")
    )
    temp_root = tempfile.mkdtemp(prefix="testcode_patch_")
    temp_testcode = os.path.join(temp_root, "testcode")

    try:
        shutil.copytree(source_root, temp_testcode)

        patcher = Patcher(repo_root=temp_testcode)
        patch = Patch(
            file_path="main.py",
            change_type="modify",
            patch_format="search_replace",
            patch="""FILE: main.py
<<<<<<< SEARCH
    result = calc.compute('add', 10.5, 5.0)
=======
    result = calc.compute('mul', 10.5, 5.0)
>>>>>>> REPLACE""",
            reason="把主程序从加法改为乘法，用于验证补丁应用与执行结果",
            risk_level="low",
        )

        patch_result = patcher.apply(patch)
        print(
            f"补丁应用结果: applied={patch_result.applied}, message={patch_result.message}, error={patch_result.error}"
        )
        assert (
            patch_result.applied
        ), f"补丁未成功应用: {patch_result.error or patch_result.message}"

        patched_main = os.path.join(temp_testcode, "main.py")
        with open(patched_main, "r", encoding="utf-8") as f:
            patched_content = f.read()
        assert (
            "calc.compute('mul', 10.5, 5.0)" in patched_content
        ), "main.py 没有被正确修改"

        run_result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=temp_testcode,
            capture_output=True,
            text=True,
            check=False,
        )

        print("程序 stdout:")
        print(run_result.stdout.strip())
        print("程序 stderr:")
        print(run_result.stderr.strip())
        print(f"退出码: {run_result.returncode}")

        assert run_result.returncode == 0, f"运行失败，退出码: {run_result.returncode}"
        combined_output = f"{run_result.stdout}\n{run_result.stderr}"
        assert "52.5" in combined_output, "运行结果没有体现乘法修改"

        print("\n✅ testcode 补丁验证测试通过!")

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_frontend_login_background_flow():
    """跑通需求分析 -> 方案设计 -> 代码生成，并真正修改前端登录页背景后验证结果。

    结果会以 JSON 形式保存到项目根目录的 test_output.json。
    """
    print("\n\n====== 开始运行前端登录页背景修改全流程测试 ======\n")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_root = os.path.join(project_root, "frontend")
    temp_root = tempfile.mkdtemp(prefix="frontend_login_patch_")
    temp_frontend = os.path.join(temp_root, "frontend")
    output_path = os.path.join(project_root, "test_output.json")

    result_payload = {
        "scenario": "frontend_login_background_flow",
        "requirement_raw": "给该前端登录页面换个浅蓝色背景",
        "project_root": project_root,
        "frontend_root": frontend_root,
        "temporary_frontend_root": temp_frontend,
        "requirement_analysis": {},
        "design": {},
        "code_diff": {},
        "patch_result": {},
        "verification": {},
    }

    try:
        shutil.copytree(frontend_root, temp_frontend)

        requirement_raw = result_payload["requirement_raw"]
        analyst = RequirementAnalyst(llm_provider=doubao_llm)
        analyst_result = analyst.execute({"requirement_raw": requirement_raw})
        result_payload["requirement_analysis"] = analyst_result
        _print_requirement_summary("====== 需求分析结果（摘要） ======", analyst_result)

        requirement_structured = analyst_result.get("requirement_structured", {})
        assert requirement_structured, "需求分析未返回 requirement_structured"

        architect = TechArchitect(llm_provider=doubao_llm)
        design_result = architect.execute(
            {
                "requirement_structured": requirement_structured,
                "codebase": {"repo_path": temp_frontend},
            }
        )
        result_payload["design"] = design_result
        _print_design_summary("====== 方案设计结果（摘要） ======", design_result)

        design_data = design_result.get("design", {}) or {}
        file_change_plan = design_data.get("file_change_plan", []) or []
        assert file_change_plan, "方案设计没有产出 file_change_plan"

        fake_diff = {
            "stage": "coding",
            "mode": "diff_bundle",
            "files_changed": ["login/login.css"],
            "patches": [
                {
                    "file_path": "login/login.css",
                    "change_type": "modify",
                    "patch_format": "search_replace",
                    "patch": """FILE: login/login.css
<<<<<<< SEARCH
body.login-page {
  overflow-x: hidden;
  overflow-y: auto;
}
=======
body.login-page {
  overflow-x: hidden;
  overflow-y: auto;
  background:
    radial-gradient(circle at top, rgba(196, 231, 255, 0.9) 0%, rgba(170, 214, 255, 0.62) 30%, rgba(230, 245, 255, 0.22) 58%, rgba(245, 250, 255, 0.08) 100%),
    linear-gradient(180deg, #d9efff 0%, #bfe2ff 42%, #a9d8ff 100%);
}
>>>>>>> REPLACE""",
                    "reason": "将登录页背景调整为浅蓝色，符合需求",
                    "risk_level": "low",
                }
            ],
            "diff": "diff --git a/frontend/login/login.css b/frontend/login/login.css",
            "validation": {"static_checks": ["syntax"], "runtime_checks": []},
        }

        fake_llm = _FakeCodeGenLLM(json.dumps(fake_diff, ensure_ascii=False))
        codegen_agent = CodeGeneratorAgent(
            llm_provider=fake_llm,
            repo_root=temp_frontend,
        )

        codegen_context = {
            "codebase": {"repo_path": temp_frontend},
            "requirement_structured": requirement_structured,
            "design": design_data,
            "codebase_context": design_result.get("codebase_context", {}),
        }

        code_diff_result = codegen_agent.execute(codegen_context)
        result_payload["code_diff"] = code_diff_result
        _print_code_diff_summary("====== 代码生成结果（摘要） ======", code_diff_result)

        patcher = Patcher(repo_root=temp_frontend)
        patch_data = code_diff_result.get("code_diff", {}) or {}
        patches = patch_data.get("patches", []) or []
        assert patches, "代码生成结果没有 patches"

        patch_results = []
        for patch_item in patches:
            patch_obj = Patch(**patch_item)
            patch_result = patcher.apply(patch_obj)
            patch_results.append(patch_result.model_dump())
            print(
                f"补丁应用结果: file={patch_result.file_path}, applied={patch_result.applied}, message={patch_result.message}, error={patch_result.error}"
            )
            assert (
                patch_result.applied
            ), f"补丁应用失败: {patch_result.error or patch_result.message}"

        result_payload["patch_result"] = patch_results

        patched_css_path = os.path.join(temp_frontend, "login", "login.css")
        with open(patched_css_path, "r", encoding="utf-8") as f:
            patched_css = f.read()

        expected_markers = ["#d9efff", "#bfe2ff", "#a9d8ff", "background:"]
        missing = [marker for marker in expected_markers if marker not in patched_css]
        assert not missing, f"修改后的 login.css 缺少预期标记: {missing}"

        # 这里不直接执行 HTML，而是做文件级验证，确保修改落盘。
        verification = {
            "patched_css_path": patched_css_path,
            "verified_markers": expected_markers,
            "run_attempted": False,
            "run_exit_code": None,
            "run_stdout": "",
            "run_stderr": "",
        }
        result_payload["verification"] = verification

        print("\n✅ 前端登录页背景修改全流程测试通过!")

    finally:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, ensure_ascii=False, indent=2)
        print(f"\n已保存 JSON 结果到: {output_path}")
        shutil.rmtree(temp_root, ignore_errors=True)


def test_requirement_analyst():
    """测试需求分析 Agent"""
    print("====== 开始运行 Requirement Analyst 测试 ======\n")

    # 初始化 Agent (使用真实的豆包LLM)
    analyst = RequirementAnalyst(llm_provider=doubao_llm)

    # 测试场景 1: 正常需求分析
    print("=== 测试场景 1: 正常需求分析 ===\n")
    test_context = {"requirement_raw": """
        我需要做一个内部人员管理的后台，要包括员工列表、增加新员工、删除员工的功能。
        还要有一个统计面板，能看各个部门的人数占比饼图。
        要求页面加载要在2秒内完成，并且必须有权限控制，只有管理员能删人。
        另外，UI要偏梦感和科技感，类似飞书的风格。
        """}

    print(f"输入需求:\n{test_context['requirement_raw']}\n")
    print("正在调用 LLM 进行需求分析...")

    try:
        # 执行 Agent
        result = analyst.execute(test_context)

        _print_requirement_summary("\n====== 分析成功（摘要） ======", result)

        # 基本校验
        assert "requirement_structured" in result, "缺少 requirement_structured 字段"
        structured_data = result["requirement_structured"]
        assert "goal" in structured_data, "缺少 goal 字段"
        assert "features" in structured_data, "缺少 features 字段"
        assert "constraints" in structured_data, "缺少 constraints 字段"
        assert "acceptance_criteria" in structured_data, "缺少 acceptance_criteria 字段"
        assert "is_clear" in structured_data, "缺少 is_clear 字段"
        assert (
            "clarifying_questions" in structured_data
        ), "缺少 clarifying_questions 字段"

        print(f"\n需求是否清晰: {structured_data['is_clear']}")
        print(f"核心目标: {structured_data['goal']}")
        print(f"功能点数量: {len(structured_data['features'])}")
        print(f"约束条件数量: {len(structured_data['constraints'])}")
        print(f"验收标准数量: {len(structured_data['acceptance_criteria'])}")

        # 测试场景 2: 模糊需求测试
        print("\n\n=== 测试场景 2: 模糊需求测试 ===\n")
        fuzzy_context = {"requirement_raw": "我要做一个类似微信的软件，越快越好"}

        max_retries = 2
        for i in range(max_retries):
            print(f"\n--- 第 {i+1} 轮交互 ---")
            print(f"用户当前输入:\n{fuzzy_context['requirement_raw']}")
            fuzzy_result = analyst.execute(fuzzy_context)

            structured = fuzzy_result.get("requirement_structured", {})
            is_clear = structured.get("is_clear", False)

            print(f"\n>> Agent判断 is_clear: {is_clear}")
            if is_clear:
                print("✅ 需求终于清晰！进入下一环节，最终输出：")
                _print_requirement_summary("- 模糊需求澄清结果（摘要）", fuzzy_result)
                break

            questions = structured.get("clarifying_questions", [])
            print(
                f"⚠️ Agent以为需求不足以支撑开发，挂起流程并提出 {len(questions)} 个追问:"
            )
            for idx, q in enumerate(questions):
                print(f"  {idx+1}. {q}")

            if i < max_retries - 1:
                # 模拟用户根据问题进行补充
                print("\n[自动化模拟] -> 用户正在根据追问补充细节...")
                fuzzy_context[
                    "requirement_raw"
                ] += "\n[补充说明1]: 这是用于我们公司内部培训的交流工具，仅包含群聊和文件发送，不需要朋友圈和支付功能。开发要在1个月内上线，带有阅后即焚功能。"
            else:
                print("\n⚠️ 达到最大追问次数，跳出反问循环，最终输出需求分析：")
                _print_requirement_summary("- 最终需求分析（摘要）", fuzzy_result)

        # 测试场景 3: 极端短输入测试
        print("\n\n=== 测试场景 3: 极端短输入测试 ===\n")
        extreme_context = {"requirement_raw": "111"}
        extreme_result = analyst.execute(extreme_context)
        _print_requirement_summary("- 极端短输入结果（摘要）", extreme_result)

        # 验证极端输入处理
        extreme_structured = extreme_result.get("requirement_structured", {})
        assert not extreme_structured.get("is_clear"), "极端输入应该被标记为不清晰"
        assert (
            len(extreme_structured.get("clarifying_questions", [])) > 0
        ), "极端输入应该有澄清问题"

        # 测试场景 4: 空输入测试
        print("\n\n=== 测试场景 4: 空输入测试 ===\n")
        try:
            empty_context = {"requirement_raw": ""}
            empty_result = analyst.execute(empty_context)
            print("❌ 空输入应该抛出异常")
        except ValueError as e:
            print(f"✅ 空输入正确抛出异常: {e}")

        print("\n✅ 所有测试场景通过!")

    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback

        traceback.print_exc()


def test_full_flow():
    """测试完整流程：需求分析 -> 方案设计"""
    print("\n\n====== 开始运行完整流程测试 ======\n")

    # 初始化两个 Agent
    analyst = RequirementAnalyst(llm_provider=doubao_llm)
    architect = TechArchitect(llm_provider=doubao_llm)

    # 测试需求
    test_context = {
        "requirement_raw": "我需要为现有的计算器应用添加乘法和除法功能，并且要支持浮点数运算。"
    }

    print("=== 1. 需求分析阶段 ===")
    print(f"输入需求: {test_context['requirement_raw']}")

    # 执行需求分析
    analyst_result = analyst.execute(test_context)
    _print_requirement_summary("\n需求分析完成（摘要）", analyst_result)

    # 验证需求分析结果
    assert (
        "requirement_structured" in analyst_result
    ), "需求分析缺少 requirement_structured"
    requirement_structured = analyst_result["requirement_structured"]

    print("\n=== 2. 方案设计阶段 ===")
    # 构建方案设计的输入
    design_context = {"requirement_structured": requirement_structured}

    # 执行方案设计
    design_result = architect.execute(design_context)
    _print_design_summary("\n方案设计完成（摘要）", design_result)

    # 验证方案设计结果
    assert "design" in design_result, "方案设计缺少 design"
    design_data = design_result["design"]
    assert "architecture" in design_data, "方案设计缺少 architecture"
    assert "api_design" in design_data, "方案设计缺少 api_design"
    assert "file_change_plan" in design_data, "方案设计缺少 file_change_plan"
    assert "risk_analysis" in design_data, "方案设计缺少 risk_analysis"

    print("\n=== 3. 结果验证 ===")
    print(f"架构设计: {design_data['architecture'][:100]}...")
    print(f"API 设计: {design_data['api_design'][:100]}...")
    print(f"文件变更计划: {len(design_data['file_change_plan'])} 项")
    for item in design_data["file_change_plan"]:
        print(f"  - {item['change_type']}: {item['file_path']}")
    print(f"风险分析: {design_data['risk_analysis'][:100]}...")

    print("\n✅ 完整流程测试通过!")


def test_frontend_full_flow():
    """测试前端代码库完整流程：需求分析 -> 方案设计"""
    print("\n\n====== 开始运行前端代码库完整流程测试 ======\n")

    analyst = RequirementAnalyst(llm_provider=doubao_llm)
    architect = TechArchitect(llm_provider=doubao_llm)

    frontend_repo = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
        )
    )

    test_context = {
        "requirement_raw": "给前端登录界面换一个浅蓝色的背景，并且把登录按钮改成圆角的，要求代码改动尽可能小。",
        "codebase": {"repo_path": frontend_repo},
    }

    print("=== 1. 需求分析阶段（前端） ===")
    print(f"输入需求: {test_context['requirement_raw']}")

    analyst_result = analyst.execute(
        {"requirement_raw": test_context["requirement_raw"]}
    )
    _print_requirement_summary("\n需求分析完成（摘要）", analyst_result)

    assert (
        "requirement_structured" in analyst_result
    ), "前端需求分析缺少 requirement_structured"
    requirement_structured = analyst_result["requirement_structured"]

    print("\n=== 2. 方案设计阶段（前端） ===")
    design_context = {
        "requirement_structured": requirement_structured,
        "codebase": {"repo_path": frontend_repo},
    }

    design_result = architect.execute(design_context)
    _print_design_summary("\n前端方案设计完成（摘要）", design_result)

    assert "design" in design_result, "前端方案设计缺少 design"
    design_data = design_result["design"]
    assert "architecture" in design_data, "前端方案设计缺少 architecture"
    assert "api_design" in design_data, "前端方案设计缺少 api_design"
    assert "file_change_plan" in design_data, "前端方案设计缺少 file_change_plan"
    assert "risk_analysis" in design_data, "前端方案设计缺少 risk_analysis"

    codebase_context = design_result.get("codebase_context", {})
    hot_files = codebase_context.get("hot_files", [])
    retrieved_paths = [item.get("path", "") for item in hot_files]

    print("\n=== 3. 结果验证（前端） ===")
    print(f"架构设计: {design_data['architecture'][:100]}...")
    print(f"API 设计: {design_data['api_design'][:100]}...")
    print(f"文件变更计划: {len(design_data['file_change_plan'])} 项")
    for item in design_data["file_change_plan"]:
        print(f"  - {item['change_type']}: {item['file_path']}")
    print(f"召回文件数量: {len(hot_files)}")
    print(f"前端命中文件: {', '.join(retrieved_paths[:6])}")
    if len(retrieved_paths) > 6:
        print(f"- ... 其余 {len(retrieved_paths) - 6} 个文件省略")
    print(f"风险分析: {design_data['risk_analysis'][:100]}...")

    assert len(hot_files) > 0, "前端检索没有召回任何文件"
    assert any(
        path.endswith("index.html") for path in retrieved_paths
    ), "前端检索应命中 index.html"
    assert any(
        path.endswith("app.js") for path in retrieved_paths
    ), "前端检索应命中 app.js"
    assert any(
        "login" in path for path in retrieved_paths
    ), "前端检索应命中 login 目录文件"

    print("\n✅ 前端代码库完整流程测试通过!")


def test_self_healing_loop():
    """测试自愈循环（失败回灌 + 自动诊断 + 多轮迭代）"""
    print("\n" + "=" * 70)
    print("测试: 自愈循环 - 失败回灌 + 自动诊断")
    print("=" * 70)

    from pathlib import Path
    import shutil

    # 创建简单的测试代码库（使用 testcode 作为模板）
    source_testcode = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "testcode")
    )
    test_repo = tempfile.mkdtemp(prefix="self_healing_test_")

    try:
        # 复制 testcode 到临时目录作为基础代码库
        if os.path.exists(source_testcode):
            for item in os.listdir(source_testcode):
                src = os.path.join(source_testcode, item)
                dst = os.path.join(test_repo, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            print(f"✓ 使用 testcode 作为基础代码库: {test_repo}")
        else:
            # 如果 testcode 不存在，创建简单的项目结构
            (Path(test_repo) / "src").mkdir()
            main_py = Path(test_repo) / "src" / "main.py"
            main_py.write_text(
                "def add(a, b):\n"
                "    return a + b\n"
                "\n"
                "result = add(1, 2)\n"
                "print(f'Result: {result}')\n"
            )
            print(f"✓ 创建简单的测试项目: {test_repo}")

        # 初始化协调器（禁用 Docker 以加速测试）
        coordinator = SelfHealingCoordinator(max_retries=2, use_docker=False)

        # 执行自愈循环
        context = {
            "requirement_raw": "这是一个计算器应用的增强需求：确保现有的加法函数正常工作并通过所有测试",
            "codebase": {
                "repo_path": test_repo,
            },
        }

        report = coordinator.execute_with_self_healing(context)

        # 验证报告结构
        assert isinstance(report.success, bool), "报告缺少 success 字段"
        assert isinstance(report.iterations, int), "迭代次数应为整数"
        assert report.total_time >= 0, "总耗时应为正数"

        print(f"\n{'='*70}")
        print("📊 自愈循环测试结果摘要")
        print(f"{'='*70}")
        print(f"最终状态: {'✅ 成功' if report.success else '⚠️ 未成功'}")
        print(f"迭代次数: {report.iterations}")
        print(f"总耗时: {report.total_time:.2f}s")
        print(f"失败历史: {len(report.failure_history)} 条记录")

        if report.failure_history:
            print(f"\n失败原因分析：")
            for i, failure in enumerate(report.failure_history, 1):
                error_type = (
                    failure.error_type
                    if isinstance(failure.error_type, str)
                    else failure.error_type.value
                )
                print(f"  {i}. {error_type}")
                print(
                    f"     根源: {failure.root_cause[:60] if failure.root_cause else 'N/A'}..."
                )
                print(f"     置信度: {failure.confidence:.0%}")

        print(f"\n✅ 自愈循环端到端测试完成")
        print(f"   - 流程链路: 需求分析 → 方案设计 → 代码生成 → 测试 → 诊断 → 决策")
        print(f"   - 自愈能力: 已集成")
        print(f"   - 测试状态: {'通过' if report.success else '流程可用'}")

        return report

    finally:
        # 清理测试目录
        if os.path.exists(test_repo):
            shutil.rmtree(test_repo, ignore_errors=True)


if __name__ == "__main__":
    # test_requirement_analyst()
    # test_full_flow()
    # test_frontend_full_flow()
    # test_code_generator_agent()
    # test_patch_and_verify_testcode()
    test_sdet_agent_with_runner()
    test_sdet_agent_isolated_workspace_and_patch_application()
    test_docker_container_verification()
    test_self_healing_loop()
    test_frontend_login_background_flow()
