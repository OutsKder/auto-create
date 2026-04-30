"""
coordinator.py - 自愈循环协调器

协调整个自愈循环过程，整合 CodeGen -> SDET -> Runner -> TriageAgent -> RetryManager
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.agent.agents import CodeGeneratorAgent, SDETAgent
from backend.agent.codegen.runner import Runner
from backend.agent.codegen import Patcher, Patch
from backend.agent.workspace import WorkspaceManager
from backend.doubao_llm import llm as doubao_llm
from backend.agent import RequirementAnalyst, TechArchitect
from .triage_agent import TriageAgent
from .retry_manager import RetryManager
from .models import SelfHealingReport, SelfHealingIteration, FailureAnalysis


class SelfHealingCoordinator:
    """自愈循环协调器

    职责：
    - 管理整个自愈循环
    - 协调 CodeGen -> SDET -> Runner -> TriageAgent 的流程
    - 记录每次迭代的详细信息
    - 生成最终报告
    """

    def __init__(
        self, max_retries: int = 3, use_docker: bool = True, llm_provider: Any = None
    ):
        """初始化协调器

        Args:
            max_retries: 最大重试次数
            use_docker: 是否使用 Docker 执行测试
            llm_provider: LLM 提供者（如未指定则使用豆包 LLM）
        """
        if llm_provider is None:
            llm_provider = doubao_llm

        self.codegen = CodeGeneratorAgent(llm_provider=llm_provider)
        self.sdet = SDETAgent(llm_provider=llm_provider)
        self.runner = Runner(use_docker=use_docker)
        self.triage = TriageAgent()
        self.retry_manager = RetryManager(max_retries=max_retries)
        self.workspace_manager = WorkspaceManager()

        self.use_docker = use_docker
        self._failure_history: List[FailureAnalysis] = []
        self._iterations_log: List[SelfHealingIteration] = []
        self._start_time = None

    def execute_with_self_healing(self, context: dict) -> SelfHealingReport:
        """
        执行代码生成 + 测试 + 自愈循环

        Args:
            context: {
                "requirement_raw": str,  # 原始需求
                "codebase": {
                    "repo_path": str,
                },
            }

        Returns:
            SelfHealingReport: 完整的自愈循环报告
        """

        self._start_time = time.time()
        self.retry_manager.reset()
        self._failure_history = []
        self._iterations_log = []

        try:
            # 前置步骤：需求分析和方案设计
            print(f"\n{'='*70}")
            print("📋 前置步骤：需求分析")
            print(f"{'='*70}\n")

            analyst = RequirementAnalyst(llm_provider=doubao_llm)
            analyst_result = analyst.execute(
                {"requirement_raw": context["requirement_raw"]}
            )
            requirement_structured = analyst_result.get("requirement_structured", {})
            print(f"✓ 需求分析完成")

            print(f"\n{'='*70}")
            print("🏗️  前置步骤：方案设计")
            print(f"{'='*70}\n")

            architect = TechArchitect(llm_provider=doubao_llm)
            design_result = architect.execute(
                {
                    "requirement_structured": requirement_structured,
                    "codebase": context["codebase"],
                }
            )
            design_data = design_result.get("design", {})
            codebase_context = design_result.get("codebase_context", {})
            print(f"✓ 方案设计完成")

        except Exception as e:
            print(f"\n❌ 前置步骤失败: {e}")
            elapsed = time.time() - self._start_time
            return SelfHealingReport(
                success=False,
                iterations=0,
                final_code=[],
                test_results={
                    "passed": False,
                    "exit_code": 1,
                    "logs": f"前置步骤失败: {e}",
                },
                failure_history=[],
                total_time=elapsed,
                iterations_log=[],
            )

        iteration = 0
        feedback_for_codegen = None
        final_patches = []
        final_test_result = None

        print(f"\n{'='*70}")
        print("🔄 开始自愈循环...")
        print(f"{'='*70}\n")

        while True:
            iteration += 1
            print(f"\n{'─'*70}")
            print(f"⏳ 第 {iteration} 次迭代")
            print(f"{'─'*70}")

            try:
                # 1. CodeGen：生成或修复代码
                print(f"\n[1/5] 代码生成 (CodeGen)...")
                codegen_input = {
                    "requirement_raw": context["requirement_raw"],
                    "requirement_structured": requirement_structured,
                    "design": design_data,
                    "codebase": context["codebase"],
                    "codebase_context": codebase_context,
                }

                if feedback_for_codegen:
                    codegen_input["failure_feedback"] = feedback_for_codegen
                    print(
                        f"      ℹ️ 注入失败反馈: {feedback_for_codegen.get('error_type', '未知')}"
                    )

                codegen_result = self.codegen.execute(codegen_input)
                patches = codegen_result.get("code_diff", {}).get("patches", [])
                print(f"      ✓ 生成 {len(patches)} 个代码补丁")
                final_patches = patches

                # 2. WorkspaceManager：创建隔离工作区
                print(f"\n[2/5] 创建隔离工作区...")
                workspace_path = self.workspace_manager.create_workspace(
                    context["codebase"]["repo_path"]
                )
                print(f"      ✓ 工作区: {workspace_path}")

                # 3. 应用补丁
                print(f"\n[3/5] 应用代码补丁...")
                patcher = Patcher()
                for i, patch in enumerate(patches):
                    result = patcher.apply(patch)
                    status = "✓ 已应用" if result.applied else "✗ 未应用"
                    print(f"      {status}: {patch.file_path}")

                # 4. SDET：生成测试
                print(f"\n[4/5] 生成测试套件 (SDET)...")
                sdet_result = self.sdet.execute(
                    {
                        "workspace": workspace_path,
                        "requirement": context["requirement_raw"],
                    }
                )
                test_bundle = sdet_result.get("test_bundle")
                runner_commands = test_bundle.runner_commands if test_bundle else []
                print(f"      ✓ 生成 {len(runner_commands)} 个测试命令")

                # 5. Runner：执行测试
                print(f"\n[5/5] 在隔离环境执行测试...")
                runner_result = self.runner.run_commands(
                    runner_commands,
                    workspace_path,
                    (
                        {
                            "network_disabled": True,
                            "read_only": True,
                            "cpus": "1",
                            "memory": "512m",
                        }
                        if self.use_docker
                        else {}
                    ),
                )
                final_test_result = runner_result
                print(
                    f"      {'✓' if runner_result.passed else '✗'} 测试 {'通过' if runner_result.passed else '失败'}"
                )
                print(f"      exit_code: {runner_result.exit_code}")

                # 记录本次迭代
                iteration_log = SelfHealingIteration(
                    iteration_num=iteration,
                    codegen_output=codegen_result,
                    test_result={
                        "passed": runner_result.passed,
                        "exit_code": runner_result.exit_code,
                        "logs_snippet": runner_result.logs[:200],
                    },
                    passed=runner_result.passed,
                )
                self._iterations_log.append(iteration_log)

                # 6. 判断结果
                if runner_result.passed:
                    print(f"\n{'='*70}")
                    print(f"✅ 第 {iteration} 次迭代成功！")
                    print(f"{'='*70}\n")

                    elapsed = time.time() - self._start_time
                    return SelfHealingReport(
                        success=True,
                        iterations=iteration,
                        final_code=patches,
                        test_results={
                            "passed": True,
                            "exit_code": 0,
                            "logs": runner_result.logs,
                        },
                        failure_history=[],
                        total_time=elapsed,
                        iterations_log=self._iterations_log,
                    )

                # 7. 失败：进行诊断
                print(f"\n❌ 第 {iteration} 次迭代失败，开始失败诊断...\n")

                triage_result = self.triage.execute(
                    {
                        "sandbox_result": runner_result,
                        "code_changes": str(patches),
                        "previous_failures": self._failure_history,
                    }
                )

                failure_analysis = triage_result["failure_analysis"]
                self._failure_history.append(failure_analysis)

                # 更新迭代日志
                iteration_log.failure_analysis = failure_analysis

                print(f"📋 失败诊断结果：")
                print(f"   错误类型: {failure_analysis.error_type.value}")
                print(f"   根本原因: {failure_analysis.root_cause}")
                print(f"   置信度: {failure_analysis.confidence:.0%}")
                print(f"   修复建议: {failure_analysis.suggestion}")

                # 8. RetryManager：决策是否继续
                if not self.retry_manager.should_continue(failure_analysis):
                    print(f"\n{'='*70}")
                    print(f"⚠️  自愈循环停止")
                    print(f"{'='*70}\n")

                    elapsed = time.time() - self._start_time
                    return SelfHealingReport(
                        success=False,
                        iterations=iteration,
                        final_code=final_patches,
                        test_results={
                            "passed": False,
                            "exit_code": runner_result.exit_code,
                            "logs": runner_result.logs,
                        },
                        failure_history=self._failure_history,
                        final_failure=failure_analysis,
                        total_time=elapsed,
                        iterations_log=self._iterations_log,
                    )

                # 9. 反馈给 CodeGen，准备下一轮迭代
                feedback_for_codegen = {
                    "error_type": failure_analysis.error_type.value,
                    "error_message": failure_analysis.error_message,
                    "suggestion": failure_analysis.suggestion,
                    "failed_code": failure_analysis.code_snippet,
                    "root_cause": failure_analysis.root_cause,
                }

                self.retry_manager.record_failure(failure_analysis)

                if iteration < self.retry_manager.max_retries:
                    print(f"\n📝 准备第 {iteration + 1} 次迭代...")
                    print(
                        f"   重试进度: {self.retry_manager.retry_count}/{self.retry_manager.max_retries}"
                    )

            except Exception as e:
                print(f"\n❌ 迭代过程中发生异常: {str(e)}")
                import traceback

                traceback.print_exc()

                elapsed = time.time() - self._start_time
                return SelfHealingReport(
                    success=False,
                    iterations=iteration,
                    final_code=final_patches,
                    test_results={
                        "passed": False,
                        "exit_code": 1,
                        "logs": f"Exception: {str(e)}",
                    },
                    failure_history=self._failure_history,
                    final_failure=None,
                    total_time=elapsed,
                    iterations_log=self._iterations_log,
                )

    def get_retry_status(self) -> dict:
        """获取重试状态"""
        return self.retry_manager.get_status()
